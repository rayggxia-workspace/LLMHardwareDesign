"""Slurm-only native range RTL build/regression. No model throughput claim."""
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
    rtl = a.source / 'project/rtl/block_local_native/a_scale_directory32.sv'
    build = [a.verilator, '--cc', '--exe', '--build', '--assert', '-Wall', '--top-module',
             'a_scale_directory32', '--x-initial', 'unique', '--x-assign', 'unique', '-j', '10',
             '--Mdir', str(a.out / 'obj'), str(rtl),
             str(a.source / 'project/experiments/block_local_native/test_scale_directory.cpp')]
    with (a.out / 'build.log').open('w') as log:
        subprocess.run(build, env=env, cwd=a.out, stdout=log, stderr=subprocess.STDOUT, check=True)
    with (a.out / 'scaled-front-lint.log').open('w') as log:
        subprocess.run([a.verilator, '--lint-only', '-Wall', '--top-module', 'private_a_scaled_frontend', str(a.source / 'project/rtl/block_local_native/private_a_scaled_frontend.sv'), str(a.source / 'project/experiments/shared_x_control/rtl/private_a_tile_frontend.sv')], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    results = []
    for initial in (0, 1, 2):
        path = a.out / ('initial-' + str(initial) + '.log')
        with path.open('w') as log:
            subprocess.run([str(a.out / 'obj/Va_scale_directory32'), str(a.seed), str(initial)],
                           env=env, cwd=a.out, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
        assert path.read_text().startswith('PASS scale_directory ')
        results.append(dict(initial=initial, receipt=path.read_text().strip()))
    report = dict(seed=a.seed, results=results, hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in a.out.iterdir() if p.is_file()}, qualification='Finite scale-directory unit; publication true-ACK source and lifetime proofs must be wired in joint LC')
    (a.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
