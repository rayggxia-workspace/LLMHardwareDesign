"""Capture complete-path diagnostic lineage and exact-overlap experiment evidence."""
from pathlib import Path
import subprocess,shlex,json,hashlib,base64,shutil
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=repo.parent.parent;out=repo/'work/YUZE-LU/162/continuation-proof-40';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,time,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391';paths={}
def add(p,live=False):
 if p.is_file():paths[p]=paths.get(p,False)or live
for n in [199,202,204,207,211]:
 for name in ['source-manifest.json','freeze-import.json','project/experiments/control_v1/router_conflict_snapshot.py','project/experiments/control_v1/test_router_conflict_snapshot.py','project/experiments/control_v1/system_upper.py','project/experiments/control_v1/electrical_floorplan.cpp','project/experiments/control_v1/electrical_floorplan.py','project/experiments/control_v1/linked_floorplan.py']:add(b/('source-'+str(n))/name)
for ledger in ['sready200-complete-path-diagnostic','sready201-complete-path-refill','sready203-complete-path-supported','sready205-complete-path-with-PG','sready208-exact-overlap-placement','sready212-complete-interface-analysis']:
 for p in(b/'route-selection-102'/ledger).rglob('*'):add(p)
records=['s-ready-strong-local-bounds208.json','sready208-quantized-replay-verification.json','s-ready-exact-fast-source172.json','s-ready-exact-cpp-source172.json']
for name in records:add(b/'route-selection-102'/name)
task_records=[b/'route-selection-102'/name for name in records]+[b/'route-selection-102'/ledger/'tasks.json'for ledger in ['sready200-complete-path-diagnostic','sready203-complete-path-supported','sready205-complete-path-with-PG','sready212-complete-interface-analysis']]
for record in task_records:
 if not record.exists():continue
 for row in json.loads(record.read_text()).get('tasks',[]):
  p=Path(row['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'];add(p);queue=p.parent.parent
  for f in [queue/'commands'/p.name,queue/'results'/p.name,queue/(p.stem+'.log')]:add(f,True)
for name in ['00-k-sready140-route-1462','00-k-sready143cache-route-1492','00-k-sready143cache-route-1495']:
 node=25 if name.endswith('1462')else 3 if name.endswith('1492')else 6;queue=b/('dynamic-04'if node==25 else'dynamic-02')/('node'+str(node))
 for p in [queue/'pending'/(name+'.json'),queue/'commands'/(name+'.json'),queue/'results'/(name+'.json')]:add(p)
for folder in ['router-complete-path-preflight-203','router-complete-path-preflight-205']:
 for p in(b/folder).rglob('*'):add(p)
for folder in ['router-complete-path-full-203','router-complete-path-full-205','router-complete-interface-analysis-212']:
 for p in(b/folder).rglob('*'):
  if p.suffix in ['.json','.log','.cpp']:add(p,not(b/folder/'receipt.json').exists())
for seed in [2070,2071,2072]:
 for p in(c/'cap-capacity-candidates'/str(seed)).rglob('*'):
  if p.suffix in['.json','.txt','.log']:add(p)
for folder in ['strong-local-native-residual-208','strong-local-native-pin-load-208']:
 for p in(c/folder).rglob('*'):add(p)
for seed in [1980,1981,2090,2091]:
 for p in(c/'upper-candidates'/str(seed)).rglob('*'):
  if p.suffix in ['.json','.log','.rpt']:add(p,True)
for fam,node in [(5,2),(2,3),(5,4),(3,5),(2,6),(2,7),(4,25),(2,26)]:add(b/('dynamic-%02d'%fam)/('node'+str(node))/'queue-state.json',True)
rows=[]
for p,live in sorted(paths.items()):
 raw=p.read_bytes();r=dict(path=str(p),relative=str(p.relative_to(b)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(raw)<=524288:r['base64']=base64.b64encode(raw).decode()
 rows.append(r)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False,scope='Exact supported complete-path diagnostic lineage including real rejected/failed attempts, three-case actual preflight,16 full replays and exact-overlap search/source/bounds/replay/full-route admission. Diagnostic/necessary passes are not physical qualification. Large full path files remain source-bound in their computed diagnostic reports.')))
'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir();copied=0
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 raw=base64.b64decode(encoded);assert len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);copied+=1
helpers=[]
names=['control162-complete-path-queue200.py','control162-complete-path-refill201.py','control162-complete-path-retry203.py','control162-complete-path-pg-retry205.py','control162-cluster-demand206.py','control162-cluster-demand206.json','control162-exact-overlap-launch208.py','control162-exact-overlap-bounds208.py','control162-exact-overlap-status208.py','control162-quantized-replay208.py','control162-exact-overlap-compare208.py','control162-local-density208.json','control162-exact-overlap-full209.py','control162-extend-collectors209.py','control162-collector209-source-proof.json','control162-system-ready140.py','control162-final-receipts-retry140.py','control162-next-gate143.py','control162-collect-proof40.py']
names+=['control162-complete-path-status210.py','control162-complete-interface-analysis212.py']
for name in names:
 p=out/'helpers'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(home/name,p);helpers.append(dict(relative=str(p.relative_to(out)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
d.update(helpers=helpers,copied_count=copied);(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
with(repo/'.gitattributes').open('a',encoding='utf-8')as f:f.write('\nwork/YUZE-LU/162/continuation-proof-40/** -text\n')
print(json.dumps(dict(indexed=len(d['rows']),copied=copied,helpers=len(helpers),captured_at=d['captured_at'],whole_system_qualified=False)))
