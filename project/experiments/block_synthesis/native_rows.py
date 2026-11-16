"""Generate real U RTL row programs and a virtual-memory algorithm case.

The 2048-element RMS row checks streaming statistics/replay at an LLM hidden
dimension; it is a native integration test, not a small-parameter LLM benchmark.
"""
import argparse
import hashlib
import json
from pathlib import Path

from emit import emit
from lowering import lower_rows
from native_catalog import build_catalog
from run import compile_model
from solver import optimize
from verify import verify


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('qualification', type=Path)
    p.add_argument('memory_source', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    source = a.qualification / 'source'
    addr_text = (source / 'project/rtl/s_sram/local_s_base.sv').read_text()
    import re
    capacity = 1 << (int(re.search(r'\[(\d+):0\]\s+req_addr', addr_text).group(1)) + 1)
    h = build_catalog((a.qualification / 'native.log').read_text(), a.memory_source.read_text(),
                      sites={'U0': {'words': capacity, 'memory_group': 0}}, row_lengths=(8, 16, 2048))
    model = {'tasks': [
        {'id': 'rms', 'op': 'RMSNorm', 'numeric': 'n-rms-q6.10-gamma-q6.10',
         'inputs': ['x', 'gamma', 'epsilon'], 'outputs': ['normalized']},
        {'id': 'soft', 'op': 'Softmax', 'numeric': 'n-softmax-q6.10-to-q1.14',
         'inputs': ['scores'], 'outputs': ['probability']},
        {'id': 'residual', 'op': 'AddSat', 'numeric': 's16-saturate-no-rescale',
         'inputs': ['normalized', 'x'], 'outputs': ['y']}],
        'values': {'x': {'shape': [1, 2048]}, 'gamma': {'shape': [2048]}, 'epsilon': {'shape': []},
                   'normalized': {'shape': [1, 2048]}, 'scores': {'shape': [1, 16]}, 'y': {'shape': [1, 2048]},
                   'probability': {'shape': [1, 16]}}, 'outputs': ['y', 'probability'],
        'source': 'native integer N interface semantics; not a relabeled FLOAT ONNX'}
    # Algorithm evaluation includes the virtual memory operations. No physical
    # data preconnections, deployment images or real DMA replay are required.
    virtual = compile_model(model, h, seconds=2, rounds=1)
    if virtual['status'] != 'planned':
        raise ValueError(virtual)
    write(a.output / 'virtual-result.json', virtual)
    g, = lower_rows(model, h)
    for value in g['values'].values():
        if 'producer' not in value:
            value['site'] = 'U0.S'
        if 'output_site' in value:
            value['output_site'] = 'U0.S'
    plan = optimize(g, h, seconds=2, rounds=0)
    check = verify(g, h, plan)
    alloc = {v['value']: v for v in plan['allocations'] if v['value'] is not None}
    bench = (source / 'project/experiments/pu_leaf_base/tb_pu_u_group.sv').read_text()
    bench = bench[:bench.index('    initial begin')]
    lines = ['    initial begin', '        time began;', '        repeat (2) tick();', '        reset=0;']
    for name, value in g['values'].items():
        if 'producer' in value:
            continue
        number = 0 if value['tensor'] == 'scores' else 1 if value['tensor'] == 'epsilon' else 1024
        payload = "128'd1" if value['tensor'] == 'epsilon' else f"{{8{{16'd{number}}}}}"
        for i in range(value['words']):
            lines.append(f"        write_word(10'd{alloc[name]['address'] + i},{payload});")
    lines.append('        began=$time;')
    descriptors = []
    for tid, taskrow in sorted(plan['tasks'].items(), key=lambda r: r[1]['start']):
        task = next(t for t in g['tasks'] if t['id'] == tid)
        s = h['services'][taskrow['service']]
        bases = [alloc[n]['address'] for n in task['inputs']]
        dst = alloc[task['outputs'][0]]['address']
        scratch = next((r['address'] for r in plan['allocations'] if r['value'] is None and r['id'] == tid + ':scratch:' + taskrow['service']), None)
        for step in s['native_program']:
            op, i = step['meta'] & 15, step.get('chunk', 0)
            src0 = src1 = 0
            if step['lane'] == 0:
                src0, src1 = bases[0] + i, bases[1] + i
            elif op == 0 and step['sources']:
                src0 = bases[2]
            elif op in (1, 3, 5):
                src0 = bases[0] + i
                if op == 5:
                    src1 = bases[1] + i
            elif op == 6:
                src0 = scratch + i
            target = scratch + i if op == 3 else dst + i
            lines.append(f"        execute({step['lane']},64'h{step['meta']:x},2'd{step['sources']},{{10'd0,10'd{src1},10'd{src0}}},1'b{step['store']},10'd{target},answer);")
            descriptors.append({'task': tid, **step, 'src_words': [src0, src1], 'dst_words': target})
    lines.append(f"        if (($time-began)/10 != {plan['makespan']}) $fatal(1,\"row program timing differs\");")
    for name in g['outputs']:
        expected = 2048 if g['values'][name]['tensor'] == 'y' else 1024
        for i in range(g['values'][name]['words']):
            lines.append(f"        expect_word(10'd{alloc[name]['address'] + i},{{8{{16'd{expected}}}}});")
    lines += [f'        $display("NATIVE_ROWS_PASS rms_elements=2048 softmax_elements=16 residual_elements=2048 cycles={plan["makespan"]}");',
              '        $finish;', '    end', '    initial begin #10000000; $fatal(1,"row watchdog"); end', 'endmodule']
    (a.output / 'tb_pu_u_group.sv').write_text(bench + '\n'.join(lines) + '\n')
    for name, obj in [('model', model), ('graph', g), ('hardware', h), ('plan', plan), ('verification', check),
                      ('native-command-program', descriptors), ('outputs', emit(g, h, plan))]:
        write(a.output / (name + '.json'), obj)
    write(a.output / 'source-bindings.json', {'qualification_log_sha256': hashlib.sha256((a.qualification / 'native.log').read_bytes()).hexdigest(),
        'memory_source_sha256': hashlib.sha256(a.memory_source.read_bytes()).hexdigest(),
        'capacity_words_from_actual_rtl': capacity})
    print(json.dumps({'native_cycles': plan['makespan'], 'virtual_cycles': virtual['plan']['makespan'],
                      'virtual_external_words': virtual['plan']['external_words'],
                      'data_preconnections': sum(bool(n.get('fixed')) for n in h['nets'].values()),
                      'required_internal_channel_bundles': len(plan['nets'])}))


if __name__ == '__main__':
    main()
