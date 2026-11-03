"""Append exact recent source, diagnostic, refill and active-route evidence."""
from pathlib import Path
import subprocess,shlex,json,hashlib,base64,shutil
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=repo.parent.parent;out=repo/'work/YUZE-LU/162/continuation-proof-39';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,time,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391';paths={}
def add(p,live=False):
 if p.is_file():paths[p]=paths.get(p,False)or live
for n in [190,196,197]:
 for name in ['source-manifest.json','freeze-import.json','project/experiments/control_v1/electrical_floorplan.cpp','project/experiments/control_v1/electrical_floorplan.py','project/experiments/control_v1/system_upper.py','project/experiments/control_v1/pin_escape_bound.py']:add(b/('source-'+str(n))/name)
records=['s-ready-cpp-weighted-local-source172.json','sready197-balanced-local-placement.json','s-ready-strong-local-bounds196.json','s-ready-strong-local-bounds197.json','sready196-default-replay-verification.json','sready197-default-replay-verification.json','s-ready-balanced-fast-source172.json','s-ready-balanced-cpp-source172.json']
for name in records:
 p=b/'route-selection-102'/name;add(p)
 if p.exists():
  for row in json.loads(p.read_text()).get('tasks',[]):
   f=Path(row['path']);assert hashlib.sha256(f.read_bytes()).hexdigest()==row['sha256'];add(f);queue=f.parent.parent
   for p in [queue/'commands'/f.name,queue/'results'/f.name,queue/(f.stem+'.log')]:add(p,True)
for name in ['sready193-weighted-local-refill','sready196-strong-local-placement']:
 for p in (b/'route-selection-102'/name).rglob('*.json'):add(p)
for seed in [1960,1961,1962,1970,1971,1972]:
 for p in (c/'cap-capacity-candidates'/str(seed)).rglob('*'):add(p,not(c/'cap-capacity-candidates'/str(seed)/'receipt.json').exists())
for folder in ['strong-local-native-residual-196','strong-local-native-pin-load-196','strong-local-native-residual-197','strong-local-native-pin-load-197']:
 for p in (c/folder).rglob('*'):add(p,not(c/folder/'receipt.json').exists())
for seed in [1770,1840,1850,1851,1852,1853,1980,1981]:
 for p in (c/'upper-candidates'/str(seed)).rglob('*'):
  if p.suffix in ['.json','.log','.rpt']:add(p,True)
for fam,node in [(5,2),(2,3),(5,4),(3,5),(2,6),(2,7),(4,25),(2,26)]:add(b/('dynamic-%02d'%fam)/('node'+str(node))/'queue-state.json',True)
rows=[]
for p,live in sorted(paths.items()):
 raw=p.read_bytes();r=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(raw)<=524288 and p.suffix not in ['.odb']:r['base64']=base64.b64encode(raw).decode()
 rows.append(r)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False,scope='Exact recent diagnostic/placement source bindings and active search snapshots. Necessary bounds/diagnostic execution do not qualify a whole physical system.')))
'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir();copied=0
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 raw=base64.b64decode(encoded);assert len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);copied+=1
names=['control162-pin-escape190.py','control162-pin-escape-bound190.json','control162-weighted-local192.py','control162-weighted-refill193.py','control162-extend-collectors194.py','control162-collector194-source-proof.json','control162-local-density-launch196.py','control162-local-density-bounds196.py','control162-local-density-status196.py','control162-default-replay-verify196.py','control162-local-density-compare196.py','control162-local-density196.json','control162-local-density-launch197.py','control162-local-density-bounds197.py','control162-default-replay-verify197.py','control162-local-density-compare197.py','control162-local-density197.json','control162-collect-proof39.py']
helpers=[]
names+=['control162-local-density-status197.py','control162-balanced-full198.py','control162-extend-collectors198.py','control162-collector198-source-proof.json','control162-system-ready140.py','control162-final-receipts-retry140.py','control162-next-gate143.py']
for name in names:
 src=home/name
 if not src.is_file():continue
 p=out/'helpers'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,p);helpers.append(dict(relative=str(p.relative_to(out)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
d.update(helpers=helpers,copied_count=copied);(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
with(repo/'.gitattributes').open('a',encoding='utf-8')as f:f.write('\nwork/YUZE-LU/162/continuation-proof-39/** -text\n')
print(json.dumps(dict(indexed=len(d['rows']),copied=copied,helpers=len(helpers),captured_at=d['captured_at'],whole_system_qualified=False)))
