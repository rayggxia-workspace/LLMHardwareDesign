"""Run only inside a Slurm allocation; all writes stay in a fresh output dir."""
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
SOURCES = [
    'project/rtl/block_feed_v1/block_feed_s16k.sv',
    'project/rtl/block_feed_v1/block_feed_loader.sv',
    'project/rtl/block_local_s/block_local_s_arbiter.sv',
    'project/rtl/block_local_s/block_local_s_macro.sv',
    'project/experiments/block_local_s/local_s_pool.sv',
    'project/experiments/block_local_s/test_local_s.cpp',
    'project/experiments/block_local_s/run_server.py',
    'project/experiments/block_local_s/job.sh',
]
SHA = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--verilator', default='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator')
    a = p.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise SystemExit('A real Slurm allocation is required.')
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    before = {name: SHA(ROOT / name) for name in SOURCES}
    binding = json.loads((ROOT / 'source_binding.json').read_text())
    if before != binding['files']:
        raise SystemExit('Uploaded source hashes do not match source_binding.json')
    result = dict(pass_all=False, job_id=os.environ['SLURM_JOB_ID'],
                  host=platform.node(), python=sys.version, source=binding,
                  started=time.time(), outputs=str(out), runs=[])

    def call(cmd, name):
        with (out / name).open('w') as f:
            r = subprocess.run([str(x) for x in cmd], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
        if r.returncode:
            raise RuntimeError(f'{name}: exit {r.returncode}; see preserved log')

    try:
        result['verilator'] = subprocess.check_output([a.verilator, '--version'], text=True).strip()
        result['verilator_sha256'] = SHA(a.verilator)
        result['yosys'] = subprocess.check_output(['yosys', '-V'], text=True).strip()
        rtl = [ROOT / x for x in SOURCES if x.endswith('.sv')]
        call([a.verilator, '--lint-only', '--top-module', 'local_s_pool', *rtl], 'lint.log')
        # Full integration is synthesized through memory collection. Do not map
        # payload RAM to invented SRAM cells or call this physical qualification.
        script = '\n'.join([
            'read_verilog -sv ' + ' '.join(map(str, rtl)),
            'hierarchy -check -top local_s_pool', 'proc', 'opt',
            'memory_collect', 'check -assert', 'stat',
            f'write_json {out / "structure.json"}',
        ]) + '\n'
        (out / 'structure.ys').write_text(script)
        call(['yosys', '-s', out / 'structure.ys'], 'structure.log')
        net = json.loads((out / 'structure.json').read_text())['modules']
        inventory = dict(private_stores=0, arbiters=0, feeders=0, banks=0, payload_bits=0)

        def visit(name):
            for cname, cell in net[name].get('cells', {}).items():
                kind = cell['type']
                if kind == '$mem_v2':
                    q = cell['parameters']
                    width, size = int(q['WIDTH'], 2), int(q['SIZE'], 2)
                    if (width, size) != (128, 256):
                        raise RuntimeError(f'Unexpected payload memory: {width}x{size}')
                    inventory['banks'] += 1
                    inventory['payload_bits'] += width * size
                if kind in net:
                    if cname == 'storage': inventory['private_stores'] += 1
                    if cname == 'local_port': inventory['arbiters'] += 1
                    if cname == 'with_feeder.feeder': inventory['feeders'] += 1
                    visit(kind)
        visit('local_s_pool')
        expected = dict(private_stores=9, arbiters=9, feeders=3, banks=36, payload_bits=1179648)
        if inventory != expected:
            raise RuntimeError(f'Unexpected structural inventory: {inventory}, expected {expected}')
        result['structural_inventory'] = inventory
        (out / 'inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
        arb = ROOT / SOURCES[2]
        for clients in (1, 4, 5):
            script = (f'read_verilog -sv {arb}\n'
                      f'hierarchy -top block_local_s_arbiter -chparam CLIENTS {clients}\n'
                      'synth -top block_local_s_arbiter\ncheck -assert\nstat\n')
            path = out / f'arbiter-{clients}.ys'
            path.write_text(script)
            call(['yosys', '-s', path], f'arbiter-{clients}.log')
        call([a.verilator, '--cc', '--exe', '--build', '-j', '4', '--assert',
              '--x-initial', 'unique', '--x-assign', 'unique', '--top-module', 'local_s_pool',
              '--Mdir', out / 'obj', '-CFLAGS', '-std=c++17 -O1',
              *rtl, ROOT / SOURCES[5]], 'build.log')
        exe = out / 'obj/Vlocal_s_pool'
        result['executable_sha256'] = SHA(exe)

        def trial(pair):
            mode, seed = pair
            name = f'run-init{mode}-seed{seed}.log'
            call([exe, f'+verilator+rand+reset+{mode}', f'+verilator+seed+{seed}', f'--seed={seed}'], name)
            lines = (out / name).read_text().splitlines()
            data = json.loads(lines[-1])
            if not data['pass'] or sum(s.startswith('CASE_PASS') for s in lines) != 7:
                raise RuntimeError(f'Incomplete coverage: {name}')
            return dict(init=mode, log=name, log_sha256=SHA(out / name), **data)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            result['runs'] = list(pool.map(trial, [(m, s) for m in (0, 1, 2) for s in (177, 1001, 9001)]))
        result['source_unchanged'] = before == {name: SHA(ROOT / name) for name in SOURCES}
        if not result['source_unchanged']:
            raise RuntimeError('Source changed during execution')
        result['checks'] = sum(r['checks'] for r in result['runs'])
        result['pass_all'] = True
    except Exception as e:
        result['error'] = repr(e)
        raise
    finally:
        result['finished'] = time.time()
        result['log_hashes'] = {p.name: SHA(p) for p in out.glob('*.log')}
        (out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: result.get(k) for k in ('pass_all', 'job_id', 'checks', 'error')}, indent=2))


if __name__ == '__main__':
    main()
