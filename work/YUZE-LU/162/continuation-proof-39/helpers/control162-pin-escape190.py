"""Read actual immutable scene terminals and apply a conservative escape bound."""
from pathlib import Path
import subprocess,shlex,json

q=r'''from pathlib import Path
import sys,json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-190';sys.path.insert(0,str(source/'project/experiments/control_v1'))
from pin_escape_bound import inspect
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();m=json.loads((source/'source-manifest.json').read_text());assert m['commit']=='34a4369fd6141676a84a4b2fe32639867eb2591a'
module=source/'project/experiments/control_v1/pin_escape_bound.py';assert m['files']['project/experiments/control_v1/pin_escape_bound.py']==sha(module)
rows=[]
for seed in [1513,1770,1840,1850,1851]:
 path=b/'s-ready-composition-01/1391/upper-candidates'/str(seed)/'route/placement.json';p=json.loads(path.read_text());assert len(p['terminals'])==8990
 nx,ny=round(p['width_um']/4),round(p['height_um']/4);assert nx*4==p['width_um']and ny*4==p['height_um']
 r=inspect(p['terminals'],nx,ny);r.update(seed=seed,source=str(path),sha256=sha(path),terminals_sha256=hashlib.sha256(json.dumps(p['terminals'],sort_keys=True,separators=(',',':')).encode()).hexdigest());rows.append(r)
print(json.dumps(dict(captured_at=time.time(),source_commit=m['commit'],module_sha256=sha(module),source_manifest_sha256=sha(source/'source-manifest.json'),reports=rows,whole_system_qualified=False,scope='Read-only necessary first-step pin escape matching on actual8990-net placement terminal sets. No route/placement/task/acceptance mutation, no EDA execution. A Hall witness proves local impossibility under unchanged grid/via rules; a full matching cannot prove global routing or physical qualification.')))
'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45))
out=Path(r'D:\Data\电路实验\control162-pin-escape-bound190.json');assert not out.exists();out.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
for r in d['reports']:
    print(json.dumps({k:v for k,v in r.items()if k not in ['hall_witness','scope']}))
    if r['hall_witness']:print('HALL_WITNESS',json.dumps(r['hall_witness'])[:8000])
