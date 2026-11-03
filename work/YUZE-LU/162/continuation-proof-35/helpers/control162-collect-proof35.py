"""Capture actual internal-channel diagnostics and fourteen full downstream specs."""
from pathlib import Path
import subprocess,shlex,json,base64,hashlib,shutil
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=repo.parent.parent;out=repo/'work/YUZE-LU/162/continuation-proof-35';assert not out.exists()
q=r'''from pathlib import Path
import json,time,hashlib,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391';paths=set();active=set();summaries=[]
def one(p):
 if p.is_file():paths.add(p)
for p in (b/'route-selection-102/sready158-internal-channel-preflight').rglob('*.json'):one(p)
for name in ['s-ready-internal-channel-bounds158.json','sready158-internal-channel-native-cap-config.json','s-ready-internal-channel-openroad-source157.json']:
 p=b/'route-selection-102'/name;one(p)
 if 'tasks'in json.loads(p.read_text()):
  for row in json.loads(p.read_text())['tasks']:
   f=Path(row['path']);one(f);queue=f.parent.parent
   for t in [queue/'commands'/f.name,queue/'results'/f.name,queue/(f.stem+'.log')]:one(t);active.add(t)
for seed in range(1580,1584):
 folder=c/'cap-capacity-candidates'/str(seed)
 for p in folder.glob('*'):
  if p.suffix in ['.json','.log','.txt']:one(p)
for folder in ['internal-channel-native-residual-158','internal-channel-native-pin-load-158']:
 for p in (c/folder).glob('*.json'):one(p)
 f=c/folder/('native-pin-load.json'if'pin-load'in folder else'native-cap-residual.json')
 if f.exists():
  d=json.loads(f.read_text());rows=[]
  for r in d['placements']:
   key='optimistic_total_with_minimum_pin_ff'if'pin-load'in folder else'optimistic_total_ff'
   worst=max(r['rows'],key=lambda x:x[key]['high']/x['max_capacitance_ff']);rows.append(dict(placement=r['placement'],violations=r['violations'],worst_high_ratio=worst[key]['high']/worst['max_capacitance_ff'],worst=worst))
  summaries.append(dict(source=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),placements=rows))
for seed in [1590,1591]:
 one(b/'route-selection-102'/('sready159internal-acceptance-'+str(seed)+'.json'))
 for p in (c/'upper-candidates'/str(seed)).rglob('*'):
  if p.is_file()and p.suffix in ['.json','.log','.tcl','.rpt']:one(p);active.add(p)
for fam,node in [(5,2),(2,3),(5,4),(3,5),(2,6),(2,7),(4,25),(2,26)]:one(b/('dynamic-%02d'%fam)/('node'+str(node))/'queue-state.json')
rows=[]
for p in sorted(paths):
 data=p.read_bytes();row=dict(path=str(p),relative=str(p.relative_to(b)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),capture_time=time.time(),active_prefix_snapshot=p in active)
 if len(data)<=524288:row['base64']=base64.b64encode(data).decode()
 rows.append(row)
print(json.dumps(dict(captured_at=time.time(),rows=rows,derived_actual_report_summaries=summaries,scope='Actual four internal-channel placements and native-ground/input-pin lower-bound results; three failed high RC. Two actual full-scene mature routes on1580 plus fourteen unchanged full physical gates. Search and necessary-condition evidence, never joint qualification.')))
'''
data=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir();copied=0
for row in data['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 blob=base64.b64decode(encoded);assert hashlib.sha256(blob).hexdigest()==row['sha256']and len(blob)==row['bytes'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob);copied+=1
helpers=[]
for name in ['control162-internal-channel-preflight158.py','control162-internal-channel-status158.py','control162-internal-channel-bounds158.py','control162-internal-channel-native-status158.py','control162-internal-channel-routes159.py','control162-internal-channel-route-status159.py','control162-extend-collectors159.py','control162-system-ready140.py','control162-final-receipts-retry140.py','control162-next-gate143.py','control162-collect-proof35.py']:
 p=out/'helpers'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(home/name,p);helpers.append(dict(relative=str(p.relative_to(out)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
data['helpers']=helpers;data['copied_count']=copied;(out/'index.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
with(repo/'.gitattributes').open('a',encoding='utf-8')as f:f.write('\nwork/YUZE-LU/162/continuation-proof-35/** -text\n')
print(json.dumps(dict(indexed=len(data['rows']),copied=copied,helpers=len(helpers),captured_at=data['captured_at'],whole_system_qualified=False)))
