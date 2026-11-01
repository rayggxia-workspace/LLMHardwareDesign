"""Independent bandwidth/latency grid, same immutable numeric fixtures and binaries."""
from pathlib import Path
import json,subprocess,concurrent.futures,hashlib
B=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture');O=Path.cwd()/'results';O.mkdir(exist_ok=False)
manifest=json.loads((B/'attempt003/results/corpus/MANIFEST.json').read_text())['cases']
cases=[c for c in manifest if c['path']in ['W0-m0-n2048-t16.bin','W1-m0-l24-t16.bin','W2-m0-n8192-t1.bin','W3-t16.bin']]
configs=[(40,b)for b in [1,4,16,64]]+[(l,16)for l in [0,100]]
archs=[(0,2048),(1,256),(1,512),(1,1024),(1,2048),(2,0),(3,0)]
binaries={a:B/('attempt038'if a[0]==3 else'attempt022')/'results'/('a%d_%d'%a)/'obj/Vresearch_top'for a in archs}
(O/'BINARY_VERSIONS.json').write_text(json.dumps([dict(architecture=a[0],capacity=a[1],path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())for a,p in binaries.items()],indent=2)+'\n')
tasks=[(a,c,l,b,p)for a in archs for c in cases for l,b in configs for p in ['cache','cache_shared']]
def run(t):
 a,c,l,b,p=t;src=B/'attempt003/results/corpus'/c['path'];assert hashlib.sha256(src.read_bytes()).hexdigest()==c['sha256']
 dst=O/('a%d_%d_'%a+src.stem+'_'+str(l)+'_'+str(b)+'_'+p+'.json')
 with dst.with_suffix('.log').open('w')as f:r=subprocess.run([str(binaries[a]),str(src),str(dst),str(l),str(b),p],stdout=f,stderr=subprocess.STDOUT)
 row=dict(architecture=a[0],capacity=a[1],workload=c['path'],input_sha256=c['sha256'],policy=p,exit=r.returncode)
 if dst.exists():row.update(json.loads(dst.read_text()))
 return row
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=96)as pool:
 pending=[pool.submit(run,t)for t in tasks]
 for job in concurrent.futures.as_completed(pending):rows.append(job.result());(O/'RESULTS.json').write_text(json.dumps(rows,indent=2)+'\n')
assert len(rows)==336 and all(r['exit']==0 for r in rows)
