"""Capture actual pin-load exclusion, immutable searches and exact refills."""
from pathlib import Path
import subprocess,shlex,json,hashlib,base64,shutil
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');paths=set();active_logs=set()
def add(p):
 if p.is_file():paths.add(p)
for name in ['source-manifest.json','freeze-import.json']:add(b/'source-141'/name)
root=b/'s-ready-composition-01/1391/native-pin-load-01'
for p in root.rglob('*'):
 if p.is_file():add(p)
for p in (b/'route-selection-102').glob('*capacity*source140.json'):add(p)
for pattern in ['*capacity-placements1420-1425.json','*capacity-residual*.json','*native-pin-load.json','s-ready-cap-proof141-refill-source140.json']:
 for p in (b/'route-selection-102').glob(pattern):add(p)
for p in (b/'route-selection-102/sready141-proven-cap1421-retired').glob('*.json'):add(p)
base=b/'s-ready-composition-01/1391'
for p in (base/'cap-capacity-candidates').glob('*/*'):
 if p.name in ['receipt.json','wire-cap-lower-bound.json','placement.json','placement-search.json']:add(p)
for p in (base/'capacity-native-residual-01').glob('*.json'):add(p)
for seed in list(range(1410,1414))+list(range(1430,1434))+list(range(1440,1455)):
 p=base/'upper-candidates'/str(seed)/'route'
 for f in [p/'trial-0/router.log',p/'trial-0/input.txt',p/'router-distance-oracle.json',p/'receipt.json',p/'trial-index.json']:
  add(f)
  if f.name=='router.log'and not(p/'receipt.json').exists():active_logs.add(f)
for family,candidate in [('s-escape-composition-03',1350),('s-ready-composition-01',1390),('s-ready-composition-01',1391)]:
 p=b/family/str(candidate)/'final-composition';add(p/'receipt.json')
 for f in p.glob('initial-*.json'):
  if f.stat().st_size:add(f)
for node in [2,3,4,5,6,7,25,26]:
 family=5 if node in (2,4)else 3 if node==5 else 4 if node==25 else 2
 p=b/('dynamic-%02d'%family)/('node'+str(node));add(p/'queue-state.json')
 for sub in ['pending','commands','results']:
  for f in (p/sub).glob('*sready14*.json'):add(f)
rows=[]
for p in sorted(paths):
 size=p.stat().st_size;copy=size<=512000;remaining=size;h=hashlib.sha256();parts=[]
 with p.open('rb')as stream:
  while remaining:
   data=stream.read(min(remaining,16*1024*1024));assert data;remaining-=len(data);h.update(data)
   if copy:parts.append(data)
 rows.append(dict(remote=str(p),relative=str(p.relative_to(b)),bytes=size,sha256=h.hexdigest(),copied=copy,active_log_prefix_snapshot=p in active_logs,data=base64.b64encode(b''.join(parts)).decode()if copy else None))
print(json.dumps(dict(time=time.time(),files=rows,scope='Actual source141 final-ODB minimum pin capacitance exclusion and exact own four-step retirement/refill. Same physical blocks. Active router logs are captured prefixes at the recorded byte length, never final-file hashes or route/physical qualifications. Missing receipts are pending, not passed.')))
'''
d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]));home=Path(r'D:\Data\电路实验');repo=home/'LLMHardwareDesign-worktrees/issue-162-control';out=repo/'work/YUZE-LU/162/continuation-proof-28';assert not out.exists();out.mkdir()
for row in d['files']:
 encoded=row.pop('data')
 if row['copied']:
  data=base64.b64decode(encoded);assert len(data)==row['bytes']and hashlib.sha256(data).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
helpers=[]
for name in ['control162-capacity-launch140.py','control162-capacity-residual140.py','control162-capacity-upper140.py','control162-capacity-refill140.py','control162-pin-load-launch141.py','control162-retire-cap1421-proof141.py','control162-cap-proof-refill141.py','control162-final-receipts-retry140.py','control162-system-ready140.py','control162-github-checkpoint27-readback.json','control162-proof28.py']:
 data=(home/name).read_bytes();(out/name).write_bytes(data);helpers.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
p=home/'control162-git-data-publish-14027/receipt.json';data=p.read_bytes();r=json.loads(data);assert r['passed']and r['exact_local_commit_identity']and not r['force'];(out/'exact-git-checkpoint27.json').write_bytes(data);helpers.append(dict(path='exact-git-checkpoint27.json',bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
d['helpers']=helpers;(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8',newline='\n')
p=repo/'.gitattributes';rule='work/YUZE-LU/162/continuation-proof-28/** -text'
if rule not in p.read_text(encoding='utf-8'):
 with p.open('a',encoding='utf-8')as f:f.write('\n'+rule+'\n')
print(json.dumps(dict(indexed=len(d['files']),copied=sum(r['copied']for r in d['files']),capture=d['time'])))
