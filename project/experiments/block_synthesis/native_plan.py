"""Generate and replay a plan on the pinned, real U/E/16KiB-S RTL.

This is a native-service integration test, not an LLM benchmark. The original
accepted operands are retained. No off-chip or LC timing is inferred here.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re

from solver import optimize
from verify import verify


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('qualification', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    measurements = defaultdict(set)
    log = a.qualification / 'native.log'
    for lane, meta, count, store, ticks in re.findall(
            r'PROFILE kind=service lane=(\d+) meta=(\w+) sources=(\d+) store=(\d+) ticks=(\d+)', log.read_text()):
        measurements[int(lane), int(meta, 16), int(count), int(store)].add(int(ticks))
    times = measurements[0, 0, 2, 1]
    if len(times) != 1 or log.read_text().count('PASS U native') != 3:
        raise ValueError('missing consistent three-initial-state native ADD qualification')
    source = a.qualification / 'source'
    s = source / 'project/rtl/s_sram/local_s_base.sv'
    text = s.read_text()
    address_bits = int(re.search(r'\[(\d+):0\]\s+req_addr', text).group(1)) + 1
    h = {'external': 'MEM', 'sites': {'U0.S': {'words': 1 << address_bits}},
         'resources': {'U0.E': 1, 'U0.S.port': 1, 'U0.service-client': 1},
         'services': {'U0.E.add': {'op': 'AddSat', 'numeric': 's16-saturate-no-rescale',
             'site': 'U0.S', 'ticks': next(iter(times)), 'qualified': True,
             'input_words': [1, 1], 'output_words': [1],
             'resources': ['U0.E', 'U0.S.port', 'U0.service-client']}},
         'routes': {}, 'nets': {},
         'evidence': {'kind': 'native group RTL, client-driver boundary', 'log_sha256': digest(log),
                      'scope': 'No DDR/HBM, parent LC or physical/top-level timing qualification'}}
    g = {'tasks': [], 'values': {}, 'outputs': ['d']}
    initial = dict(x=17, y=25, z=2, w=3)
    expected = dict(initial)
    for name in initial:
        g['values'][name] = {'words': 1, 'site': 'U0.S'}
    for tid, ins in [('a', ['x', 'y']), ('b', ['z', 'w']), ('c', ['a', 'b']), ('d', ['c', 'a'])]:
        g['tasks'].append({'id': tid, 'op': 'AddSat', 'numeric': 's16-saturate-no-rescale',
                           'inputs': ins, 'outputs': [tid]})
        g['values'][tid] = {'producer': tid, 'words': 1}
        expected[tid] = max(-32768, min(32767, sum(expected[n] for n in ins)))
    g['values']['d']['output_site'] = 'U0.S'
    plan = optimize(g, h, seconds=10, rounds=2)
    audit = verify(g, h, plan)
    allocations = {v['value']: v for v in plan['allocations']}
    bench = (source / 'project/experiments/pu_leaf_base/tb_pu_u_group.sv').read_text()
    bench = bench[:bench.index('    initial begin')]
    commands = ['    initial begin', '        time began;', '        repeat (2) tick();', '        reset=0;']
    for name, number in initial.items():
        commands.append(f"        write_word(10'd{allocations[name]['address']}, {{8{{16'd{number}}}}});")
    commands.append('        began=$time;')
    descriptors = []
    for tid, row in sorted(plan['tasks'].items(), key=lambda kv: kv[1]['start']):
        t = next(t for t in g['tasks'] if t['id'] == tid)
        srcs = [allocations[n]['address'] for n in t['inputs']]
        dst = allocations[tid]['address']
        commands += [f"        execute(0,0,2,{{10'd0,10'd{srcs[1]},10'd{srcs[0]}}},1,10'd{dst},answer);",
                     f"        if (answer !== {{8{{16'd{expected[tid]}}}}}) $fatal(1,\"generated {tid} result differs\");"]
        # These are the exact #195 adapter descriptor fields, not an MC/LC
        # image. Hardware PC/PM fetch and their latency remain a separate gate.
        descriptors.append({'task': tid, 'native_op': 0x100, 'native0': 2 << 2 | 1 << 4 | dst << 5,
                            'native1': srcs[0] | srcs[1] << 10, 'native2': 0, 'native3': 0})
    commands += [f"        if (($time-began)/10 != {plan['makespan']}) $fatal(1,\"generated schedule timing differs\");",
                 f"        expect_word(10'd{allocations['d']['address']},{{8{{16'd{expected['d']}}}}});",
                 f'        $display("GENERATED_PLAN_PASS tasks={len(g["tasks"])} cycles={plan["makespan"]} S_words={1 << address_bits}");',
                 '        $finish;', '    end', 'endmodule']
    (a.output / 'tb_pu_u_group.sv').write_text(bench + '\n'.join(commands) + '\n')
    for name, obj in [('graph', g), ('hardware', h), ('plan', plan), ('audit', audit), ('native-descriptors', descriptors)]:
        (a.output / (name + '.json')).write_text(json.dumps(obj, indent=2) + '\n')
    (a.output / 'input.sha256').write_text('\n'.join(f'{digest(v)}  {v}' for v in [s, log]) + '\n')
    print(json.dumps({'native_integration_test': True, 'tasks': len(g['tasks']), 'predicted_cycles': plan['makespan']}))


if __name__ == '__main__':
    main()
