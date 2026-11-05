"""Capture actual R256 native/PG work, recovery and routing evidence."""
from pathlib import Path
import subprocess,shlex,json,hashlib,base64,shutil
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=repo.parent.parent;out=repo/'work/YUZE-LU/162/continuation-proof-44';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,time,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');paths={}
def add(p,live=False):
 if p.is_file():paths[p]=paths.get(p,False)or live
for n in [282,286,290]:
 for name in ['source-manifest.json','freeze-import.json']:add(b/('source-'+str(n))/name)
for stem in ['r256-fixed-pg-271/2371','r256-fixed-pg-272','r256-fixed-pg-291','r256-composition-274','r256-early-native-283']:
 for p in(b/stem).rglob('*'):
  if p.suffix in ['.json','.log','.rpt','.tsv','.tcl','.lydrc','.ys']and not any(part in ['obj','obj_dir','hierarchical-obj','native-types','flow']for part in p.relative_to(b/stem).parts):add(p,True)
for p in(b/'r256-composition-273/function').glob('*'):
 if p.suffix=='.json'or p.name in ['build.log','cells.log']:add(p,True)
for p in(b/'router-adaptive-regression-287').glob('*'):
 if p.suffix in ['.json','.log']:add(p)
for p in(b/'route-selection-102').glob('*'):
 if p.name.startswith(tuple('sready'+str(n)for n in [283,287,291,267])):
  for f in p.rglob('*'):
   if f.suffix in ['.json','.txt']:add(f)
folder=b/'dynamic-07/node7'
for name in ['queue-state.json','submission.json','slurm.log']:add(folder/name,True)
for p in(folder/'pending').glob('*'):
 if any(token in p.name for token in ['283','287','291']):add(p)
for p in(folder/'commands').glob('*'):
 if any(token in p.name for token in ['283','291']):add(p)
for p in(folder/'results').glob('*'):
 if any(token in p.name for token in ['257','261','291']):add(p)
for p in folder.glob('*.log'):
 if any(token in p.name for token in ['257-timing','291','283']):add(p,True)
rows=[]
for p,live in sorted(paths.items()):
 raw=p.read_bytes();r=dict(path=str(p),relative=str(p.relative_to(b)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(raw)<=524288:r['base64']=base64.b64encode(raw).decode()
 rows.append(r)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False,scope='C8 and R256 final fixed-PG actual acceptances, retained zero-passive receiver assertion failure and strict retry, early350 unconstrained TOP outputs, actual final23-type selection and345-instance graph, ongoing full-native timing/function, verified adaptive search regression and pending unchanged whole-system gates. Live snapshots never imply eventual qualification.')))
'''
compile(q,'proof44','exec')
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir();copied=0
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 raw=base64.b64decode(encoded);assert len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);copied+=1
helpers=[]
names=['control162-early-audit288.py', 'control162-r-timing289.py', 'control162-r-timing-retry291.py', 'control162-progress293.py', 'control162-native-failure294.py', 'control162-r256-upper267.py', 'control162-r256-upper267-pre-adaptive295.py', 'control162-adaptive-regression287.py', 'control162-r256-c-index285.py', 'control162-receive-r256-c285.py', 'control162-r256-r-index296.py', 'control162-receive-r256-r296.py', 'control162-current-delivery298.py', 'control162-final-prereq299.py', 'control162-runtime300.py', 'control162-collect-proof44.py']
for name in names:
 p=home/name;assert p.is_file(),name;target=out/'helpers'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(p,target);helpers.append(dict(relative=str(target.relative_to(out)),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size))
d.update(helpers=helpers,copied_count=copied);(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
with(repo/'.gitattributes').open('a',encoding='utf-8')as f:f.write('\nwork/YUZE-LU/162/continuation-proof-44/** -text\n')
print(json.dumps(dict(indexed=len(d['rows']),copied=copied,helpers=len(helpers),captured_at=d['captured_at'],whole_system_qualified=False)))
