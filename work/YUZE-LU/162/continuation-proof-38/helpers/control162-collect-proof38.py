"""Capture bounded snapshots, matched-grid comparison and original active searches."""
from pathlib import Path
import subprocess,shlex,json,base64,hashlib,shutil,sys

repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=repo.parent.parent;out=repo/'work/YUZE-LU/162/continuation-proof-38'
assert not out.exists()
q=r'''from pathlib import Path
import json,time,hashlib,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391';paths=set();active=set()
def add(p,live=False):
 if p.is_file():paths.add(p)
 if live:active.add(p)
for n in [172,180]:
 for name in ['source-manifest.json','freeze-import.json','project/experiments/control_v1/system_upper.py','project/experiments/control_v1/openroad_snapshot.py','project/experiments/control_v1/openroad_grid.py']:
  add(b/('source-'+str(n))/name)
for ledger in ['sready180-bounded-snapshot','sready186-duplicate1514-phase-refill']:
 for p in (b/'route-selection-102'/ledger).rglob('*.json'):add(p)
for name in ['sready178-cugr24um-phase-probe.json','sready181-full-cugr-inputs.json','sready181-full-cugr-snapshot.json','s-ready-fastroute24phase-source172.json','s-ready-cpp-localdensity-source172.json','s-ready-cugr24phase-source172.json','s-ready-cpp-shortwire-source172.json','s-ready-cpp-shortwire-source172-units-correction.json']:
 record=b/'route-selection-102'/name;add(record)
 if record.exists():
  for task in json.loads(record.read_text()).get('tasks',[]):
   f=Path(task['path']);assert hashlib.sha256(f.read_bytes()).hexdigest()==task['sha256'];add(f);queue=f.parent.parent
   for p in [queue/'commands'/f.name,queue/'results'/f.name,queue/(f.stem+'.log')]:add(p,True)
for folder in ['router-bounded-snapshot-preflight-180','router-full-cugr-snapshot-181','router-cugr24phase-preflight-178']:
 for p in (b/folder).rglob('*'):
  if p.is_file():add(p,not(p.parent/'receipt.json').exists())
for node,names in [(2,['00-i-sready180-bounded-snapshot-preflight','00-i-sready181-full-cugr-snapshot']),(4,['00-j-sready178-cugr24um-phase-probe','00-k-sready177fast-route-1770'])]:
 queue=b/('dynamic-05/node'+str(node))
 for name in names:
  for p in [queue/'pending'/(name+'.json'),queue/'commands'/(name+'.json'),queue/'results'/(name+'.json'),queue/(name+'.log')]:add(p,True)
for seed in [1513,1514,1515,1590,1591,1630,1631,1690,1691,1770,1840,1850,1851]:
 folder=c/'upper-candidates'/str(seed)
 for p in folder.rglob('*'):
  if p.is_file()and p.suffix in ['.json','.log','.rpt']:add(p,True)
for fam,node in [(5,2),(2,3),(5,4),(3,5),(2,6),(2,7),(4,25),(2,26)]:add(b/('dynamic-%02d'%fam)/('node'+str(node))/'queue-state.json',True)
rows=[]
for p in sorted(paths):
 raw=p.read_bytes();row=dict(path=str(p),relative=str(p.relative_to(b)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),capture_time=time.time(),active_prefix_snapshot=p in active)
 if len(raw)<=524288 and p.suffix not in ['.odb']:row['base64']=base64.b64encode(raw).decode()
 rows.append(row)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False,scope='Actual source180 bounded replay fixture/full-scene diagnostic, exact duplicate-child retirement ledger and source172 same24um-phase CUGR comparison queue. Full original search/qualification chains retained. No joint physical qualification inferred.')))
'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir();copied=0
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 raw=base64.b64decode(encoded);assert hashlib.sha256(raw).hexdigest()==row['sha256']and len(raw)==row['bytes']
 p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);copied+=1
helpers=[]
names=['control162-cugr-phase-probe178.py','control162-pin-cut-diagnostic179.py','control162-pin-cut179.json','control162-snapshot-preflight180.py','control162-snapshot-negative180.py','control162-full-snapshot181.py','control162-summarize-snapshot182.py','control162-cugr24-full184.py','control162-cpp-local-full185.py','control162-extend-collectors185.py','control162-collector185-source-proof.json','control162-extend-collectors177.py','control162-collector177-source-proof.json','control162-system-ready140.py','control162-final-receipts-retry140.py','control162-next-gate143.py','control162-collect-proof38.py']
for optional in ['control162-short-diagnostic182.json','control162-short-diagnostic183.json','control162-snapshot-coverage183.py','control162-phase-refill186.py','control162-extend-collectors184.py','control162-collector184-source-proof.json','control162-cpp-shortwire-full187.py','control162-shortwire-units187.py','control162-extend-collectors187.py','control162-collector187-source-proof.json']:
 if(home/optional).is_file():names.append(optional)
for name in names:
 p=out/'helpers'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(home/name,p);helpers.append(dict(relative=str(p.relative_to(out)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
r=json.loads(subprocess.check_output([sys.executable,str(home/'control162-snapshot-negative180.py')],encoding='utf-8'));assert r['passed']
p=out/'helpers/actual-snapshot-binding-negative-controls.json';p.write_text(json.dumps(r,indent=2)+'\n');helpers.append(dict(relative=str(p.relative_to(out)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
d['helpers']=helpers;d['copied_count']=copied;(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
with(repo/'.gitattributes').open('a',encoding='utf-8')as f:f.write('\nwork/YUZE-LU/162/continuation-proof-38/** -text\n')
print(json.dumps(dict(indexed=len(d['rows']),copied=copied,helpers=len(helpers),captured_at=d['captured_at'],whole_system_qualified=False)))
