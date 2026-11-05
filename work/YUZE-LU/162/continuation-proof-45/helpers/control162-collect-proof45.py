"""Capture actual R256 native/PG work, recovery and routing evidence."""
from pathlib import Path
import subprocess,shlex,json,hashlib,base64,shutil
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=repo.parent.parent;out=repo/'work/YUZE-LU/162/continuation-proof-45';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,time,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');paths={}
def add(p,live=False):
 if p.is_file():paths[p]=paths.get(p,False)or live
for n in [305,313]:
 for name in ['source-manifest.json','freeze-import.json']:add(b/('source-'+str(n))/name)
for stem in ['r256-composition-274/native-sta','r256-composition-274/native-residual','r256-composition-274/native-residual302','r256-composition-274/native-pin-load302','r256-composition-274/native-residual307','r256-composition-274/native-pin-load307','r256-priority-regression-314']:
 for p in(b/stem).glob('*'):
  if p.suffix in ['.json','.log','.rpt','.tsv','.tcl']:add(p,True)
for n in [3070,3071,3072,3073]:
 for p in(b/('r256-composition-274/cap-candidates/'+str(n))).glob('*'):
  if p.suffix in ['.json','.log','.txt']:add(p,True)
for p in(b/'r256-composition-273/function').glob('*'):
 if p.suffix=='.json'or p.name in ['build.log','cells.log']:add(p)
for p in(b/'route-selection-102').glob('*'):
 if p.name.startswith(tuple('sready'+str(n)for n in [267,302,307,311,314])):
  for f in p.rglob('*'):
   if f.suffix in ['.json','.txt']:add(f)
for node,folder in [(2,'dynamic-05/node2'),(3,'dynamic-02/node3'),(4,'dynamic-05/node4'),(25,'dynamic-04/node25'),(7,'dynamic-07/node7')]:
 root=b/folder
 for name in ['queue-state.json','submission.json']:add(root/name,True)
 for sub in ['pending','commands','results']:
  for p in(root/sub).glob('*'):
   if any(token in p.name for token in ['267','302','307','314','sready259-eight']):add(p,True)
 for p in root.glob('*.log'):
  if any(token in p.name for token in ['native-residual','sready259-eight']):add(p,True)
for n in [2670,2671,2672,2950,2951,3140,3141,3142]:
 root=b/('r256-composition-274/upper-candidates/'+str(n)+'/route');add(root/'receipt.json',True);add(root/'locked-original-output-search.json',True)
 for p in root.glob('trial-*/router.log'):add(p,True)
 add(root/'openroad-search/case-0/openroad.log',True)
rows=[]
for p,live in sorted(paths.items()):
 raw=p.read_bytes();r=dict(path=str(p),relative=str(p.relative_to(b)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(raw)<=524288:r['base64']=base64.b64encode(raw).decode()
 rows.append(r)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False,scope='Actual final23-type345-instance complete native diagnostic passed with all TOP outputs constrained, three-initial eight-program full-cell success, retained residual receipt race and original three failing minimum-pin placements, four measured-budget placements passing all three necessary corners, eight real full-route chains with all48 successors, exact own three-step retirement, and actual R646 optional priority proof. Live route prefixes never imply eventual geometry/PG/RC300MHz success.')))
'''
compile(q,'proof45','exec')
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir();copied=0
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 raw=base64.b64decode(encoded);assert len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);copied+=1
helpers=[]
names=['control162-residual-retry302.py', 'control162-native-aware-placement307.py', 'control162-priority-regression314.py', 'control162-r256-slot-refill311.py', 'control162-r256-upper267.py', 'control162-r256-full-refill314.py', 'control162-real-progress310.py', 'control162-own-active309.py', 'control162-r256-route-status315.py', 'control162-collect-proof45.py']
for name in names:
 p=home/name;assert p.is_file(),name;target=out/'helpers'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(p,target);helpers.append(dict(relative=str(target.relative_to(out)),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size))
d.update(helpers=helpers,copied_count=copied);(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
with(repo/'.gitattributes').open('a',encoding='utf-8')as f:f.write('\nwork/YUZE-LU/162/continuation-proof-45/** -text\n')
print(json.dumps(dict(indexed=len(d['rows']),copied=copied,helpers=len(helpers),captured_at=d['captured_at'],whole_system_qualified=False)))
