"""Capture actual R256 native/PG work, recovery and routing evidence."""
from pathlib import Path
import subprocess,shlex,json,hashlib,base64,shutil
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=repo.parent.parent;out=repo/'work/YUZE-LU/162/continuation-proof-46';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,time,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');paths={}
def add(p,live=False):
 if p.is_file():paths[p]=paths.get(p,False)or live
for n in [323,335,350,358]:
 for name in ['source-manifest.json','freeze-import.json']:add(b/('source-'+str(n))/name)
for stem in ['r256-global-report-probe-324','r256-pin-escape-diagnostic-330','r256-grid-capacity-diagnostic-331','r256-grid-cut-diagnostic-339','r256-native-tree-cap-diagnostic-347','r256-complete-path-preflight-337','r256-complete-path-full-337','r256-native-353/3530','r256-fixed-pg-356/3530','r256-composition-359']:
 for p in(b/stem).rglob('*'):
  if p.suffix in ['.json','.log','.rpt','.tsv','.tcl','.ys','.txt','.lyrdb'] and not any(n in p.parts for n in ['obj','objects','gds-flow','fixed-pg-wrappers']):add(p,True)
for p in(b/'route-selection-102').glob('*'):
 if p.name.startswith(tuple('sready'+str(n)for n in [325,337,338,344,345,353,354,356,359])):
  for f in p.rglob('*'):
   if f.suffix in ['.json','.txt']:add(f)
for folder in ['dynamic-05/node2','dynamic-02/node3','dynamic-05/node4','dynamic-04/node25','dynamic-07/node7','dynamic-03/node5','dynamic-02/node6','dynamic-06/node26']:
 root=b/folder
 for name in ['queue-state.json','submission.json']:add(root/name,True)
 for sub in ['pending','commands','results']:
  for p in(root/sub).glob('*'):
   if any(token in p.name for token in ['sready'+str(n)for n in [325,337,344,353,356,359]]):add(p,True)
 for p in root.glob('*.log'):
  if any(token in p.name for token in ['sready'+str(n)for n in [325,337,344,353,356,359]]):add(p,True)
for n in [2670,2671,2672,2950,2951,3140,3141,3142,3250,3440,3441]:
 root=b/('r256-composition-274/upper-candidates/'+str(n)+'/route');add(root/'receipt.json',True)
 for p in root.glob('trial-*/router.log'):add(p,True)
 for p in(root/'openroad-search/case-0').glob('*'):
  if p.suffix in ['.rpt','.log','.json','.tcl']:add(p,True)
rows=[]
for p,live in sorted(paths.items()):
 raw=p.read_bytes();r=dict(path=str(p),relative=str(p.relative_to(b)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(raw)<=524288:r['base64']=base64.b64encode(raw).decode()
 rows.append(r)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False,scope='Retained actual FastRoute3142 60um failure, explicit24um report preflight324/full3250, exact currentR first-round complete-path replay337, static diagnostics including330 horizontal-only correction, stronger metric MST/2 proof rejecting all four old placements, exact8 own searches retired only after reset53 replacement queued, actual reset53 native/fullDRC/PG/300MHz/function/strictLEC qualification, actual rewired scene359 and ongoing programs/native/placements. Live prefixes and necessary tests never qualify whole-system geometry/PG/three-RC/300MHz.')))
'''
compile(q,'proof45','exec')
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir();copied=0
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 raw=base64.b64decode(encoded);assert len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);copied+=1
helpers=[]
names=['control162-r256-path-queue337.py', 'control162-r256-path-refill338.py', 'control162-grid-cut339.py', 'control162-r256-alternative344.py', 'control162-r256-node6-refill345.py', 'control162-tree-cap347.py', 'control162-reset-owner348.py', 'control162-reset53-native353.py', 'control162-tree-bound-retire354.py', 'control162-reset53-pg356.py', 'control162-reset53-scene359.py', 'control162-reset53-index361.py', 'control162-receive-reset53-361.py', 'control162-current-reset53-delivery363.py', 'control162-collect-proof46.py']
for name in names:
 p=home/name;assert p.is_file(),name;target=out/'helpers'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(p,target);helpers.append(dict(relative=str(target.relative_to(out)),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size))
d.update(helpers=helpers,copied_count=copied);(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
with(repo/'.gitattributes').open('a',encoding='utf-8')as f:f.write('\nwork/YUZE-LU/162/continuation-proof-46/** -text\n')
print(json.dumps(dict(indexed=len(d['rows']),copied=copied,helpers=len(helpers),captured_at=d['captured_at'],whole_system_qualified=False)))
