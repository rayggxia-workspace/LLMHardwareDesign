"""Actual three-P S, G and Mid quantizer lifetime check on allocated node."""
import argparse
import hashlib
import json
import os
import random
import sys
from pathlib import Path
import subprocess


def oracle(root, out, seed):
    sys.path.insert(0, str(root / 'project/experiments/w8a16_g'))
    from reference import packet, rne
    rng = random.Random(seed)
    columns = 11008
    gates = [rng.randrange(-17 << 16, 17 << 16) for _ in range(columns)]
    ups = [rng.randrange(-20 << 16, 20 << 16) for _ in range(columns)]
    mid = []
    for i in range(0, columns, 2):
        result, error = packet(gates[i:i+2], ups[i:i+2], True, 3)
        assert not error
        mid.extend(result)
    def pack(values, width):
        return sum((x % (1 << width)) << (width*i) for i, x in enumerate(values))
    words = [pack(x[i:i+4], 32) for x in (gates, ups) for i in range(0, columns, 4)]
    for i in range(0, columns, 128):
        values = mid[i:i+128]
        peak = max(map(abs, values))
        shift = next(s for s in range(18) if peak <= 32767 << s)
        rounded = [rne(x, shift) for x in values]
        words.extend([shift] + [pack(rounded[k:k+8], 16) for k in range(0, 128, 8)])
    assert len(words) == columns // 2 + columns // 128 * 17
    out.write_text(''.join(f'{word:032x}\n' for word in words), encoding='ascii')


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
    vector_path = a.out / 'vectors.hex'
    oracle(a.source, vector_path, a.seed)
    names = (
        'project/experiments/block_local_native/real_s_lint.vlt',
        'project/experiments/block_local_native/test_ffn_mid_ring_joint.sv',
        'project/rtl/block_local_native/s32_stripe_copy.sv',
        'project/rtl/block_local_native/ffn_gate_up_ring_control.sv',
        'project/rtl/block_local_native/ffn_stripe_commit.sv',
        'project/rtl/block_local_native/quant_mid_s128_router.sv',
        'project/rtl/block_local_native/ffn_gate_up_mid.sv',
        'project/rtl/block_local_native/s32_a16_tile_quantizer.sv',
        'project/rtl/block_local_native/g_s128_observed_scale.sv',
        'project/rtl/w8a16_v1/g_s128_frontend.sv',
        'project/rtl/w8a16_v1/g_s32.sv',
        'project/experiments/shared_x_control/rtl/early_copy_3p.sv',
        'project/experiments/shared_x_control/rtl/native_s128_mux3.sv',
        'project/rtl/s_sram/local_s_base.sv',
        'project/rtl/s_sram/block_feed_s16k_sram.sv')
    build = [a.verilator, '--binary', '--timing', '--assert', '-Wall',
             '--top-module', 'test_ffn_mid_ring_joint', '--timescale-override', '1ns/1ps',
             '--x-initial', 'unique', '--x-assign', 'unique', '-j', '10',
             '--Mdir', str(a.out / 'obj')] + [str(a.source / x) for x in names] + [str(local_bank)]
    with (a.out / 'build.log').open('w') as log:
        subprocess.run(build, env=env, cwd=a.out, stdout=log, stderr=subprocess.STDOUT, check=True)
    results = []
    for initial in (0, 1, 2):
        for mode in (0, 1):
            name = f'mode-{mode}-initial-{initial}.log'
            with (a.out / name).open('w') as log:
                subprocess.run([str(a.out / 'obj/Vtest_ffn_mid_ring_joint'),
                    f'+mode={mode}', f'+vectors={vector_path}', f'+verilator+rand+reset+{initial}',
                    f'+verilator+seed+{a.seed}'], env=env, cwd=a.out, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT, check=True)
            text = (a.out / name).read_text()
            assert 'PASS ffn_mid_ring_joint columns=11008 tiles=86 actual_banks=12 extra_SRAM=0' in text
            assert text.count('FFN_STRIPE mode=') == 58
            assert text.count('FFN_MID mode=') == 86
            results.append(dict(initial=initial, mode=mode, log=name))
    report = dict(seed=a.seed, results=results,
        hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in a.out.iterdir() if p.is_file()},
        qualification='Actual all-11008-column ring, G and 86 owner-S Mid writes; fixture projection inputs, no Down or physical')
    (a.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
