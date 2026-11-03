"""Measure actual one/16-thread cell models with identical independent scoreboards."""
from pathlib import Path
import argparse, concurrent.futures, hashlib, json, os, subprocess, time

p = argparse.ArgumentParser()
p.add_argument('--single', type=Path, required=True)
p.add_argument('--multi', type=Path, required=True)
p.add_argument('--netlist', type=Path, required=True)
p.add_argument('--capacity', type=int, choices=[256,1024], default=256)
a = p.parse_args()
O = Path.cwd() / 'benchmark'
O.mkdir(exist_ok=False)
C = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt003/results/corpus')
M = json.loads((C / 'MANIFEST.json').read_text())
sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
cpu = sorted(os.sched_getaffinity(0))
assert len(cpu) >= 32
bindings = {}
for label, source in [('single', a.single), ('multi', a.multi)]:
    dat = source / 'engine/Vr_stream_local__verFiles.dat'
    assert str(a.netlist) in dat.read_text() and str(source / 'cells.v') in dat.read_text()
    binding = {'inputs': {str(a.netlist): sha(a.netlist), 'cells.v': sha(source / 'cells.v')}, 'verfiles_sha256': sha(dat)}
    bindings[label] = binding
assert bindings['single']['inputs'] == bindings['multi']['inputs']

def run(label):
    source = a.single if label == 'single' else a.multi
    cc = cpu[:16] if label == 'single' else cpu[16:32]
    rows = []
    for n in [0, 3, 9]:
        case = M['cases'][n]
        inp = C / case['path']
        assert sha(inp) == case['sha256']
        log = O / (label + '-' + str(n) + '.log')
        cmd = ['taskset', '-c', ','.join(map(str, cc)), str(source / 'engine/Vr_stream_local'), str(inp), '+verilator+rand+reset+2', '+verilator+seed+168']
        start = time.monotonic()
        with log.open('w') as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=True)
        result = json.loads(log.read_text())
        assert result['passed'] is True and result['words']==a.capacity
        rows.append(dict(case=n, seconds=time.monotonic()-start, result=result, log_sha256=sha(log)))
    return rows

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    rows = dict(zip(['single', 'multi'], pool.map(run, ['single', 'multi'])))
assert [r['result'] for r in rows['single']] == [r['result'] for r in rows['multi']]
(O / 'receipt.json').write_text(json.dumps(dict(passed=True, bindings=bindings, rows=rows, binaries={label: sha(source / 'engine/Vr_stream_local') for label, source in [('single', a.single), ('multi', a.multi)]}, scope='Measured simulation scheduling only; no additional hardware qualification.'), indent=2)+'\n')
