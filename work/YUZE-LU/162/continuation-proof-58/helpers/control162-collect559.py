from pathlib import Path
import subprocess,shlex,json,hashlib,base64
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-58';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');paths={}
def add(p,live=False):
 if p.is_file():paths[p]=live
for folder in ['r256-s-local-active-pool-audit-553','r256-initial-order-window-diagnostic-558']:
 for p in(b/folder).glob('*'):add(p)
for prefix in ['sready545','sready546','sready549','sready555','sready556']:
 for folder in(b/'route-selection-102').glob(prefix+'*'):
  for p in folder.glob('*'):add(p)
for seed in [5400,5450,5451,5550,5551]:
 base=b/'r256-composition-453/upper-candidates'/str(seed);add(base/'receipt.json',True);add(base/'acceptance.json',True)
 route=base/'route'
 for name in ['router-distance-oracle.json','router-input.txt','trial-index.json','locked-original-output-search.json']:add(route/name,True)
 for p in route.glob('trial-*/router.log'):add(p,True)
for folder in ['dynamic-05/node2','dynamic-03/node5','dynamic-04/node25','dynamic-06/node26']:
 base=b/folder;add(base/'queue-state.json',True)
 for sub in ['pending','commands','results']:
  for p in(base/sub).glob('*'):
   if any(x in p.name for x in ['sready545','sready549','sready555']):add(p,True)
rows=[]
for p,live in sorted(paths.items()):
 if p.suffix not in ['.json','.cpp','.stdout','.log','.txt','.py']:continue
 data=p.read_bytes();row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(data)<=524288:row['base64']=base64.b64encode(data).decode()
 rows.append(row)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False)))
'''
d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir()
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is not None:
  data=base64.b64decode(encoded);assert len(data)==row['bytes']and hashlib.sha256(data).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
d['helpers']=[]
for n in ['queue545.py','queue545-remote.py','prepare546.py','refill546-remote.py','queue549.py','queue549-remote.py','queue555.py','queue555-remote.py','prepare556.py','refill556-remote.py','node548.py','audit553.py','order558.py','order558-remote.py','collect559.py','verify551.py','progress507.py','online550-issue-verified.json','online550-pr-request.json','online550-pr-verified.json']:
 p=home/('control162-'+n);data=p.read_bytes();rel='helpers/'+p.name;t=out/rel;t.parent.mkdir(exist_ok=True);t.write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
p=home/'control162-git-data-publish-544/receipt.json';data=p.read_bytes();rel='helpers/publication-544.json';(out/rel).write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
