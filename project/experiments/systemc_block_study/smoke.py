"""Exercise producer ACKs, finite buffers, fusion and native-M shape tails."""
import json,subprocess
from pathlib import Path
from sweep import SIM

trace='''10 7 1
0 64 32 1
1 512 16 1
2 1 32 1
3 32 32 0
4 32 32 0
5 32 32 0
6 64 32 0
7 2 32 0
8 2 16 0
9 1 32 0
3 Dot 32 2 16 32 1 16 0 2 0 1
4 Product 32 2 16 1 1 29 0 2 3 2
5 Add 32 2 16 1 1 0 0 2 4 2
6 View 64 2 32 1 1 0 0 1 5
7 Sum 2 1 2 32 1 0 0 1 6
8 Convert 2 1 2 1 1 0 0 1 7
9 NFactor 1 1 1 2 1 0 0 1 8
'''
Path('generated/smoke.trace').write_text(trace)
results=[]
for profile in ['packed_k1','packed_k32','reference_io','reference_io_w8','unfused']:
    p=subprocess.run(SIM+['generated/smoke.trace',profile],capture_output=True,text=True)
    Path('generated/smoke-'+profile+'.log').write_text(p.stdout+p.stderr)
    if p.returncode:raise RuntimeError(profile+' '+p.stdout+p.stderr)
    r=json.loads(next(s[7:] for s in p.stdout.splitlines() if s.startswith('RESULT ')))
    assert r['P_scratch_peak_bytes']<=16384 and r['U_cache_peak_bytes']+4096<=16384
    assert r['read_bus_bytes']>=r['logical_read_bytes'] and r['write_bus_bytes']>=r['logical_write_bytes']
    results.append(r)
assert results[1]['ticks']<results[0]['ticks'],'K32 failed to improve independent small matrix'
Path('generated/smoke.json').write_text(json.dumps(results,indent=2)+'\n')
print('SMOKE_PASS',len(results))
