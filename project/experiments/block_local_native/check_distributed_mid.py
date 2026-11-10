"""Compute-job-only quantizer -> shared link -> actual private S -> A replay."""
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
        raise RuntimeError('RTL simulation requires allocated compute job')
    a.out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    env.pop('VERILATOR_ROOT', None)
    bank = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
    assert hashlib.sha256(bank.read_bytes()).hexdigest() == '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
    local_bank = a.out / bank.name
    local_bank.write_bytes(bank.read_bytes())
    names = (
        'project/rtl/block_local_native/early_copy_epoch_3p.sv',
        'project/rtl/block_local_native/a_scale_directory32.sv',
        'project/experiments/shared_x_control/rtl/early_copy_source_router.sv',
        'project/experiments/block_local_native/real_s_lint.vlt',
        'project/experiments/block_local_native/test_distributed_mid_joint.sv',
        'project/rtl/block_local_native/s32_a16_tile_quantizer.sv',
        'project/rtl/block_local_native/private_a_scaled_frontend.sv',
        'project/rtl/block_local_native/copy_scale_header_tx.sv',
        'project/rtl/block_local_native/copy_scale_header_rx.sv',
        'project/experiments/shared_x_control/rtl/early_copy_3p.sv',
        'project/experiments/shared_x_control/rtl/native_s128_mux3.sv',
        'project/experiments/shared_x_control/rtl/private_a_tile_frontend.sv',
        'project/rtl/s_sram/local_s_base.sv',
        'project/rtl/s_sram/block_feed_s16k_sram.sv')
    build = [a.verilator, '--binary', '--timing', '--assert', '-Wall',
             '--top-module', 'test_distributed_mid_joint', '--timescale-override', '1ns/1ps',
             '--x-initial', 'unique', '--x-assign', 'unique', '-j', '10',
             '--Mdir', str(a.out / 'obj')] + [str(a.source / x) for x in names] + [str(local_bank)]
    with (a.out / 'build.log').open('w') as log:
        subprocess.run(build, env=env, cwd=a.out, stdout=log, stderr=subprocess.STDOUT, check=True)
    results = []
    for initial in (0, 1, 2):
        for mode in (0, 1):
            name = f'mode-{mode}-initial-{initial}.log'
            with (a.out / name).open('w') as log:
                subprocess.run([str(a.out / 'obj/Vtest_distributed_mid_joint'),
                    f'+mode={mode}', f'+seed={a.seed}', f'+verilator+rand+reset+{initial}',
                    f'+verilator+seed+{a.seed}'], env=env, cwd=a.out, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT, check=True)
            text = (a.out / name).read_text()
            assert 'PASS distributed_mid_joint tiles=86 down_sweeps=6 cases=516 actual_banks=16 shared_header_data_wires=1 A_uses=3096 two_live_pairs=258 overwritten_S_words=24768 directory_entries=86 private_S_bytes=16384 extra_SRAM=0' in text
            assert text.count('DISTRIBUTED_MID_REAL_S case=') == 516
            results.append(dict(initial=initial, mode=mode, log=name))
    report = dict(seed=a.seed, results=results,
        hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in a.out.iterdir() if p.is_file()},
        qualification='True 16-bank distributed A16 Mid/directory/COPY/A only; host A16 input, no quantizer/MC/LC/M or 300MHz qualification')
    (a.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
