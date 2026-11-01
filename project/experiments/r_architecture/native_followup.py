"""Reuse the immutable E co-simulation executable for sensitivity and real strips."""
from pathlib import Path
import json,hashlib,subprocess,concurrent.futures
B=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
O=Path.cwd()/'results';O.mkdir(exist_ok=False)
exe=B/'attempt055/results/a4_0/obj/Vresearch_top'
cases=json.loads((B/'attempt003/results/corpus/MANIFEST.json').read_text())['cases']
tasks=[(B/'attempt003/results/corpus',c,l,b,p)for c in cases if c['path']in ['W0-m0-n256-t1.bin','W0-m0-n2048-t16.bin','W1-m1-l8-t1.bin','W2-m0-n8192-t1.bin','W3-t16.bin']or'edge'in c['path']for l,b in [(20,4),(100,8)]for p in ['cache','cache_shared']]
real=B/'attempt027/results/corpus'
tasks += [(real,c,40,16,'cache')for c in json.loads((real/'MANIFEST.json').read_text())['cases']]
def run(t):
 root,c,l,b,p=t;src=root/c['path'];assert hashlib.sha256(src.read_bytes()).hexdigest()==c['sha256']
 dest=O/(src.stem+'_'+str(l)+'_'+str(b)+'_'+p+'.json')
 with dest.with_suffix('.log').open('w')as f:r=subprocess.run([str(exe),str(src),str(dest),str(l),str(b),p],stdout=f,stderr=subprocess.STDOUT)
 row=dict(architecture=4,capacity=0,workload=c['path'],input_sha256=c['sha256'],policy=p,exit=r.returncode);row.update(json.loads(dest.read_text())if dest.exists()else{});return row
with concurrent.futures.ThreadPoolExecutor(max_workers=16)as pool:rows=list(pool.map(run,tasks))
(O/'RESULTS.json').write_text(json.dumps(rows,indent=2)+'\n')
(O/'BINARY.json').write_text(json.dumps(dict(path=str(exe),sha256=hashlib.sha256(exe.read_bytes()).hexdigest()),indent=2)+'\n')
assert all(r['exit']==0 for r in rows)
