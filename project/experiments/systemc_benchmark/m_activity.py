"""Measure true old220 scalar-M operands on RTL and routed gate netlist.

This is one calibration ingredient, never complete Qwen energy. Every routed
netlist simulation also checks exact S64 outputs against independent arithmetic.
"""
from concurrent.futures import ThreadPoolExecutor
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def call(command, log, cwd=None):
    with log.open('w') as stream:
        result = subprocess.run(list(map(str, command)), cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError('command failed: ' + str(log))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--physical-dir', type=Path)
    p.add_argument('--std-lib', type=Path)
    p.add_argument('--verilator', type=Path)
    p.add_argument('--cores', type=int, default=10)
    p.add_argument('--workers', type=int, default=6)
    p.add_argument('--build-workers', type=int, default=2)
    p.add_argument('--trace-depth', type=int, default=1,
                   help='flat gate netlist top-level physical nets suffice; avoid duplicate cell internals')
    a = p.parse_args()
    if min(a.cores, a.workers, a.build_workers) < 1:
        raise ValueError('positive worker limits required')
    import os
    if os.environ.get('SLURM_NTASKS'):
        budget = int(os.environ['SLURM_NTASKS']) * int(os.environ['SLURM_CPUS_PER_TASK'])
        if a.cores * max(a.workers, a.build_workers) > budget:
            raise ValueError('worker limits exceed Slurm allocation')
    root = Path.cwd()
    base = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign')
    gate = a.physical_dir or base / 'issue-187-p16-j16/005-leaf-views/inputs/M'
    std = a.std_lib or Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    # Executed inside ORFS, with a private source snapshot of the accepted RTL.
    inputs = {str(p): sha(p) for p in [gate / ('6_final.' + s) for s in ('v', 'odb', 'sdc', 'spef')] +
              [std, root / 'm_activity.py', root / 'm_activity.cpp', root / 'block_v2_m.sv', root / 'operands/m-operands.tsv']}
    call(['yosys', '-Q', '-p', 'read_liberty -ignore_miss_func -ignore_miss_dir %s; write_verilog -noattr cells.v' % std], root / 'cells.log')
    verilator = a.verilator or Path('/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator')

    def build(kind):
        sources = [root / 'block_v2_m.sv'] if kind == 'rtl' else [gate / '6_final.v', root / 'cells.v']
        out = root / ('obj-' + kind)
        call([verilator, '--cc', '--exe', '--build', '-j', str(a.cores), '--trace',
              '--trace-depth', str(a.trace_depth),
              '--timescale', '1ps/1ps', '--top-module', 'block_v2_m', '-Wno-fatal',
              '--output-split', '10000', '--output-split-cfuncs', '500', '--output-groups', '0',
              '--Mdir', out, '-CFLAGS', '-std=c++17 -O1', *sources, root / 'm_activity.cpp'],
             root / ('build-' + kind + '.log'))
        return out / 'Vblock_v2_m'

    with ThreadPoolExecutor(max_workers=a.build_workers) as pool:
        binaries = dict(zip(['rtl', 'gate'], pool.map(build, ['rtl', 'gate'])))
    rows = (root / 'operands/m-operands.tsv').read_text().splitlines()
    if len(rows) != 72:
        raise ValueError('unexpected captured cohort')

    def worker(index):
        out = root / ('sample-%d' % index)
        out.mkdir(exist_ok=False)
        cohort, mode = index // 2, 'active' if index % 2 == 0 else 'idle'
        operands = out / 'operands.tsv'
        operands.write_text('\n'.join(rows[cohort * 24:(cohort + 1) * 24]) + '\n')
        reports = {}
        for kind, binary in binaries.items():
            vcd = out / (kind + '.vcd')
            call([binary, operands, vcd, mode], out / (kind + '.log'))
            text = (out / (kind + '.log')).read_text()
            values = [json.loads(line[9:]) for line in text.splitlines() if line.startswith('ACTIVITY ')]
            if len(values) != 1 or not values[0]['passed']:
                raise ValueError('activity receipt absent')
            durations = [int(v) for v in re.findall(r'^EXECUTE_CYCLES (\d+)$', text, re.M)]
            if not durations or set(durations) != {22}:
                raise ValueError('old220 Execute timing differs from actual driver')
            reports[kind] = values[0]
        if reports['rtl'] != reports['gate']:
            raise ValueError('routed and RTL latency differs')
        vcd = out / 'gate.vcd'
        header = []
        with vcd.open() as f:
            for line in f:
                header.append(line)
                if '$enddefinitions' in line:
                    break
        if '$timescale 1ps $end' not in ''.join(header).replace('\n', ' '):
            raise ValueError('VCD timescale is not ps')
        script = out / 'power.tcl'
        script.write_text('read_liberty {%s}\nread_db {%s}\nread_sdc {%s}\nread_spef {%s}\n' %
                          (std, gate / '6_final.odb', gate / '6_final.sdc', gate / '6_final.spef') +
                          'set_propagated_clock [all_clocks]\n' +
                          'read_vcd -scope TOP/dut {%s}\n' % vcd +
                          'report_activity_annotation\nreport_power\nputs "ACTIVITY_POWER_COMPLETED"\n')
        call(['openroad', '-no_init', '-threads', str(a.cores), '-exit', script], out / 'power.log')
        text = (out / 'power.log').read_text()
        if 'ACTIVITY_POWER_COMPLETED' not in text or re.search(r'(?m)^Error:', text):
            raise ValueError('power command failed')
        record = {'cohort': cohort, 'mode': mode, 'timing': reports['gate'],
                  'scope': 'scalar M only; full energy needs annotation review, integration and all other components',
                  'qualified_full_model_energy': False,
                  'activity': {kind: {'sha256': sha(out / (kind + '.vcd')),
                                      'bytes': (out / (kind + '.vcd')).stat().st_size} for kind in binaries},
                  'power_log_sha256': sha(out / 'power.log')}
        (out / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
        # Preserve compressed VCD as well as a digest of the raw analyzer input.
        for kind in binaries:
            vcd = out / (kind + '.vcd')
            with vcd.open('rb') as src, gzip.open(str(vcd) + '.gz', 'wb') as dst:
                for chunk in iter(lambda: src.read(4 * 1024 * 1024), b''):
                    dst.write(chunk)
        return record

    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        records = list(pool.map(worker, range(6)))
    (root / 'm-calibration.json').write_text(json.dumps({'inputs': inputs, 'records': records,
        'trace_depth': a.trace_depth, 'qualified_full_model_energy': False}, indent=2) + '\n')
    print(json.dumps({'samples': len(records), 'exact_outputs_passed': True, 'full_model_energy_qualified': False}))


if __name__ == '__main__':
    main()
