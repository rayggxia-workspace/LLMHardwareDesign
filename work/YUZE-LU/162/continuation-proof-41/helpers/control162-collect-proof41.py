"""Capture actual source213 regressions, three full chains and exact refills."""
from pathlib import Path
import subprocess,shlex,json,hashlib,base64,shutil
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=repo.parent.parent;out=repo/'work/YUZE-LU/162/continuation-proof-41';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,time,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391';paths={}
def add(p,live=False):
 if p.is_file():paths[p]=paths.get(p,False)or live
for name in ['source-manifest.json','freeze-import.json','project/experiments/control_v1/tree_router.cpp','project/experiments/control_v1/tree_router_cpp.py','project/experiments/control_v1/router_regression.py','project/experiments/control_v1/system_upper.py']:add(b/'source-213'/name)
for folder in ['router-initial-order-regression-214','route-selection-102/sready214-initial-order-regression','route-selection-102/sready216-initial-order-refill-1499','route-selection-102/sready216-initial-order-refill-1500']:
 for p in(b/folder).rglob('*'):
  if p.suffix in['.json','.txt','.log']:add(p)
record=b/'route-selection-102/s-ready-initial-order-source213.json';add(record)
for row in json.loads(record.read_text())['tasks']:
 p=Path(row['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'];add(p)
 for f in [p.parent.parent/'commands'/p.name,p.parent.parent/'results'/p.name,p.parent.parent/(p.stem+'.log')]:add(f,True)
for p in(b/'route-selection-102').glob('sready215order-acceptance-*.json'):add(p)
for seed in [1980,1981,2090,2091,2150,2151,2152]:
 for p in(c/'upper-candidates'/str(seed)).rglob('*'):
  if p.suffix in['.json','.log','.rpt']:add(p,True)
for fam,node in [(5,2),(2,3),(5,4),(3,5),(2,6),(2,7),(4,25),(2,26)]:add(b/('dynamic-%02d'%fam)/('node'+str(node))/'queue-state.json',True)
rows=[]
for p,live in sorted(paths.items()):
 raw=p.read_bytes();r=dict(path=str(p),relative=str(p.relative_to(b)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(raw)<=524288:r['base64']=base64.b64encode(raw).decode()
 rows.append(r)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False,scope='Actual old-source byte replays, new ordered fixtures, source213 exact full graph tasks and original eight-acceptor SHA proof. Search gates only, no physical/system qualification.')))
'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir();copied=0
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 raw=base64.b64decode(encoded);assert len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);copied+=1
helpers=[]
for name in ['control162-order-regression214.py','control162-initial-order-full215.py','control162-extend-collectors215.py','control162-collector215-source-proof.json','control162-order-refill216.py','control162-system-ready140.py','control162-final-receipts-retry140.py','control162-next-gate143.py','control162-collect-proof41.py']:
 p=out/'helpers'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(home/name,p);helpers.append(dict(relative=str(p.relative_to(out)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
d.update(helpers=helpers,copied_count=copied);(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
with(repo/'.gitattributes').open('a',encoding='utf-8')as f:f.write('\nwork/YUZE-LU/162/continuation-proof-41/** -text\n')
print(json.dumps(dict(indexed=len(d['rows']),copied=copied,helpers=len(helpers),captured_at=d['captured_at'],whole_system_qualified=False)))
