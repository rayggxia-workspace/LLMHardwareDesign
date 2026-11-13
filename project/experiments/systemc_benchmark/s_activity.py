"""Ordinary private-S read/write activity on both accepted routed variants.

Zero-delay bank view supplies functional memory, original bank Liberty supplies
power. This sample omits feeder traffic, whole-model activity and glitches.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from s_functional_bank import create


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def call(args, log):
    with log.open('w') as f:
        run = subprocess.run(list(map(str, args)), stdout=f, stderr=subprocess.STDOUT)
    if run.returncode:
        raise RuntimeError('command failed: ' + str(log))


def functional(log):
    rows = [json.loads(line[len('FUNCTIONAL '):]) for line in log.read_text().splitlines()
            if line.startswith('FUNCTIONAL ')]
    if len(rows) != 1 or not rows[0]['timing']['passed']:
        raise ValueError('missing passing functional receipt')
    return rows[0]


def main():
    root = Path.cwd()
    if (os.environ.get('SLURM_NTASKS'), os.environ.get('SLURM_CPUS_PER_TASK')) != ('6', '10'):
        raise ValueError('six tasks by ten cores required')
    base = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign')
    runs = base / 'issue-200-compact-local-s'
    views = {'base': runs / 'run08-base0/results/0/flow/results/nangate45/local_s_base/base',
             'p': runs / 'run10-delay1/results/4/flow/results/nangate45/local_s_p/base'}
    expected = {'base': 'add5e99b97b471d35ef6c1eb3161821968172a96af4feb130fd4ca45217254fc',
                'p': 'b93d064cb07d3978efe280cbddec91fb2c24d74c932078a808680705ca01e32d'}
    bank = base / 'issue-155/bank-views-011/generation/bank'
    bank_v = bank / 's_sram_256x128_freepdk45.v'
    bank_lib = bank / 's_sram_256x128_freepdk45_TT_1p1V_25C.lib'
    if sha(bank_lib) != '47f8de1c22d27beb51982c73ab745e1f3f2b5a7819e53bcb6da73980ce077189':
        raise ValueError('original SRAM characterization changed')
    for kind, view in views.items():
        if sha(view / '6_final.v') != expected[kind]:
            raise ValueError('accepted S netlist changed')
    functional_view = root / 'bank-functional.v'
    bank_receipt = create(bank_v, functional_view)
    (root / 'bank-view.json').write_text(json.dumps(bank_receipt, indent=2) + '\n')
    lib = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    files = [lib, bank_lib, bank_v]
    files += [view / ('6_final.' + suffix) for view in views.values() for suffix in ('v', 'odb', 'sdc', 'spef')]
    files += [p for p in root.iterdir() if p.suffix in ('.py', '.cpp', '.sv', '.tsv', '.sbatch')]
    inputs = {str(p): sha(p) for p in files}
    call(['yosys', '-Q', '-p', 'read_liberty -ignore_miss_func -ignore_miss_dir %s; write_verilog -noattr cells.v' % lib],
         root / 'cells.log')
    verilator = '/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'

    def build(config):
        variant, kind = config
        top = 'local_s_' + variant
        sources = ([root / (top + '.sv'), root / 'block_feed_s16k_sram.sv'] if kind == 'rtl'
                   else [views[variant] / '6_final.v', root / 'cells.v'])
        if variant == 'p' and kind == 'rtl':
            sources.append(root / 'block_feed_loader.sv')
        out = root / ('obj-' + variant + '-' + kind)
        call([verilator, '--cc', '--exe', '--build', '-j', '10', '--trace', '--trace-depth', '2',
              '--x-initial', 'unique', '--x-assign', 'unique', '--timescale', '1ps/1ps',
              '--top-module', top, '-Wno-fatal', '--output-split', '10000',
              '--output-split-cfuncs', '500', '--output-groups', '0', '--Mdir', out,
              '-CFLAGS', '-std=c++17 -O1' + (' -DS_FEEDER' if variant == 'p' else ''),
              *sources, functional_view, root / 's_activity.cpp'], root / ('build-' + variant + '-' + kind + '.log'))
        return config, out / ('V' + top)

    # Four concurrent ten-core builds use 40 of the allocated 60 cores.
    with ThreadPoolExecutor(max_workers=4) as pool:
        binaries = dict(pool.map(build, [(v, k) for v in views for k in ('rtl', 'gate')]))
    patterns = ('read', 'write', 'mixed')

    def worker(index):
        variant, pattern = ('base', 'p')[index // 3], patterns[index % 3]
        out = root / (variant + '-' + pattern)
        out.mkdir(exist_ok=False)
        receipts = {}
        for kind in ('rtl', 'gate'):
            for init, seed in ((1, 143), (2, 143), (2, 144)):
                name = '%s-active-%d-%d' % (kind, init, seed)
                log = out / (name + '.log')
                call([binaries[variant, kind], root / 'operands.tsv', out / (name + '.vcd'), 'active', pattern,
                      '+verilator+rand+reset+%d' % init, '+verilator+seed+%d' % seed], log)
                receipts[name] = functional(log)
                (out / (name + '.json')).write_text(json.dumps(receipts[name]) + '\n')
        reference = receipts['rtl-active-1-143']['timing']
        if any(row['timing'] != reference for row in receipts.values()):
            raise ValueError('RTL/netlist/three-initial-state timing differs')
        log = out / 'gate-idle.log'
        call([binaries[variant, 'gate'], root / 'operands.tsv', out / 'gate-idle.vcd', 'idle', pattern,
              '+verilator+rand+reset+1', '+verilator+seed+143'], log)
        idle_receipt = functional(log)
        if idle_receipt['timing']['window_ps'] != reference['window_ps']:
            raise ValueError('active and idle duration differs')
        (out / 'gate-idle.json').write_text(json.dumps(idle_receipt) + '\n')
        reports = {}
        for name in ('active-1-143', 'idle'):
            call([sys.executable, root / 'analyze_activity.py', views[variant], lib,
                  out / ('gate-' + name + '.vcd'), out / ('gate-' + name + '.json'),
                  out / ('power-' + name), '--scope', 'dut/local_s_' + variant, '--cores', '10',
                  '--escape-sta-backslashes',
                  '--extra-lib', bank_lib, '--sample-label', 'representative scalar S ordinary port'],
                 out / ('power-' + name + '.log'))
            reports[name] = json.loads((out / ('power-' + name) / 'receipt.json').read_text())
        active, idle = [reports[name]['power_w']['total'] for name in ('active-1-143', 'idle')]
        delta_j = (active - idle) * reference['window_ps'] * 1e-12
        record = {'variant': variant, 'pattern': pattern, 'timing': reference,
                  'gate_rtl_three_initials_equal': True,
                  'incremental_window_j': delta_j, 'idle_w': idle,
                  'negative_subtraction': delta_j < 0, 'reports': reports,
                  'energy_qualified': False, 'full_model_energy_qualified': False,
                  'limits': ['ordinary port only; feeder inactive', 'representative scalar data, not full trace',
                             'read/write coefficients require fit and mixed holdout check',
                             'unannotated pins not yet classified', 'zero-delay gate view omits glitches',
                             'SRAM original TT characterization boundary retained',
                             'LC/DMA/clock above S and DDR absent']}
        (out / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
        return record

    with ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(worker, range(6)))
    (root / 's-calibration.json').write_text(json.dumps({'inputs_sha256': inputs,
        'records': records, 'bank_view': bank_receipt, 'full_model_energy_qualified': False}, indent=2) + '\n')


if __name__ == '__main__':
    main()
