from pathlib import Path
import subprocess,shlex,json,hashlib,base64
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');h=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-58';d=json.loads((out/'index.json').read_text(encoding='utf-8'));assert'bidirectional_S_supplement'not in d
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');paths={}
def add(p,live=False):
 if p.is_file():paths[p]=live
for prefix in ['sready564','sready566']:
 for folder in(b/'route-selection-102').glob(prefix+'*'):
  for p in folder.glob('*'):add(p)
for seed in [4850,5010,5640]:
 p=b/'r256-composition-453/upper-candidates'/str(seed)/'route'
 for name in ['receipt.json','router-input.txt','router-distance-oracle.json','trial-index.json']:add(p/name,True)
 for f in p.glob('trial-*/router.log'):add(f,True)
for seed in [3750,3751]:add(b/'r256-composition-359/upper-candidates'/str(seed)/'route/openroad-search/case-0/openroad.log',seed==3751)
q=b/'dynamic-07/node7';add(q/'queue-state.json',True)
for sub in ['pending','commands','results']:
 for p in(q/sub).glob('*'):
  if'sready564'in p.name:add(p,True)
rows=[]
for p,live in sorted(paths.items()):
 if p.suffix not in ['.json','.log','.txt']:continue
 raw=p.read_bytes();row=dict(relative='bidirectional-S-supplement/'+str(p.relative_to(b)),path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(raw)<=524288:row['base64']=base64.b64encode(raw).decode()
 rows.append(row)
print(json.dumps(dict(time=time.time(),rows=rows,whole_system_qualified=False)))
'''
s=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55))
for row in s['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is not None:
  raw=base64.b64decode(encoded);assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
d['rows']+=s['rows'];d['bidirectional_S_supplement']={k:v for k,v in s.items()if k!='rows'}
for n in ['node563','queue564','queue564-remote','cohort565','prepare566','refill566-remote','supplement567']:
 p=h/('control162-'+n+'.py');raw=p.read_bytes();rel='helpers/'+p.name;assert not(out/rel).exists();(out/rel).write_bytes(raw);d['helpers'].append(dict(relative=rel,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
