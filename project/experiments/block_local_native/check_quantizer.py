"""Slurm-only native quantizer RTL build/regression. No model throughput claim."""
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
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('RTL simulation requires compute job')
    a.out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    env.pop('VERILATOR_ROOT', None)
    rtl = a.source / 'project/rtl/block_local_native/s32_a16_tile_quantizer.sv'
    build = [a.verilator, '--cc', '--exe', '--build', '--assert', '-Wall', '--top-module',
             's32_a16_tile_quantizer', '--x-initial', 'unique', '--x-assign', 'unique', '-j', '10',
             '--Mdir', str(a.out / 'obj'), str(rtl),
             str(a.source / 'project/experiments/block_local_native/test_quantizer.cpp')]
    with (a.out / 'build.log').open('w') as log:
        subprocess.run(build, env=env, cwd=a.out, stdout=log, stderr=subprocess.STDOUT, check=True)
    bank = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
    bank_bytes = bank.read_bytes()
    assert hashlib.sha256(bank_bytes).hexdigest() == '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
    local_bank = a.out / 's_sram_256x128_freepdk45.v'
    local_bank.write_bytes(bank_bytes)
    real_build = [a.verilator, '--binary', '--timing', '--assert', '-Wall', '--top-module',
        'test_quantizer_real_s', '--timescale-override', '1ns/1ps', '--x-initial', 'unique',
        '--x-assign', 'unique', '-j', '10', '--Mdir', str(a.out / 'real-obj'),
        str(a.source / 'project/experiments/block_local_native/real_s_lint.vlt'),
        str(rtl), str(a.source / 'project/experiments/shared_x_control/rtl/native_s128_mux2.sv'),
        str(a.source / 'project/rtl/s_sram/local_s_base.sv'),
        str(a.source / 'project/rtl/s_sram/block_feed_s16k_sram.sv'), str(local_bank),
        str(a.source / 'project/experiments/block_local_native/test_quantizer_real_s.sv')]
    with (a.out / 'real-build.log').open('w') as log:
        subprocess.run(real_build, env=env, cwd=a.out, stdout=log, stderr=subprocess.STDOUT, check=True)
    joint_build = list(real_build)
    joint_build[joint_build.index('test_quantizer_real_s')] = 'test_quant_a_joint'
    joint_build[joint_build.index(str(a.out / 'real-obj'))] = str(a.out / 'joint-obj')
    joint_build[-1] = str(a.source / 'project/experiments/block_local_native/test_quant_a_joint.sv')
    joint_build += [str(a.source / name) for name in (
        'project/rtl/block_local_native/a_scale_directory32.sv',
        'project/rtl/block_local_native/private_a_scaled_frontend.sv',
        'project/experiments/shared_x_control/rtl/native_s128_mux3.sv',
        'project/experiments/shared_x_control/rtl/private_a_tile_frontend.sv')]
    with (a.out / 'joint-build.log').open('w') as log:
        subprocess.run(joint_build, env=env, cwd=a.out, stdout=log, stderr=subprocess.STDOUT, check=True)
    results = []
    for initial in (0, 1, 2):
        path = a.out / ('initial-' + str(initial) + '.log')
        with path.open('w') as log:
            subprocess.run([str(a.out / 'obj/Vs32_a16_tile_quantizer'), str(a.seed), str(initial)],
                           env=env, cwd=a.out, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
        assert path.read_text().startswith('PASS quantizer ')
        results.append(dict(initial=initial, receipt=path.read_text().strip()))
        for mode in (0, 1):
            real_log = a.out / f'real-{mode}-{initial}.log'
            with real_log.open('w') as log:
                subprocess.run([str(a.out / 'real-obj/Vtest_quantizer_real_s'),
                    f'+mode={mode}', f'+seed={a.seed}', f'+verilator+rand+reset+{initial}',
                    f'+verilator+seed+{a.seed}'], env=env, cwd=a.out,
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
            assert 'PASS quantizer_real_s ' in real_log.read_text()
            joint_log = a.out / f'joint-{mode}-{initial}.log'
            with joint_log.open('w') as log:
                subprocess.run([str(a.out / 'joint-obj/Vtest_quant_a_joint'),
                    f'+mode={mode}', f'+seed={a.seed}', f'+verilator+rand+reset+{initial}',
                    f'+verilator+seed+{a.seed}'], env=env, cwd=a.out,
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
            assert 'PASS quant_a_joint ' in joint_log.read_text()
    report = dict(seed=a.seed, results=results, hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in a.out.iterdir() if p.is_file()}, qualification='LC quantizer with real ordinary SRAM banks at functional 10ns clock; not M integration, 300MHz STA, or whole-model qualification')
    (a.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
