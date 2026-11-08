"""Prepare a frozen-layout timing harness and explicitly approximate quiet RC.

The updated field solution has per-net upper-source C, not node-resolved
coupled parasitics. Preserve the existing R graph and report three positive
ground-C placements: original quiet-C weights, source end, and sink end.
This is a load/context experiment, never a new calibrated coupled SPEF.
"""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import re

from timing_native import RECEIPT, KINDS, PJ, STD, sha

ROOT = Path('/public/home/yuzelu/PingyangHuang')
PREP = ROOT / 'issue-215-top-pex-zOz2uxIr/job-99157/result'
BASE = ROOT / 'issue-215-top-pex-paPJkRpL/job-99183/result/field.spef'
COMPARE = ROOT / 'issue-222-report-t37412lZ/job-100262/result/net-comparison.json'


def esc(name): return '\\' + name + ' '


def records(path):
    name_map = {}
    header, current, rows = [], None, []
    with path.open() as f:
        for line in f:
            if line.startswith('*D_NET '):
                if current is not None: yield name_map, header, current, rows
                current = line.split()[1]
                rows = []
            elif current is None:
                header.append(line)
                if re.match(r'^\*\d+ ', line):
                    key, value = line.split(maxsplit=1)
                    name_map[key] = value.strip()
            else: rows.append(line)
        if current is not None: yield name_map, header, current, rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native-root', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path(os.environ.get('TIMING_OUT', '.')) / 'result')
    a = p.parse_args(); a.out.mkdir()
    r = json.loads(RECEIPT.read_text())
    bindpath = Path(r['artifacts']['case-binding.json']['path'])
    bind = json.loads(bindpath.read_text())['endpoints']
    audits = {}
    for f in a.native_root.glob('job-*/result/native.json'):
        d = json.loads(f.read_text()); assert d['kind'] not in audits
        d['audit'] = str(f); d['ports'] = str(f.parent / 'ports.tsv'); audits[d['kind']] = d
    assert set(audits) == set(KINDS)
    ports = {}
    for kind, d in audits.items():
        ports[kind[0]] = {bytes.fromhex(n).decode(): direct for n, direct in
                          (row.split() for row in Path(d['ports']).read_text().splitlines())}
    mapping = {}
    for net, endpoints in bind.items():
        for inst, pin in endpoints:
            assert (inst, pin) not in mapping
            mapping[inst, pin] = net
        assert ports[endpoints[0][0][0]][endpoints[0][1]] == 'output'
        assert ports[endpoints[1][0][0]][endpoints[1][1]] == 'input'
    instances = sorted(r['native_masks'])
    external = {}
    connections = {}
    for inst in instances:
        for pin, direct in ports[inst[0]].items():
            if pin in ('VDD', 'VSS'): continue
            if pin == 'clk': value = 'clk'
            elif (inst, pin) in mapping: value = mapping[inst, pin]
            else:
                value = f'ext_{inst}_{pin}'
                external[value] = direct
            connections[inst, pin] = value
    verilog = ['module qwen_timing_harness(' + ', '.join(esc(x) for x in ['clk', *external]) + ');',
               'input clk;']
    verilog += [d + ' ' + esc(n) + ';' for n, d in external.items()]
    verilog += ['wire ' + esc(net) + ';' for net in bind]
    for inst in instances:
        groups = defaultdict(dict); scalar = {}
        for pin in ports[inst[0]]:
            if (inst, pin) not in connections: continue
            match = re.fullmatch(r'(.*)\[(-?\d+)\]', pin)
            if match: groups[match[1]][int(match[2])] = connections[inst, pin]
            else: scalar[pin] = connections[inst, pin]
        args = ['.' + esc(k) + '(' + esc(v) + ')' for k, v in scalar.items()]
        for name, bits in groups.items():
            assert sorted(bits) == list(range(min(bits), max(bits) + 1))
            args.append('.' + esc(name) + '({' + ','.join(esc(bits[i]) for i in sorted(bits, reverse=True)) + '})')
        verilog += [audits[inst[0] + '0']['module'] + ' ' + inst + '(' + ','.join(args) + ');']
    verilog += ['endmodule']
    (a.out / 'harness.v').write_text('\n'.join(verilog) + '\n')

    # Detailed hierarchy and internal parasitics are reused from accepted gates.
    files, spefs, libs = [], [], {str(STD)}
    for kind, d in audits.items():
        if kind in ('P0', 'J0'):
            gate = Path(d['legacy_model']).parent
            original = (gate / 'hierarchy-sta.tcl').read_text()
            files += re.findall(r'read_verilog \{([^}]+)\}', original)
            libs.update(re.findall(r'read_liberty \{([^}]+)\}', original))
            nested = re.findall(r'read_spef -path (\S+) \{([^}]+)\}', original)
        else:
            files += [str(Path(d['native']).with_suffix('.v'))]
            libs.update(d['libraries']); nested = []
        for inst in instances:
            if inst[0] == kind[0]:
                spefs.append((inst, str(Path(d['native']).with_suffix('.spef'))))
                spefs += [(inst + '/' + name, path) for name, path in nested]
    libraries = sorted(libs, key=lambda n: n != str(STD))
    manifest = dict(audits=audits, instances=instances, libraries=libraries,
                    full_verilog=list(dict.fromkeys(files)), full_spefs=spefs,
                    external=external, binding=str(bindpath), harness=str((a.out / 'harness.v').resolve()))

    compare = json.loads(COMPARE.read_text())
    if isinstance(compare, list): comparison = {x['net']: x for x in compare}
    else: comparison = compare
    assert set(comparison) == set(bind)
    # Use the exact old R connectivity, and its accepted field-C node weights.
    source = list(records(PREP / 'resistance.spef'))
    resistance = {}
    for names, header, alias, rows in source:
        section = None; conn = []; edges = []; node_set = set()
        for line in rows:
            if line.startswith(('*CONN', '*CAP', '*RES', '*END')): section = line.split()[0]
            elif section == '*RES':
                _, x, y, value = line.split(); edges.append((x, y, float(value))); node_set.update((x, y))
            if section == '*CONN' and line.startswith('*I '): conn.append(line)
        assert len(conn) == 2 and edges
        resistance[names[alias]] = dict(alias=alias, conn=conn, edges=edges, nodes=node_set)
    # The accepted SPEF stores a mutual capacitor once, in the lower-index
    # net section. Its grounded quiet projection loads BOTH terminal nodes.
    weights_by_node = defaultdict(float)
    base_header = None
    for names, header, alias, rows in records(BASE):
        base_header = header
        section = None
        for line in rows:
            if line.startswith(('*CONN', '*CAP', '*RES', '*END')): section = line.split()[0]
            elif section == '*CAP':
                words = line.split(); assert len(words) in (3, 4)
                for node in words[1:-1]: weights_by_node[node] += float(words[-1])
    outputs = {name: (a.out / (name + '.spef')).open('x') for name in
               ('quiet-baseline', 'quiet-updated', 'quiet-updated-source', 'quiet-updated-sink')}
    inventory = []
    try:
        for names, header, alias, rows in source:
            net = names[alias]; old = resistance[net]; assert alias == old['alias']
            if not inventory:
                assert dict(re.findall(r'(?m)^(\*\d+) (\S+)\s*$', ''.join(base_header))) == names
                for f in outputs.values(): f.write(''.join(header).replace('"qwen_switch_upper"', '"qwen_timing_harness"'))
            weights = {node: weights_by_node[node] for node in old['nodes'] if weights_by_node[node] > 0}
            total = sum(weights.values()); assert total > 0
            row = comparison[net]
            # The comparison uses fF; original SPEF uses pF.
            before = row['baseline_spef_total_ff'] / 1000
            after = row['upper_source_total_ff'] / 1000
            assert abs(total - before) <= 2e-5 * max(before, .001), (net, total, before)
            terminals = {}
            for line in old['conn']:
                w = line.split(); terminals[w[2]] = w[1]
            assert set(terminals) == {'I', 'O'}
            cases = {'quiet-baseline': (before, weights), 'quiet-updated': (after, weights),
                     'quiet-updated-source': (after, {terminals['O']: 1.}),
                     'quiet-updated-sink': (after, {terminals['I']: 1.})}
            for name, (cap, distribution) in cases.items():
                f = outputs[name]; f.write(f'*D_NET {alias} {cap:.14g}\n*CONN\n' + ''.join(old['conn']) + '*CAP\n')
                norm = sum(distribution.values())
                for i, (node, value) in enumerate(distribution.items(), 1):
                    f.write(f'{i} {node} {cap * value / norm:.14g}\n')
                f.write('*RES\n')
                for i, (x, y, value) in enumerate(old['edges'], 1): f.write(f'{i} {x} {y} {value:.14g}\n')
                f.write('*END\n\n')
            inventory.append(dict(net=net, before_pf=before, after_pf=after, nodes=len(old['nodes']), edges=len(old['edges'])))
    finally:
        for f in outputs.values(): f.close()
    assert len(inventory) == 2491
    manifest.update(net_count=2491, resistance_edges=sum(x['edges'] for x in inventory),
                    inputs={str(p): sha(p) for p in (BASE, PREP / 'resistance.spef', COMPARE, bindpath)},
                    upper_rc={name: dict(path=str((a.out / (name + '.spef')).resolve()), sha256=sha(a.out / (name + '.spef'))) for name in outputs},
                    assumptions=['Quiet other electrodes; full field upper-source total C projected to grounded C.',
                                 'Updated C node locations use old accepted quiet-C weights; source/sink limits are explicit sensitivities.',
                                 'Original internal SPEF unchanged. Shared M10 landing remains in both archived models, common to cases.',
                                 'Ideal common parent clock is an analysis harness; no missing physical system route is fabricated.',
                                 'This can reject a macro abstraction in the tested context; it cannot certify full native coupling or general SI.'])
    (a.out / 'prepare.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (a.out / 'nets.json').write_text(json.dumps(inventory, indent=2) + '\n')
    print(json.dumps(dict(nets=len(inventory), instances=len(instances), resistance_edges=manifest['resistance_edges'])), flush=True)


if __name__ == '__main__': main()
