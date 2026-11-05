"""Capture actual R256 native/PG work, recovery and routing evidence."""
from pathlib import Path
import subprocess,shlex,json,hashlib,base64,shutil
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=repo.parent.parent;out=repo/'work/YUZE-LU/162/continuation-proof-43';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,time,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');paths={}
def add(p,live=False):
 if p.is_file():paths[p]=paths.get(p,False)or live
for n in [242,244,248,250,252,256,258,269]:
 for name in ['source-manifest.json','freeze-import.json']:add(b/('source-'+str(n))/name)
for name in ['r256-scene-regression-253']:
 for p in(b/name).glob('*'):
  if p.suffix in ['.json','.log','.ys','.sv']:add(p)
for p in(b/'route-selection-102').glob('*'):
 if p.name.startswith(tuple('sready'+str(n)for n in [243,245,246,249,251,253,254,257,259,261,263,266,270])):
  if p.is_file():add(p)
  else:
   for f in p.rglob('*'):
    if f.suffix in ['.json','.txt']:add(f)
for family,numbers in [('233',[2330,2333]),('237',[2371]),('243',[2430])]:
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
for stem in ['r256-fixed-pg-246/2333','r256-fixed-pg-254/2430','r256-fixed-pg-257','r256-fixed-pg-261/2371','r256-native-reuse-245','r256-native-reuse-249','r256-native-reuse-251','r256-fixed-pg-251','r256-composition-259','r256-composition-263','r256-fixed-pg-271/2371','r256-fixed-pg-272','r256-composition-273','r256-composition-274','r256-early-electrical-266']:
 for p in(b/stem).rglob('*'):
  if p.suffix in ['.json','.log','.rpt','.tsv','.tcl','.lydrc','.ys']and not any(part in ['obj_dir','hierarchical-obj','native-types','flow']for part in p.relative_to(b/stem).parts):add(p,True)
for n in [1980,2091,2090,2150,2151,2152,2230,2231,2232]:
 root=b/'s-ready-composition-01/1391/upper-candidates'/str(n)/'route';add(root/'receipt.json',True);add(root/'openroad-search/case-0/openroad.log',True)
 for p in root.glob('trial-*/router.log'):add(p,True)
for fam,node in [(5,2),(2,3),(5,4),(3,5),(2,6),(2,7),(4,25),(2,26),(6,7),(6,26),(7,7)]:
 folder=b/('dynamic-%02d'%fam)/('node'+str(node));add(folder/'queue-state.json',True);add(folder/'submission.json');add(folder/'slurm.log',True)
 if fam in (6,7):
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
compile(q,'proof43','exec')
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir();copied=0
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 raw=base64.b64decode(encoded);assert len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);copied+=1
helpers=[]
names=['control162-r256-pg-queue257.py', 'control162-r256-function-queue259.py', 'control162-r256-leaf-index260.py', 'control162-receive-r256-five260.py', 'control162-r256-pg261.py', 'control162-latest262.py', 'control162-r256-final-scene263.py', 'control162-r256-resource264.py', 'control162-r256-graph265.py', 'control162-collect-proof43.py','control162-r256-early266.py','control162-r256-upper267.py','control162-controller268.py','control162-recover270.py']
for name in names:
 p=home/name;assert p.is_file(),name;target=out/'helpers'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(p,target);helpers.append(dict(relative=str(target.relative_to(out)),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size))
d.update(helpers=helpers,copied_count=copied);(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
with(repo/'.gitattributes').open('a',encoding='utf-8')as f:f.write('\nwork/YUZE-LU/162/continuation-proof-43/** -text\n')
print(json.dumps(dict(indexed=len(d['rows']),copied=copied,helpers=len(helpers),captured_at=d['captured_at'],whole_system_qualified=False)))
