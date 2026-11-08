"""Representative scalar compact-E samples, routed-netlist activity and RC.

These are coefficients to audit, not complete-workload/chip energy. Every
sample has an independent integer check and paired matched-state idle window.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def call(args, log):
    with log.open('w') as f:
        result = subprocess.run([str(x) for x in args], stdout=f, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError('command failed: ' + str(log))


def main():
    root = Path.cwd()
    if int(os.environ.get('SLURM_NTASKS', '0')) != 6 or int(os.environ.get('SLURM_CPUS_PER_TASK', '0')) != 10:
        raise ValueError('six-by-ten Slurm allocation required')
    physical = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/release/e_compact')
    if sha(physical / '6_final.v') != 'f08f888f5d8b8d8058a664d9f0aa27a84d12460cff94ef7e437b5904d4763e13':
        raise ValueError('accepted compact E netlist drift')
    lib = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    inputs = {str(p): sha(p) for p in [physical / ('6_final.' + e) for e in ('v', 'odb', 'sdc', 'spef')] +
              [lib, root / 'e_activity.cpp', root / 'e_activity.py', root / 'operands.tsv',
               root / 'block_v2_e.sv', root / 'block_v2_e_compact.sv', root / 'analyze_activity.py']}
    call(['yosys', '-Q', '-p', 'read_liberty -ignore_miss_func -ignore_miss_dir %s; write_verilog -noattr cells.v' % lib], root / 'cells.log')
    verilator = '/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'

    def build(kind):
        sources = ([root / 'block_v2_e_compact.sv', root / 'block_v2_e.sv'] if kind == 'rtl'
                   else [physical / '6_final.v', root / 'cells.v'])
        out = root / ('obj-' + kind)
        call([verilator, '--cc', '--exe', '--build', '-j', '10', '--trace', '--trace-depth', '2',
              '--x-initial', 'unique', '--x-assign', 'unique', '--timescale', '1ps/1ps',
              '--top-module', 'block_v2_e_compact', '-Wno-fatal', '--output-split', '10000',
              '--output-split-cfuncs', '500', '--output-groups', '0', '--Mdir', out,
              '-CFLAGS', '-std=c++17 -O1', *sources, root / 'e_activity.cpp'], root / ('build-' + kind + '.log'))
        return out / 'Vblock_v2_e_compact'

    with ThreadPoolExecutor(max_workers=2) as pool:
        binaries = dict(zip(('rtl', 'gate'), pool.map(build, ('rtl', 'gate'))))
    operands = (root / 'operands.tsv').read_text().splitlines()
    if len(operands) != 72:
        raise ValueError('expected original three cohorts, 24 captured S16 components each')

    def worker(index):
        cohort, op = index // 2, (5, 6)[index % 2]
        out = root / ('cohort-%d-op-%d' % (cohort, op))
        out.mkdir(exist_ok=False)
        operand = out / 'operands.tsv'
        operand.write_text('\n'.join(operands[cohort * 24:(cohort + 1) * 24]) + '\n')
        times = {}
        for kind, binary in binaries.items():
            for init, seed in ((1, 143), (2, 143), (2, 144)):
                mode = 'active'
                name = '%s-%s-%d-%d' % (kind, mode, init, seed)
                vcd = out / (name + '.vcd')
                log = out / (name + '.log')
                call([binary, operand, vcd, mode, op, '+verilator+rand+reset+%d' % init,
                      '+verilator+seed+%d' % seed], log)
                rows = [json.loads(t[len('FUNCTIONAL '):]) for t in log.read_text().splitlines()
                        if t.startswith('FUNCTIONAL ')]
                if len(rows) != 1 or not rows[0]['timing']['passed']:
                    raise ValueError('functional terminal receipt missing')
                times[name] = rows[0]
                (out / (name + '.json')).write_text(json.dumps(rows[0]) + '\n')
        reference = times['rtl-active-1-143']['timing']
        if any(t['timing'] != reference for t in times.values()):
            raise ValueError('RTL/netlist/initial-state timing mismatch')
        idle_vcd = out / 'gate-idle.vcd'
        call([binaries['gate'], operand, idle_vcd, 'idle', op, '+verilator+rand+reset+1',
              '+verilator+seed+143'], out / 'gate-idle.log')
        idle = [json.loads(t[len('FUNCTIONAL '):]) for t in (out / 'gate-idle.log').read_text().splitlines()
                if t.startswith('FUNCTIONAL ')][0]
        if idle['timing']['window_ps'] != reference['window_ps']:
            raise ValueError('active/idle window mismatch')
        (out / 'gate-idle.json').write_text(json.dumps(idle) + '\n')
        reports = {}
        for mode in ('active-1-143', 'idle'):
            call([sys.executable, root / 'analyze_activity.py', physical, lib,
                  out / ('gate-' + mode + '.vcd'), out / ('gate-' + mode + '.json'),
                  out / ('power-' + mode), '--scope', 'dut/block_v2_e_compact', '--cores', '10',
                  '--escape-sta-backslashes',
                  '--sample-label', 'representative scalar compact E'],
                 out / ('power-' + mode + '.log'))
            reports[mode] = json.loads((out / ('power-' + mode) / 'receipt.json').read_text())
        active, idle = (reports[n]['power_w']['total'] for n in ('active-1-143', 'idle'))
        delta = (active - idle) * reference['window_ps'] * 1e-12 / 512
        result = {'cohort': cohort, 'op': op, 'native_timing': reference,
                  'gate_rtl_three_initials_equal': True,
                  'incremental_j_per_command': delta,
                  'negative_subtraction': delta < 0, 'idle_w': idle, 'reports': reports,
                  'operand_sha256': sha(operand),
                  'energy_qualified': False, 'full_model_energy_qualified': False,
                  'limits': ['representative derived operands, not a full E instruction trace',
                             'unannotated pins not yet classified', 'zero-delay gate activity omits glitches',
                             'S/LC/DMA/chip clock and DRAM energy absent']}
        (out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
        return result

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(worker, range(6)))
    (root / 'e-calibration.json').write_text(json.dumps({'inputs_sha256': inputs,
        'records': results, 'full_model_energy_qualified': False}, indent=2) + '\n')


if __name__ == '__main__':
    main()
