"""Actual G/S128 probe regression; preserve the original G numeric vectors."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--verilator', required=True)
    a = p.parse_args()
    assert os.environ.get('SLURM_JOB_ID'), 'compute job required'
    a.out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    env.pop('VERILATOR_ROOT', None)
    with (a.out / 'vectors.log').open('w') as log:
        subprocess.run(['python3', '-B', str(a.source / 'project/experiments/w8a16_g/make_vectors.py'),
            '--out', str(a.out)], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    bank = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
    raw = bank.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
    local_bank = a.out / bank.name
    local_bank.write_bytes(raw)
    units = [a.source / name for name in ('project/rtl/block_local_native/g_s128_observed_scale.sv',
        'project/rtl/w8a16_v1/g_s128_frontend.sv')]
    with (a.out / 'lint.log').open('w') as log:
        subprocess.run([a.verilator, '--lint-only', '-Wall', '--top-module', 'g_s128_observed_scale',
            *map(str, units)], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    # Inherited standalone G regression uses testbench-only clock/scoreboard
    # constructs. Every synthesizable new module is separately strict-Wall linted.
    with (a.out / 'build.log').open('w') as log:
        subprocess.run([a.verilator, '--binary', '--timing', '--assert', '--top-module',
            'test_g_observed_scale', '--timescale-override', '1ns/1ps', '--x-initial', 'unique',
            '--x-assign', 'unique', '-j', '10', '--Mdir', str(a.out / 'obj'), *map(str, units),
            str(a.source / 'project/rtl/w8a16_v1/g_s32.sv'),
            str(a.source / 'project/rtl/s_sram/local_s_p.sv'),
            str(a.source / 'project/rtl/s_sram/block_feed_s16k_sram.sv'),
            str(a.source / 'project/rtl/block_feed_v1/block_feed_loader.sv'), str(local_bank),
            str(a.source / 'project/experiments/block_local_native/test_g_observed_scale.sv')],
            env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    for initial in (0, 1, 2):
        for mode in (0, 1, 2, 3, 4):
            path = a.out / f'mode-{mode}-initial-{initial}.log'
            with path.open('w') as log:
                subprocess.run([str(a.out / 'obj/Vtest_g_observed_scale'), f'+mode={mode}',
                    f'+vectors={a.out / "vectors.txt"}', f'+verilator+rand+reset+{initial}',
                    f'+verilator+seed+{a.seed}'], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            assert 'G_SCALE_PASS ' in path.read_text(encoding='utf-8')
    report = dict(passed=True, seed=a.seed, runs=15,
        hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in a.out.iterdir() if p.is_file()},
        qualification='G/S128 actual 128 historical model values, observed scale after true S ACK; no complete FFN, physical adapter, or whole-model qualification')
    (a.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
