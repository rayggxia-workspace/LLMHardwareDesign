"""Real grouped RTL DMA validation. C++ only models host, HBM and oracle."""
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
    cases = []
    def add(name, **kw):
        cases.append(dict(name=name, options=kw))
    for groups, per in ((1, 2), (2, 2), (4, 2), (4, 4)):
        for channels in sorted({1, groups}):
            add(f'g{groups}-s{per}-ch{channels}', groups=groups, per=per, channels=channels)
    for credits in (1, 2, 4, 8):
        for queue in (4, 32):
            add(f'credit{credits}-q{queue}', groups=4, per=2, channels=4, credits=credits, queue=queue)
    for period, phase in ((5, 1), (6, 0), (6, 1), (10, 3), (15, 2)):
        add(f'clock{period}-phase{phase}', period=period, phase=phase)
    add('held-s0', groups=4, per=2, channels=2, stall=2000)
    add('held-completion', cplhold=5000)
    add('paused-core', groups=4, per=4, channels=1, credits=8, pause=1)
    add('long-latency', groups=4, per=2, channels=4, credits=8, latency=100)
    add('mixed-directions', groups=4, per=2, channels=2, mixed=1)
    add('coordinated-reset', reset=1)
    add('read-error-drain', error=1)
    add('write-error-drain', error=2)
    add('bad-id-recovery', channels=4, fault=1)
    add('duplicate-recovery', channels=4, fault=2)
    add('upper-boundaries', boundary=1)
    add('full-16k-descriptor', groups=2, per=2, words=1024)
    for mode in (0, 1, 2):
        for seed in (181, 9001):
            cases.append(dict(name=f'init{mode}-seed{seed}', init=mode, options=dict(seed=seed, words=128)))
    return cases


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--verilator', default='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator')
    a = p.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise SystemExit('Slurm allocation required')
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    binding = json.loads((ROOT / 'source_binding.json').read_text())
    before = {name: SHA(ROOT / name) for name in binding['files']}
    if before != binding['files']:
        raise RuntimeError('Source identity mismatch')
    result = dict(pass_all=False, suite='grouped-dma-rtl', source=binding,
                  job_id=os.environ['SLURM_JOB_ID'], host=platform.node(), python=sys.version,
                  started=time.time(), runs=[], negatives=[], synthesis=[])

    def call(cmd, name):
        with (out / name).open('w') as stream:
            proc = subprocess.run(list(map(str, cmd)), cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        return proc.returncode

    try:
        result['verilator'] = subprocess.check_output([a.verilator, '--version'], text=True).strip()
        result['verilator_sha256'] = SHA(a.verilator)
        result['gxx'] = subprocess.check_output(['g++', '--version'], text=True).splitlines()[0]
        result['yosys'] = subprocess.check_output(['yosys', '-V'], text=True).strip()
        rtl = [ROOT / name for name in binding['files'] if name.endswith('.sv')]
        if call([a.verilator, '--lint-only', '--top-module', 'hbm_dma_system', *rtl], 'lint.log'):
            raise RuntimeError('RTL lint failed')
        if call([a.verilator, '--cc', '--exe', '--build', '-j', '4', '--assert',
                 '--x-initial', 'unique', '--x-assign', 'unique', '--top-module', 'hbm_dma_system',
                 '--Mdir', out / 'obj', '-CFLAGS', '-std=c++17 -O1 -Wall -Wextra -Werror',
                 *rtl, HERE / 'test_dma.cpp'], 'build.log'):
            raise RuntimeError('C++/Verilator build failed')
        exe = out / 'obj/Vhbm_dma_system'
        result['executable_sha256'] = SHA(exe)
        cases = profiles()
        (out / 'profiles.json').write_text(json.dumps(cases, indent=2) + '\n')

        def trial(case):
            name = case['name'] + '.log'
            cmd = [exe, f'+verilator+rand+reset+{case.get("init", 2)}',
                   f'+verilator+seed+{case["options"].get("seed", 181)}']
            cmd += [f'--{k}={v}' for k, v in case['options'].items()]
            if call(cmd, name):
                raise RuntimeError(f'RTL test failed: {name}')
            data = json.loads((out / name).read_text().splitlines()[-1])
            if not data['pass']:
                raise RuntimeError(f'Nonpassing case: {name}')
            return dict(name=case['name'], init=case.get('init', 2), log=name,
                        log_sha256=SHA(out / name), **data)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for row in pool.map(trial, cases):
                result['runs'].append(row)
                (out / 'partial.json').write_text(json.dumps(result, indent=2) + '\n')
        negative = 'bad-payload.log'
        code = call([exe, '--corrupt=1'], negative)
        if code == 0 or 'S write payload differs from independent external image' not in (out / negative).read_text():
            raise RuntimeError('Corrupt payload negative control was not rejected')
        result['negatives'].append(dict(name='bad-payload', exit_code=code,
                                       log=negative, log_sha256=SHA(out / negative)))
        core = ROOT / 'project/rtl/hbm_feed/hbm_group_dma.sv'
        for groups, per in ((2, 2), (4, 4)):
            name = f'synth-g{groups}-s{per}'
            script = (f'read_verilog -sv {core}\n'
                      f'chparam -set GROUPS {groups} -set S_PER_GROUP {per} hbm_group_dma\n'
                      'hierarchy -check -top hbm_group_dma\nsynth -top hbm_group_dma -noabc\n'
                      f'check -assert\nstat\nwrite_json {out / (name + ".json")}\n')
            path = out / (name + '.ys')
            path.write_text(script)
            if call(['yosys', '-s', path], name + '.log'):
                raise RuntimeError(f'Synthesis failed: {name}')
            net = json.loads((out / (name + '.json')).read_text())['modules']['hbm_group_dma']
            cells = net.get('cells', {})
            if any(c['type'] in ('$dlatch', '$_DLATCH_P_', '$_DLATCH_N_') for c in cells.values()):
                raise RuntimeError('Unexpected storage latch')
            counts = {}
            for cell in cells.values():
                counts[cell['type']] = counts.get(cell['type'], 0) + 1
            result['synthesis'].append(dict(name=name, groups=groups, per_group=per,
                                            cells=len(cells), types=counts,
                                            netlist_sha256=SHA(out / (name + '.json')),
                                            log_sha256=SHA(out / (name + '.log'))))
        result['checks'] = sum(r['checks'] for r in result['runs'])
        result['matrices'] = sum(r['matrices'] for r in result['runs'])
        result['matrix_values'] = sum(r['matrix_values'] for r in result['runs'])
        result['source_unchanged'] = before == {name: SHA(ROOT / name) for name in binding['files']}
        if not result['source_unchanged']:
            raise RuntimeError('Source changed during run')
        result['pass_all'] = True
    except Exception as exc:
        result['error'] = repr(exc)
        raise
    finally:
        result['finished'] = time.time()
        result['log_hashes'] = {p.name: SHA(p) for p in out.glob('*.log')}
        (out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: result.get(k) for k in ('pass_all', 'job_id', 'checks', 'matrices', 'error')}, indent=2))


if __name__ == '__main__':
    main()
