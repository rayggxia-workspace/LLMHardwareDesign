"""Capture measured budgets, exact replays, new queues and local-congestion source."""
from pathlib import Path
import subprocess,shlex,json,base64,hashlib,shutil
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=repo.parent.parent;out=repo/'work/YUZE-LU/162/continuation-proof-36';assert not out.exists()
q=r'''from pathlib import Path
import json,time,hashlib,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391';paths=set();active=set();summaries=[]
def one(p):
 if p.is_file():paths.add(p)
for n in [160,161,165]:
 for name in ['source-manifest.json','freeze-import.json','project/experiments/control_v1/electrical_floorplan.cpp','project/experiments/control_v1/electrical_floorplan.py','project/experiments/control_v1/linked_floorplan.py','project/experiments/control_v1/placement_residual_budget.py','project/experiments/control_v1/system_upper.py']:one(b/('source-'+str(n))/name)
for name in ['sready160-measured-budget-placement','sready160-refill-slot1493-retired','sready165-local-density-placement']:
 for p in (b/'route-selection-102'/name).rglob('*.json'):one(p)
names=['sready160-measured-placement-refill1610-1611.json','s-ready-measured-placement-bounds160.json','sready160-measured-placement-native-cap-config.json','sready161-clear-trial-placements1620-1622.json','s-ready-clear-placement-bounds161.json','sready161-clear-placement-native-cap-config.json','sready161-replay-verification.json','s-ready-clear-placement-openroad-source157.json','s-ready-local-density-bounds165.json','sready165-local-density-native-cap-config.json']
for name in names:
 p=b/'route-selection-102'/name;one(p)
 if not p.exists():continue
 for row in json.loads(p.read_text()).get('tasks',[]):
  f=Path(row.get('path',row.get('spec')));one(f);queue=f.parent.parent
  for t in [queue/'commands'/f.name,queue/'results'/f.name,queue/(f.stem+'.log')]:one(t);active.add(t)
for p in (b/'route-selection-102/sready160-measured-budget-placement/tasks.json',b/'route-selection-102/sready165-local-density-placement/tasks.json'):
 for row in json.loads(p.read_text())['tasks']:
  f=Path(row['path']);one(f);queue=f.parent.parent
  for t in [queue/'commands'/f.name,queue/'results'/f.name,queue/(f.stem+'.log')]:one(t);active.add(t)
for seed in [1600,1601,1602,1603,1604,1610,1611,1620,1621,1622,1700,1701,1702,1703,1704]:
 for p in (c/'cap-capacity-candidates'/str(seed)).glob('*'):
  if p.suffix in ['.json','.log','.txt']:one(p)
for folder in ['measured-placement-native-residual-160','measured-placement-native-pin-load-160','clear-placement-native-residual-161','clear-placement-native-pin-load-161','local-density-native-residual-165','local-density-native-pin-load-165']:
 for p in (c/folder).rglob('*'):
  if p.is_file()and p.suffix in ['.json','.log','.tsv','.tcl']:one(p)
 f=c/folder/('native-pin-load.json'if'pin-load'in folder else'native-cap-residual.json')
 if f.exists():
  d=json.loads(f.read_text());rows=[]
  for r in d['placements']:
   key='optimistic_total_with_minimum_pin_ff'if'pin-load'in folder else'optimistic_total_ff';worst=max(r['rows'],key=lambda x:x[key]['high']/x['max_capacitance_ff']);rows.append(dict(placement=r['placement'],violations=r['violations'],worst_high_ratio=worst[key]['high']/worst['max_capacitance_ff'],worst=worst))
  summaries.append(dict(source=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),placements=rows))
for seed in [1630,1631]:
 one(b/'route-selection-102'/('sready163clear-acceptance-'+str(seed)+'.json'))
 for p in (c/'upper-candidates'/str(seed)).rglob('*'):
  if p.is_file()and p.suffix in ['.json','.log','.tcl','.rpt']:one(p);active.add(p)
for fam,node in [(5,2),(2,3),(5,4),(3,5),(2,6),(2,7),(4,25),(2,26)]:one(b/('dynamic-%02d'%fam)/('node'+str(node))/'queue-state.json')
rows=[]
for p in sorted(paths):
 data=p.read_bytes();row=dict(path=str(p),relative=str(p.relative_to(b)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),capture_time=time.time(),active_prefix_snapshot=p in active)
 if len(data)<=524288:row['base64']=base64.b64encode(data).decode()
 rows.append(row)
print(json.dumps(dict(captured_at=time.time(),rows=rows,derived_actual_report_summaries=summaries,scope='Measured native/pin placement budgets, exact64 trial-byte replays and default placement identity, clear1620/21/22 necessary bounds, actual1630/31 full physical queues, actual local-congestion165 source and diagnostic queues. Not joint qualification.')))
'''
compile(q,'collect_source_bound_proof36','exec')
data=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir();copied=0
for row in data['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 blob=base64.b64decode(encoded);assert hashlib.sha256(blob).hexdigest()==row['sha256']and len(blob)==row['bytes'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob);copied+=1
helpers=[]
for name in ['control162-residual-budget-test160.py','control162-measured-placement-launch160.py','control162-measured-placement-refill160.py','control162-measured-refill-slot160.py','control162-measured-placement-bounds160.py','control162-clear-trial-placement-launch161.py','control162-clear-placement-bounds161.py','control162-placement-replay-verify161.py','control162-clear-placement-routes163.py','control162-clear-route-status163.py','control162-local-density-diagnostic164.py','control162-local-density164.json','control162-local-density-launch165.py','control162-local-density-status165.py','control162-local-density-bounds165.py','control162-extend-collectors163.py','control162-system-ready140.py','control162-final-receipts-retry140.py','control162-next-gate143.py','control162-git-data-publish-161/receipt.json','control162-collect-proof36.py']:
 p=out/'helpers'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(home/name,p);helpers.append(dict(relative=str(p.relative_to(out)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
data['helpers']=helpers;data['copied_count']=copied;(out/'index.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
with(repo/'.gitattributes').open('a',encoding='utf-8')as f:f.write('\nwork/YUZE-LU/162/continuation-proof-36/** -text\n')
print(json.dumps(dict(indexed=len(data['rows']),copied=copied,helpers=len(helpers),captured_at=data['captured_at'],whole_system_qualified=False)))
