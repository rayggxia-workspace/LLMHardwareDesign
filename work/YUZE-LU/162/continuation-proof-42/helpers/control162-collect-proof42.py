"""Capture actual R256 native/PG work, recovery and routing evidence."""
from pathlib import Path
import subprocess,shlex,json,hashlib,base64,shutil
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=repo.parent.parent;out=repo/'work/YUZE-LU/162/continuation-proof-42';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,time,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');paths={}
def add(p,live=False):
 if p.is_file():paths[p]=paths.get(p,False)or live
for n in [217,220,226,228,232,236,239]:
 for name in ['source-manifest.json','freeze-import.json']:add(b/('source-'+str(n))/name)
for name in ['router-bidirectional-regression-218','router-bidirectional-regression-221','r256-scene-regression-240']:
 for p in(b/name).glob('*'):
  if p.suffix in ['.json','.log','.ys','.sv']:add(p)
for p in(b/'route-selection-102').glob('*'):
 if p.name.startswith(('sready218','sready221','sready223','sready225','sready229','sready230','sready233','sready235','sready237','sready238','s-ready-bidirectional-source220')):
  if p.is_file():add(p)
  else:
   for f in p.rglob('*'):
    if f.suffix in ['.json','.txt']:add(f)
for family,numbers in [('229',range(2290,2296)),('233',[2330,2333]),('237',[2371])]:
 for n in numbers:
  root=b/('r256-native-'+family)/str(n);add(root/'native/receipt.json',True)
  for p in(root/'native').glob('*.json'):add(p,True)
  for name in ['native-flow.json','03-do-cts.log','04-do-route.log','05-do-finish.log']:add(root/'native/pnr'/name,True)
  for gate in ['sealed','physical','drc','function','formal','deliver']:
   for p in(root/'gates'/gate).glob('*'):
    if p.suffix in ['.json','.log','.rpt']:add(p,True)
for n in [2292,2294,2295]:
 root=b/'r256-fixed-pg-235'/str(n)
 for folder in ['wrapper','checks/physical','checks/timing','delivery']:
  for p in(root/folder).glob('*'):
   if p.suffix in ['.json','.log','.rpt','.tsv']:add(p,True)
for n in [1980,2091,2230,2231,2232]:
 root=b/'s-ready-composition-01/1391/upper-candidates'/str(n)/'route'
 add(root/'receipt.json',True);add(root/'openroad-search/case-0/openroad.log',True)
 for p in root.glob('trial-*/router.log'):add(p,True)
for fam,node in [(5,2),(2,3),(5,4),(3,5),(2,6),(2,7),(4,25),(2,26),(6,7),(6,26)]:
 folder=b/('dynamic-%02d'%fam)/('node'+str(node));add(folder/'queue-state.json',True);add(folder/'submission.json');add(folder/'slurm.log',True)
 if fam==6:
  for sub in ['pending','commands','results','previous-controller-failure']:
   for p in(folder/sub).glob('*'):
    if p.suffix in ['.json','.log','.txt']:add(p,True)
rows=[]
for p,live in sorted(paths.items()):
 raw=p.read_bytes();r=dict(path=str(p),relative=str(p.relative_to(b)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(raw)<=524288:r['base64']=base64.b64encode(raw).decode()
 rows.append(r)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False,scope='Actual source-bound R256 reuse/new physical/PG results, retained CTS and controller failures/recovery, actual routing regressions/full searches. Snapshots are not eventual results or qualification.')))
'''
compile(q,'proof42','exec')
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir();copied=0
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 raw=base64.b64decode(encoded);assert len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);copied+=1
helpers=[]
names=['control162-bidirectional-regression218.py','control162-bidirectional-tie-regression221.py','control162-bidirectional-tie-full223.py','control162-bidirectional-refill225.py','control162-reuse-r256227.py','control162-r256-backend228.py','control162-r256-native-queue229.py','control162-r256-native-refill230.py','control162-r256-retry233.py','control162-r256-pg235.py','control162-recover-queues237.py','control162-refill238.py','control162-contract-queue240.py','control162-collect-proof42.py']
for name in names:
 p=home/name;assert p.is_file(),name;target=out/'helpers'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(p,target);helpers.append(dict(relative=str(target.relative_to(out)),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size))
d.update(helpers=helpers,copied_count=copied);(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
with(repo/'.gitattributes').open('a',encoding='utf-8')as f:f.write('\nwork/YUZE-LU/162/continuation-proof-42/** -text\n')
print(json.dumps(dict(indexed=len(d['rows']),copied=copied,helpers=len(helpers),captured_at=d['captured_at'],whole_system_qualified=False)))
