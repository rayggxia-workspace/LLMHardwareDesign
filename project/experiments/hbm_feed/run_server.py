"""Reproducible Slurm-only real-RTL/HBM-architecture experiment runner."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SHA = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def profiles():
    runs = []
    def add(name, **kw):
        runs.append(dict(name=name, options=kw))
    for n in (2, 4, 8, 16):
        for channels in sorted({1, min(n // 2, 4)}):
            add(f'scale-s{n}-ch{channels}', active=n, groups=n // 2, channels=channels)
    for credits in (1, 2, 8, 32):
        for queue in (4, 64):
            add(f'credit-{credits}-q{queue}', active=8, groups=4, channels=4,
                credits=credits, queue=queue)
    for period, phase in ((5, 1), (6, 0), (6, 1), (10, 3), (15, 2)):
        add(f'clock-{period}-phase{phase}', period=period, phase=phase)
    for width in (128, 256, 512):
        add(f'width-{width}', active=8, groups=4, channels=1, width=width, credits=32)
    for burst in (1, 16):
        add(f'fair-burst-{burst}', active=8, groups=4, channels=1, burst=burst, credits=32)
    add('held-s0', active=8, groups=4, channels=2, stall=2000)
    add('coordinated-reset', reset=1)
    add('long-latency', active=8, groups=4, channels=4, latency=100, credits=32)
    add('no-refresh-control', refresh=0)
    for mode in (0, 1, 2):
        for seed in (181, 9001):
            runs.append(dict(name=f'init-{mode}-seed{seed}', options=dict(seed=seed, bulk=128), init=mode))
    return runs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--verilator', default='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator')
    args = parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise SystemExit('Run inside a Slurm allocation.')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    binding = json.loads((ROOT / 'source_binding.json').read_text())
    before = {p: SHA(ROOT / p) for p in binding['files']}
    if before != binding['files']:
        raise RuntimeError('Uploaded source identity mismatch')
    result = dict(pass_all=False, source=binding, job_id=os.environ['SLURM_JOB_ID'],
                  host=platform.node(), python=sys.version, start=time.time(), runs=[], negatives=[])

    def call(command, log):
        with (out / log).open('w') as stream:
            proc = subprocess.run(list(map(str, command)), cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        return proc.returncode

    try:
        result['verilator'] = subprocess.check_output([args.verilator, '--version'], text=True).strip()
        result['verilator_sha256'] = SHA(args.verilator)
        result['gxx'] = subprocess.check_output(['g++', '--version'], text=True).splitlines()[0]
        rtl = [ROOT / p for p in binding['files'] if p.endswith('.sv')]
        cmd = [args.verilator, '--lint-only', '--top-module', 'hbm_s_pool', *rtl]
        if call(cmd, 'lint.log'):
            raise RuntimeError('RTL lint failed; see preserved lint.log')
        cmd = [args.verilator, '--cc', '--exe', '--build', '-j', '4', '--assert',
               '--x-initial', 'unique', '--x-assign', 'unique', '--top-module', 'hbm_s_pool',
               '--Mdir', out / 'obj', '-CFLAGS', '-std=c++17 -O1 -Wall -Wextra',
               *rtl, HERE / 'test_hbm.cpp']
        if call(cmd, 'build.log'):
            raise RuntimeError('Verilator/C++ build failed; see preserved build.log')
        exe = out / 'obj/Vhbm_s_pool'
        result['executable_sha256'] = SHA(exe)
        spec = profiles()
        (out / 'profiles.json').write_text(json.dumps(spec, indent=2) + '\n')

        def trial(p):
            log = p['name'] + '.log'
            command = [exe, f'+verilator+rand+reset+{p.get("init", 2)}',
                       f'+verilator+seed+{p["options"].get("seed", 181)}']
            command += [f'--{k}={v}' for k, v in p['options'].items()]
            if call(command, log):
                raise RuntimeError(f'Functional case failed: {log}')
            data = json.loads((out / log).read_text().splitlines()[-1])
            if not data['pass']:
                raise RuntimeError(f'Non-passing result: {log}')
            return dict(name=p['name'], init=p.get('init', 2), command=list(map(str, command)),
                        log=log, log_sha256=SHA(out / log), **data)

        # Exactly four independent processes under the allocated four CPUs.
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for row in pool.map(trial, spec):
                result['runs'].append(row)
                (out / 'partial.json').write_text(json.dumps(result, indent=2) + '\n')
        negatives = [
            ('corrupt-payload', ['--corrupt=1'], 'S write ACK payload mismatch'),
            ('corrupt-tag', ['--badtag=1'], 'response routed to wrong S/tag'),
            ('bad-destination', ['--active=17'], 'invalid S/group destination configuration'),
            ('bad-extent', ['--bulk=897'], 'invalid burst/address extent'),
            ('zero-credit', ['--credits=0'], 'invalid finite capacity'),
        ]
        for name, options, expected in negatives:
            log = name + '.log'
            code = call([exe, *options], log)
            text = (out / log).read_text()
            if code == 0 or expected not in text:
                raise RuntimeError(f'Negative control was not rejected correctly: {name}')
            result['negatives'].append(dict(name=name, exit_code=code,
                                           expected=expected, log=log, log_sha256=SHA(out / log)))
        result['source_unchanged'] = before == {p: SHA(ROOT / p) for p in before}
        if not result['source_unchanged']:
            raise RuntimeError('Source changed during execution')
        result['checks'] = sum(p['checks'] for p in result['runs'])
        result['matrices'] = sum(p['matrices'] for p in result['runs'])
        result['pass_all'] = True
    except Exception as exc:
        result['error'] = repr(exc)
        raise
    finally:
        result['finish'] = time.time()
        result['log_hashes'] = {p.name: SHA(p) for p in out.glob('*.log')}
        (out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: result.get(k) for k in ('pass_all', 'job_id', 'checks', 'matrices', 'error')}, indent=2))


if __name__ == '__main__':
    main()
