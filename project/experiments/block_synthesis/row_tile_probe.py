"""Freeze unchanged P/S/feeder RTL and test native multi-row weight reuse.

This is a protocol/numeric probe, not a new hardware implementation, compiler
qualification, DRAM measurement or calibrated performance/energy result.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import shutil
import subprocess


BANK_SHA = '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
RTL = [
    's_sram/local_s_base.sv', 's_sram/local_s_p.sv',
    's_sram/block_feed_s16k_sram.sv', 'block_feed_v1/block_feed_loader.sv',
    'block_local_s/block_local_s_arbiter.sv',
    'block_v2/block_v2_m.sv', 'block_v2/block_v2_g.sv',
    'block_v2/block_v2_g_tables.svh',
    'pu_leaf_base/pu_p_group.sv', 'pu_leaf_base/pu_p_store_control.sv',
    'pu_leaf_base/pj_feed_hold.sv', 'pu_leaf_base/pj_mem_port.sv',
    'pu_leaf_base/pj_sram_client.sv',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def final_s32(value, shift):
    quotient, remainder = divmod(value, 1 << shift)
    if shift and (remainder * 2 > 1 << shift or
                  (remainder * 2 == 1 << shift and quotient % 2)):
        quotient += 1
    return min((1 << 31) - 1, max(-(1 << 31), quotient))


def prepare(source_root, bank_model, output, long_k=0):
    if sha(bank_model) != BANK_SHA:
        raise ValueError('unqualified SRAM bank model')
    output.mkdir(parents=True, exist_ok=False)
    sources = {}
    for relative in RTL:
        original = source_root / 'project/rtl' / relative
        target = output / 'rtl' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        sources['rtl/' + relative] = sha(target)
    shutil.copyfile(bank_model, output / bank_model.name)
    sources[bank_model.name] = sha(bank_model)
    bench = Path(__file__).with_name('tb_row_tile_probe.sv')
    shutil.copyfile(bench, output / bench.name)
    sources[bench.name] = sha(bench)
    generator = Path(__file__)
    shutil.copyfile(generator, output / generator.name)
    sources[generator.name] = sha(generator)
    words, cases, groups = [], [], []
    shapes = [(r, k) for r in (1, 2, 4, 8) for k in (1, 3, 7, 17)]
    if long_k:
        if not 1 <= long_k <= 2048:
            raise ValueError('long K outside declared probe storage')
        shapes.append((2, long_k))
    edges_a = [-2147483648, 2147483647, -65537, -32769, -32768,
               -1, 0, 1, 32767, 32768, 65535, 65536]
    edges_b = [-32768, 32767, -129, -1, 0, 1, 127, 128]

    def add_case(rows, weights, kind, group):
        r, k = len(rows), len(weights)
        base_a = len(words)
        words.extend(x & ((1 << 64) - 1) for row in rows for x in row)
        base_b = len(words)
        words.extend(x & ((1 << 64) - 1) for x in weights)
        base_gold = len(words)
        golden = [sum(a * b for a, b in zip(row, weights)) for row in rows]
        if any(not -(1 << 63) <= v < (1 << 63) for v in golden):
            raise ValueError('S64 golden overflow')
        words.extend(x & ((1 << 64) - 1) for x in golden)
        base_final = len(words)
        words.extend(final_s32(x, shift) & 0xffffffff
                     for x in golden for shift in (0, 8, 16, 24))
        cases.append({'id': len(cases), 'group': group, 'kind': kind,
                      'rows': r, 'k': k, 'a': base_a, 'b': base_b,
                      'gold': base_gold, 'final': base_final, 'golden_s64': golden})
        return len(cases) - 1

    for group, (r, k) in enumerate(shapes):
        rng = random.Random(139 + group)
        rows = [[(edges_a[(rr * k + kk + group) % len(edges_a)]
                  if kk % 3 != 2 else rng.randint(-(1 << 31), (1 << 31) - 1))
                 for kk in range(k)] for rr in range(r)]
        weights = [(edges_b[(kk + group) % len(edges_b)]
                    if kk % 3 != 2 else rng.randint(-32768, 32767))
                   for kk in range(k)]
        tile = add_case(rows, weights, 'tile', group)
        serial = [add_case([row], weights, 'serial', group) for row in rows]
        groups.append({'id': group, 'rows': r, 'k': k,
                       'tile': tile, 'serial': serial})
    group = len(groups)
    tie_rows = [[128], [-128], [384], [-384]]
    tile = add_case(tie_rows, [1], 'tile', group)
    serial = [add_case([row], [1], 'serial', group) for row in tie_rows]
    groups.append({'id': group, 'rows': 4, 'k': 1, 'tile': tile, 'serial': serial,
                   'purpose': 'positive and negative half-even ties'})
    (output / 'vectors.hex').write_text(''.join(f'{w:016x}\n' for w in words))
    (output / 'vectors_size.svh').write_text(f'localparam integer VECTOR_WORDS={len(words)};\n')
    (output / 'cases.svh').write_text(''.join(
        f"run_case({c['id']},{c['rows']},{c['k']},{c['a']},{c['b']},{c['gold']},{c['final']});\n"
        for c in cases))
    for name in ('vectors.hex', 'vectors_size.svh', 'cases.svh'):
        sources[name] = sha(output / name)
    manifest = {'kind': 'native-row-tile-probe-v1', 'cases': cases,
                'groups': groups, 'source_root': str(source_root),
                'source_commit': subprocess.check_output(
                    ['git', 'rev-parse', 'HEAD'], cwd=source_root, text=True).strip(),
                'sha256': sources, 'vector_words': len(words),
                'scope': 'S32 A / S16 B, N1, K segment1, full-K S64 and final RNE; unchanged RTL',
                'excluded': ['dynamic packing', 'N>1 scatter', 'compiler registration',
                             'MC/LC program', 'DRAM timing/traffic', 'energy', 'physical timing']}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    sources_for_compile = ['tb_row_tile_probe.sv'] + [
        'rtl/' + name for name in RTL if name.endswith('.sv')] + [bank_model.name]
    (output / 'compile.f').write_text(''.join(name + '\n' for name in sources_for_compile))
    print(json.dumps({'cases': len(cases), 'groups': len(groups),
                      'vector_words': len(words), 'output': str(output)}))


def analyse(directory, log):
    manifest = json.loads((directory / 'manifest.json').read_text())
    for name, expected in manifest['sha256'].items():
        if sha(directory / name) != expected:
            raise ValueError('probe input changed: ' + name)
    records = {}
    text = log.read_text()
    for match in re.finditer(r'^ROW_TILE (\{.*\})$', text, re.MULTILINE):
        record = json.loads(match[1])
        if record['id'] in records:
            raise ValueError('duplicate case')
        records[record['id']] = record
    if (text.count('PASS native row tile probe') != 1 or
            set(records) != {c['id'] for c in manifest['cases']} or 'FATAL' in text):
        raise ValueError('probe incomplete')
    for case in manifest['cases']:
        record = records[case['id']]
        r, k = case['rows'], case['k']
        expected = {'rows': r, 'k': k, 'a_fires': 3 * r * k,
                    'b_fires': 2 * k, 'wide_reads': k * (2 + 3 * ((r + 3) // 4)),
                    'store_acks': 5 * r, 'a_stage_words': 3 * r * k,
                    'b_stage_words': k}
        for key, value in expected.items():
            if record[key] != value:
                raise ValueError(f'case {case["id"]} {key}: {record[key]} != {value}')
    groups = []
    for group in manifest['groups']:
        tile = records[group['tile']]
        serial = [records[i] for i in group['serial']]
        groups.append({'rows': group['rows'], 'k': group['k'],
                       'tile_cycles': tile['cycles'],
                       'serial_cycles': sum(c['cycles'] for c in serial),
                       'tile_b_stage_words': tile['b_stage_words'],
                       'serial_b_stage_words': sum(c['b_stage_words'] for c in serial),
                       'tile_a_stage_words': tile['a_stage_words'],
                       'serial_a_stage_words': sum(c['a_stage_words'] for c in serial)})
    result = {'manifest_sha256': sha(directory / 'manifest.json'),
              'log_sha256': sha(log), 'passed_cases': len(records), 'groups': groups,
              'scope': manifest['scope'], 'excluded': manifest['excluded'],
              'timing_note': 'Testbench cycles include serialized host transactions and deliberate stalls; not system latency.'}
    (directory / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--source-root', type=Path, required=True)
    prep.add_argument('--bank-model', type=Path, required=True)
    prep.add_argument('--output', type=Path, required=True)
    prep.add_argument('--long-k', type=int, default=0)
    check = sub.add_parser('analyse')
    check.add_argument('directory', type=Path)
    check.add_argument('log', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.source_root, args.bank_model, args.output, args.long_k)
    else:
        analyse(args.directory, args.log)
