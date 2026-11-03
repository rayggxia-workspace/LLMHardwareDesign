"""Capture only new source-bound milestones and live route prefixes."""
from pathlib import Path
import subprocess,shlex,json,hashlib,base64,shutil
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=repo.parent.parent;out=repo/'work/YUZE-LU/162/continuation-proof-47';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,time,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');paths={}
def add(p,live=False):
 if p.is_file():paths[p]=paths.get(p,False)or live
for name in ['source-manifest.json','freeze-import.json']:add(b/'source-383'/name)
for stem in ['r256-complete-path-full-337','r256-reset53-priority-regression-375','r256-congestion-summary-376','r256-congestion-summary-correction-378','r256-directional-regression-384']:
 for p in(b/stem).rglob('*'):
  if p.suffix in ['.json','.txt','.log']:add(p,stem.endswith('384'))
add(b/'r256-reset53-priority-isolated-failure-375.json')
root=b/'r256-composition-359'
for sub in ['selected','topology','native-sta','native-residual369','native-pin-load369','cap-necessary-371','cap-candidates/3690','cap-candidates/3691','cap-candidates/3692','cap-candidates/3693','function']:
 for p in(root/sub).rglob('*'):
  if any(v in p.parts for v in ['obj','objects']):continue
  if p.suffix in ['.json','.log','.rpt','.tsv','.txt']and not(p.name=='build.log'):add(p,sub=='function')
add(root/'function/build.log',True)
for seed in [3730,3731,3732,3733,3734,3740,3741,3750,3751,3840,3841]:
 add(root/('acceptance-'+str(seed)+'.json'))
 base=root/'upper-candidates'/str(seed)/'route'
 for p in base.glob('*'):
  if p.suffix=='.json':add(p,True)
 for p in base.glob('trial-*/router.log'):add(p,True)
 for p in(base/'openroad-search/case-0').glob('*'):
  if p.suffix in ['.rpt','.log','.json']:add(p,True)
for seed in [3250,3441]:
 base=b/'r256-composition-274/upper-candidates'/str(seed)/'route';add(base/'receipt.json',seed==3441)
 for p in(base/'openroad-search/case-0').glob('*'):
  if p.suffix in ['.rpt','.log','.json']:add(p,seed==3441)
for folder in(b/'route-selection-102').glob('*'):
 if folder.name.startswith(tuple('sready'+str(n)for n in [369,371,373,377,384,385])):
  for p in folder.rglob('*'):
   if p.suffix=='.json':add(p)
for folder in ['dynamic-05/node2','dynamic-02/node3','dynamic-05/node4','dynamic-04/node25','dynamic-07/node7','dynamic-03/node5','dynamic-02/node6','dynamic-06/node26']:
 base=b/folder
 for name in ['queue-state.json','submission.json']:add(base/name,True)
 for sub in ['pending','commands','results']:
  for p in(base/sub).glob('*'):
   if any('sready'+str(n)in p.name for n in [369,371,373,377,384]):add(p,True)
 for p in base.glob('*.log'):
  if any('sready'+str(n)in p.name for n in [369,371,373,377,384]):add(p,True)
rows=[]
for p,live in sorted(paths.items()):
 raw=p.read_bytes();row=dict(path=str(p),relative=str(p.relative_to(b)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(raw)<=524288:row['base64']=base64.b64encode(raw).decode()
 rows.append(row)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False,scope='Actual final337 full16-path diagnostic, new native359 audit, four measured/stronger-bound placements3690-3, individually independent prerequisites371, nine actual full current-scene routes373/377 plus two directional384, real nine-case/default-byte-replay/rejection regression, exact two old235 own steps replaced only after full successor chains queued, current359 final-cell program prefixes. Preserve original faulty isolated375 test and congestion376 report-completeness claim with explicit378 retraction; truncated congestion reports do not establish global coverage. All live prefixes/search or native/necessary checks are not joint whole-system qualification.')))
'''
data=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir();copied=0
for row in data['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 raw=base64.b64decode(encoded);assert len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);copied+=1
helpers=[]
for name in ['control162-reset53-native-aware-placement369.py','control162-independent-necessary371.py','control162-reset53-upper373.py','control162-reset53-route-binding374.py','control162-reset53-priority375.py','control162-reset53-priority375-isolated-failed.py','control162-complete-diagnostic376.py','control162-congestion-report-correction378.py','control162-current380.py','control162-directional384.py','control162-retire385.py','control162-collect-proof47.py']:
 p=home/name;assert p.is_file(),name;target=out/'helpers'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(p,target);helpers.append(dict(relative=target.relative_to(out).as_posix(),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size))
data.update(helpers=helpers,copied_count=copied);(out/'index.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
with(repo/'.gitattributes').open('a',encoding='utf-8')as f:f.write('\nwork/YUZE-LU/162/continuation-proof-47/** -text\n')
print(json.dumps(dict(indexed=len(data['rows']),copied=copied,helpers=len(helpers),captured_at=data['captured_at'],whole_system_qualified=False)))
