"""Server-only byte microprogram/RTL pilot and source-bound cost-table producer."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import random
import subprocess
import time

HERE = Path(__file__).resolve().parent
S = importlib.util.spec_from_file_location('micro76', HERE/'micro.py')
M = importlib.util.module_from_spec(S); S.loader.exec_module(M)
SOURCES = {'micro_sha256': 'micro.py', 'byte_core_sv_sha256': 'byte_core.sv',
           'byte_tb_cpp_sha256': 'byte_tb.cpp', 'run_server_sha256': 'run_server.py'}


def need(ok, message):
    if not ok: raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1<<20), b''): value.update(block)
    return value.hexdigest()


def put(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def bound(folder):
    folder = Path(folder); manifest = load(folder/'manifest.json')
    for a in manifest['artifacts']:
        p = folder/a['path']
        need(p.resolve().is_relative_to(folder.resolve()) and p.stat().st_size == a['bytes'] and sha(p) == a['sha256'], 'source artifact '+str(p))
    return {'path': str(folder), 'manifest_sha256': sha(folder/'manifest.json')}


def oracle(op, a, b=0, shift=0):
    valid = True
    if op.startswith('mul_'): result = {'value': a*b}
    elif op in ('add_s64', 'sub_s64', 'add_u128'):
        v = a-b if op == 'sub_s64' else a+b; signed = op != 'add_u128'; width = 64 if signed else 128
        valid = -(1<<(width-1)) <= v < 1<<(width-1) if signed else 0 <= v < 1<<width
        encoded = v & ((1<<width)-1)
        if signed and encoded >= 1<<(width-1): encoded -= 1<<width
        result = {'value': encoded}
    elif op == 'abs_s64': result = {'value': abs(a)}
    elif op == 'cmp_s64': result = {'less': a < b, 'equal': a == b}
    elif op == 'max_s64': result = {'value': max(a, b)}
    elif op.startswith('shl_') or op == 'align_s32_i64':
        v = a << shift; width = 64 if op == 'align_s32_i64' else 128; signed = op != 'shl_u128'
        valid = -(1<<(width-1)) <= v < 1<<(width-1) if signed else 0 <= v < 1<<width
        encoded = v & ((1<<width)-1)
        if signed and encoded >= 1<<(width-1): encoded -= 1<<width
        result = {'value': encoded}
    elif op.startswith('rne_') or op == 'div_rne_s128_u64_i32':
        den = 1<<shift if op.startswith('rne_') else b
        if den:
            q, r = divmod(abs(a), den); q += 2*r > den or (2*r == den and q&1)
            value = -q if a < 0 else q
            result = {'value': value}; valid = -(1<<31) <= value < 1<<31
        else: return {'valid': False}
    elif op == 'udiv_u128':
        if not b: return {'valid': False}
        q, r = divmod(a, b); result = {'quotient': q, 'remainder': r}
    elif op == 'isqrt_u128': result = {'value': math.isqrt(a)}
    else: raise ValueError('unknown oracle op')
    result['valid'] = valid
    return result


def cases(random_count=2):
    result = []
    def add(op, a, b=0, shift=0, source='boundary'):
        result.append({'op': op, 'a': a, 'b': b, 'shift': shift, 'source': source})
    for op, aa, bb in [('mul_s32_s32', -(1<<31), -(1<<31)), ('mul_s64_s32', -(1<<63), -(1<<31)),
                       ('mul_s32_u16', -(1<<31), 32768), ('mul_s32_u16', (1<<31)-1, 65535)]: add(op, aa, bb)
    for op in ('add_s64', 'sub_s64', 'max_s64', 'cmp_s64'):
        for aa, bb in [(-(1<<63), (1<<63)-1), ((1<<63)-1, -1), (0, 0)]: add(op, aa, bb)
    add('add_u128', (1<<128)-1, 1); add('add_u128', 0, (1<<128)-1)
    for aa in (-(1<<63), -1, 0, (1<<63)-1): add('abs_s64', aa)
    for op in ('rne_s64_i32', 'rne_s128_i32'):
        for aa, ss in [(-5, 1), (-3, 1), (5, 1), (3, 1), ((1<<31)-1, 0), (1<<31, 0), (-(1<<63), 64), (0, 128)]: add(op, aa, shift=ss)
    add('rne_s128_i32', -(1<<127), shift=128)
    for op, aa, ss in [('align_s32_i64', -(1<<31), 32), ('align_s32_i64', 1, 63),
                       ('shl_s64_s128', -(1<<63), 12), ('shl_u128', 1<<127, 1)]: add(op, aa, shift=ss)
    for aa, bb in [(0, 1), ((1<<128)-1, (1<<64)+1), (17, 3), (123, 0)]: add('udiv_u128', aa, bb)
    for aa in [0, 1, 2, (1<<128)-1, ((1<<63)+7)**2-1]: add('isqrt_u128', aa)
    for aa, bb in [(-5, 2), (-3, 2), (123456789<<12, 777), (1<<100, 1), (0, 0)]: add('div_rne_s128_u64_i32', aa, bb)
    rng = random.Random(7601)
    for op in M.OP_SPECS:
        for _ in range(random_count):
            if op == 'mul_s32_u16': aa, bb = rng.randrange(-(1<<31), 1<<31), rng.randrange(1<<16)
            elif op in ('add_u128', 'shl_u128', 'udiv_u128', 'isqrt_u128'): aa, bb = rng.randrange(1<<128), rng.randrange(1, 1<<128)
            elif op in ('rne_s128_i32', 'div_rne_s128_u64_i32'): aa, bb = rng.randrange(-(1<<127), 1<<127), rng.randrange(1, 1<<64)
            elif op in ('mul_s32_s32', 'align_s32_i64'): aa, bb = rng.randrange(-(1<<31), 1<<31), rng.randrange(-(1<<31), 1<<31)
            else: aa, bb = rng.randrange(-(1<<63), 1<<63), rng.randrange(-(1<<63), 1<<63)
            if op == 'mul_s64_s32': bb = rng.randrange(-(1<<31), 1<<31)
            ss = rng.randrange(64 if op == 'align_s32_i64' else 128 if op.startswith('shl_') else 129)
            add(op, aa, bb, ss, 'random_seed7601')
    return result


def actual_cases(granite, compiled):
    # This function is server-only. No entire model is loaded; existing integer arrays are read-only.
    import numpy as np
    source = [bound(compiled)]; result = []
    with np.load(Path(compiled)/'constants.npz', allow_pickle=False) as const:
        for folder in granite:
            source.append(bound(folder)); report = load(Path(folder)/'report.json'); layer = report['layer']
            need(report['router_bits'] == 16 and report['split'] == 'evaluation', 'frozen R16/evaluation only')
            with np.load(Path(folder)/'runtime.npz', allow_pickle=False) as z:
                def add(op, a, b=0, shift=0, provenance=None, expected=None):
                    row = {'op': op, 'a': int(a), 'b': int(b), 'shift': int(shift),
                           'source': {'run': str(folder), 'manifest_sha256': sha(Path(folder)/'manifest.json'),
                                      'layer': layer, 'provenance': provenance}}
                    if expected is not None: row['source_expected'] = int(expected)
                    result.append(row)
                for t in (0, 64, 71):
                    for rank in (0, 7):
                        expert = int(z['router.ids'][t, rank])
                        for c in (0, 1535):
                            a = int(z['down_acc32'][t, rank, c]); b = int(const[f'L{layer}.down_mant_q31'][expert, c])
                            add('mul_s32_s32', a, b, provenance={'down_acc32': [t, rank, c], 'expert': expert, 'mantissa_output': c}, expected=z['down_RQ_product64'][t, rank, c])
                            shift = 31-int(const[f'L{layer}.down_exp'][expert, c])-int(z['mid_delta'][t, rank])
                            need(0 <= shift <= 128, 'actual RQ falls within calibrated right-shift domain')
                            add('rne_s64_i32', a*b, shift=shift, provenance={'down_RQ_product64': [t, rank, c], 'shift_formula': '31-exp-mid_delta'}, expected=z['down_q12'][t, rank, c])
                            add('mul_s32_u16', z['down_q12'][t, rank, c], z['router.gate_q15'][t, rank],
                                provenance={'down_q12': [t, rank, c], 'gate_q15': [t, rank]}, expected=z['merge_product64'][t, rank, c])
                    c = 0; x = int(z['layer_output_q12'][t, c]); gamma = int(const[f'L{layer}.next_gamma_q20'][c])
                    den = int(z['next_norm.denominator_u64'][t])
                    add('mul_s32_s32', x, gamma, provenance={'layer_output_q12': [t, c], 'next_gamma_q20': c})
                    add('shl_s64_s128', x*gamma, shift=12, provenance={'norm_numerator_for': [t, c]})
                    add('div_rne_s128_u64_i32', (x*gamma)<<12, den, provenance={'next_norm': [t, c]}, expected=z['next_norm_q12'][t, c])
                    total = (int(z['next_norm.sumsq_hi_u64'][t])<<64)+int(z['next_norm.sumsq_lo_u64'][t])
                    variance = (int(z['next_norm.variance_hi_u64'][t])<<64)+int(z['next_norm.variance_lo_u64'][t])
                    add('udiv_u128', total, 1536, provenance={'next_norm_sumsq': t})
                    add('shl_u128', variance, shift=40, provenance={'next_norm_variance': t})
                    add('isqrt_u128', variance<<40, provenance={'next_norm_variance': t}, expected=den)
    return result, source


def stringify(value):
    if isinstance(value, bool): return value
    if isinstance(value, int): return str(value)
    if isinstance(value, dict): return {k: stringify(v) for k, v in value.items()}
    if isinstance(value, list): return [stringify(v) for v in value]
    return value


class Sink:
    def __init__(self, stream): self.stream, self.topology = stream, hashlib.sha256()
    def write(self, text):
        self.stream.write(text)
        words = text.strip().split()
        if words[0] == 'A': words = words[:7]
        elif words[0] == 'I': words = words[:2]
        elif words[0] == 'O': words = words[:4]
        elif words[0] in ('B', 'E'): words = words[:1]
        self.topology.update((' '.join(words)+'\n').encode())


def cost_table(source):
    ops = {}
    for op in M.OP_SPECS:
        domain = list(range(64 if op == 'align_s32_i64' else 128 if op.startswith('shl_') else 129)) if op.startswith(('rne_', 'shl_')) or op == 'align_s32_i64' else [0]
        profiles = [M.execute(op, 0, 1, shift=s)[1] for s in domain]
        # All data-dependent choices use byte MUX; operation count/address shape depends only on key/shift.
        fields = ('scalar_ALU_dependency_cycles', 'software_controller_dispatches', 'conservative_scalar_cycles_ALU_plus_dispatch',
                  'byte_store_reads', 'byte_store_writes', 'input_load_bytes', 'result_read_bytes', 'scratch_peak_bytes')
        costs = {k: max(p[k] for p in profiles) for k in fields}
        hist = {k: max(p['primitive_counts'].get(k, 0) for p in profiles) for k in M.OPCODES}
        need(all(p['scalar_ALU_dependency_cycles'] == costs['scalar_ALU_dependency_cycles'] for p in profiles), 'fixed cycle topology for '+op)
        costs.update(primitive_counts=hist, frame_capacity_bytes=M.FRAME_BYTES, SIMD8_qualified=False)
        ops[op] = {'spec': M.OP_SPECS[op], 'costs': costs,
                   'proof': {'kind': 'fixed_loops_exhaustive_shift_domain', 'domain': domain,
                             'data_dependent_control': 'none; carry/borrow/sign/round/zero/overflow choices are byte MUX/logic, no early exit',
                             'padding': 'max over complete finite shift domain; physical reads may be lower, service charges bound',
                             'source_sha256': source['micro_sha256']}}
    return {'schema': 'micro-cost-table76-v1', 'level': 'BYTE_ALU_RTL_REPLAY_WITH_SOFTWARE_CONTROLLER', 'source': source,
            'inventory': {'VR8_lanes': 8, 'SFU_count': 1, 'SFU_uses_VR8_lane0': True, 'scalar_frame_bytes': M.FRAME_BYTES,
                          'operand_register_bytes_per_active_lane': 5, 'VR8_operand_register_total_bytes': 40,
                          'ROM': {'word_bits': 32, 'latency_cycles': 2, 'II_cycles': 1, 'ports': 1, 'depth_words': 32768, 'capacity_bytes': 131072},
                          'SFU_ops': ['udiv_u128', 'isqrt_u128', 'div_rne_s128_u64_i32'],
                          'resource_note': 'single SFU controller borrows existing VR8 lane0, no extra wide ALU; frame uses reserved Vaux bank; all frame reads/writes and IO remain payable by service'},
            'ops': ops, 'limits': ['No full wide RTL FSM, register file, target timing/STA or PPA calibration',
                                      'Byte core one clock/action is RTL functionality; extra controller dispatch one/action is a declared candidate surcharge',
                                      'No unconditional SIMD8 division: scalar dependency and byte-store/bank/BUS costs must be scheduled explicitly',
                                      'ROM synchronous candidate32bit latency2/II1 is not process macro timing;128bit payload requires4 reads plus shared bank/BUS/FIFO']}


def rom_inputs(out, compiled=None):
    source = {'kind': 'synthetic_boundary_words'}; words = []
    if compiled:
        import numpy as np
        with np.load(Path(compiled)/'constants.npz', allow_pickle=False) as z:
            for key in ('silu_lut_q12', 'route_exp2_q24'):
                a = z[key]; need(a.dtype.kind in 'iu' and a.dtype.itemsize == 4, 'real integer32 ROM words')
                words.extend(int(v)&0xffffffff for v in a.reshape(-1))
        source = {'kind': 'actual_Granite_integer_LUTs', 'compiled_manifest_sha256': sha(Path(compiled)/'manifest.json'),
                  'order': ['silu_lut_q12', 'route_exp2_q24'], 'packing': 'one32bit little-endian word per element; no concatenation overlap'}
    else: words = [0, 0xffffffff, 0x80000000, 0x7fffffff]+[i*7601 & 0xffffffff for i in range(252)]
    used = len(words); need(used <= 32768, 'finite ROM capacity'); words += [0]*(32768-used)
    (out/'rom.hex').write_text(''.join(f'{v:08x}\n' for v in words), encoding='ascii')
    rng = random.Random(7602); addresses = [0, 1, max(0, used-1), used, 32767]+[rng.randrange(32768) for _ in range(64)]
    (out/'rom.requests').write_text(''.join(f'{a} {words[a]}\n' for a in addresses), encoding='ascii')
    return {**source, 'used_words': used, 'depth_words': 32768, 'used_bytes': used*4, 'reserved_bytes': 131072,
            'requests': len(addresses), 'word_bits': 32, 'latency_cycles': 2, 'II_cycles': 1,
            'ROM_file_sha256': sha(out/'rom.hex'), 'requests_sha256': sha(out/'rom.requests')}


def command(out, label, args, prefix):
    started = time.time()
    completed = subprocess.run([*prefix, *map(str, args)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out/(label+'.log')).write_text(completed.stdout, encoding='utf-8')
    record = {'argv': [*prefix, *map(str, args)], 'returncode': completed.returncode, 'elapsed_seconds': time.time()-started}
    put(out/(label+'-command.json'), record)
    need(completed.returncode == 0, label+' failed; log preserved')
    return record


def run(args):
    out = args.out; out.mkdir(parents=True, exist_ok=False)
    source = load(args.binding); need(source.get('commit'), 'source commit')
    for key, filename in SOURCES.items(): need(source.get(key) == sha(HERE/filename), 'frozen source '+key)
    prefix = json.loads(args.tool_prefix); need(isinstance(prefix, list) and all(isinstance(v, str) for v in prefix), 'tool prefix argv')
    test_cases = cases(args.random_count); inputs = []
    if args.granite:
        need(args.compiled is not None, 'real Granite cases need compiled constants')
        actual, inputs = actual_cases(args.granite, args.compiled); test_cases.extend(actual)
    # Every finite shift control value gets an actual causal byte-RTL replay.
    # Input values cannot change instruction topology: all choices are byte logic/MUX.
    for op in M.OP_SPECS:
        if op.startswith(('rne_', 'shl_')) or op == 'align_s32_i64':
            for shift in range(64 if op == 'align_s32_i64' else 128 if op.startswith('shl_') else 129):
                test_cases.append({'op': op, 'a': 0, 'b': 1, 'shift': shift, 'source': 'complete_shift_domain_zero_input'})
    records = []
    with (out/'program.tsv').open('x', encoding='ascii', newline='\n') as stream:
        for index, case in enumerate(test_cases):
            start = stream.tell(); sink = Sink(stream); name = 'case'+str(index)
            result, profile = M.execute(case['op'], case['a'], case['b'], case['shift'], sink, name)
            expected = oracle(case['op'], case['a'], case['b'], case['shift'])
            need(all(result[k] == v for k, v in expected.items()), 'independent bigint oracle '+name)
            if 'source_expected' in case: need(result.get('value') == case['source_expected'], 'actual original integer code '+name)
            records.append({'case': name, **stringify(case), 'result': stringify(result), 'oracle': stringify(expected), 'status': 'PASS_MICROPROGRAM_ORACLE',
                            'profile': profile, 'trace_byte_start': start, 'trace_byte_end': stream.tell(), 'topology_sha256': sink.topology.hexdigest()})
    put(out/'cases.json', records)
    rom = rom_inputs(out, args.compiled)
    (out/'build').mkdir()
    commands = [command(out, 'verilator-version', [args.verilator, '--version'], prefix),
                command(out, 'compile', [args.verilator, '--cc', '--exe', '--build', '-j', '2', '-Wno-fatal', '--top-module', 'byte_core',
                                        '--prefix', 'Vbyte_core', '--Mdir', out/'build', '-CFLAGS', '-std=c++17', HERE/'byte_core.sv', HERE/'byte_tb.cpp'], prefix),
                command(out, 'rtl-replay', [out/'build/Vbyte_core', out/'program.tsv', out/'rom.requests', out/'rtl_actual.tsv', out/'rtl_report.json', '+rom='+str(out/'rom.hex')], prefix)]
    rtl = load(out/'rtl_report.json')
    need(rtl['status'] == 'PASS_BYTE_CORE_RTL_REPLAY' and rtl['actions'] == sum(r['profile']['scalar_ALU_dependency_cycles'] for r in records)
         and rtl['cases'] == len(records) and all(v > 0 for v in rtl['lanes_covered']), 'actual full action coverage')
    table = cost_table(source)
    for op, value in table['ops'].items():
        selected = [r for r in records if r['op'] == op]
        need(selected, 'every cost key requires actual RTL replay vectors')
        value['domain_bound_status'] = 'FIXED_DATA_INDEPENDENT_TOPOLOGY_EXHAUSTIVE_SHIFT'
        value['observed_max'] = {k: max(r['profile'][k] for r in selected) for k in ('scalar_ALU_dependency_cycles', 'byte_store_reads', 'byte_store_writes', 'scratch_peak_bytes')}
        value['coverage'] = {'cases': len(selected), 'boundary': sum(r['source'] == 'boundary' for r in selected),
                             'random': sum(r['source'] == 'random_seed7601' for r in selected),
                             'real_Granite': sum(isinstance(r['source'], dict) for r in selected),
                             'complete_shift_domain_vectors': sum(r['source'] == 'complete_shift_domain_zero_input' for r in selected), 'RTL_status': rtl['status']}
        for r in selected:
            for k in ('scalar_ALU_dependency_cycles', 'byte_store_reads', 'byte_store_writes', 'input_load_bytes', 'result_read_bytes', 'scratch_peak_bytes'):
                need(r['profile'][k] <= value['costs'][k], 'complete-domain bound covers actual '+op+' '+k)
    put(out/'cost_table.json', table)
    put(out/'report.json', {'schema': 'micro-calibration76-v1', 'status': 'PASS_BYTE_CORE_AND_WIDE_MICROPROGRAM', 'source': source,
                            'environment': {'python': platform.python_version(), 'platform': platform.platform()},
                            'input_sources': inputs, 'cases': len(records), 'actions': rtl['actions'], 'RTL': rtl, 'ROM': rom,
                            'commands': commands, 'limits': table['limits'], 'full_wide_RTL_FSM': False,
                            'array_data_location': 'existing authorized server only; no model is loaded'})
    artifacts = [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(out.iterdir()) if p.is_file() and p.name != 'manifest.json']
    put(out/'manifest.json', {'schema': 'micro-calibration-run76-v1', 'status': 'PASS_BYTE_CORE_AND_WIDE_MICROPROGRAM', 'source': source, 'artifacts': artifacts})
    print(json.dumps({'status': 'PASS_BYTE_CORE_AND_WIDE_MICROPROGRAM', 'out': str(out), 'cases': len(records), 'actions': rtl['actions']}), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True); p.add_argument('--binding', type=Path, required=True)
    p.add_argument('--verilator', default='/eda/verilator-5.042/bin/verilator'); p.add_argument('--tool-prefix', default='[]')
    p.add_argument('--compiled', type=Path); p.add_argument('--granite', type=Path, action='append', default=[])
    p.add_argument('--random-count', type=int, default=2)
    args = p.parse_args(); need(0 <= args.random_count <= 32, 'bounded random coverage'); run(args)


if __name__ == '__main__': main()
