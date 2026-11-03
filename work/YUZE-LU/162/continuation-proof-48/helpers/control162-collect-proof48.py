from pathlib import Path
import subprocess,shlex,json,hashlib,base64,shutil
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=repo.parent.parent;out=repo/'work/YUZE-LU/162/continuation-proof-48';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,time,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-359';paths={}
def add(p,live=False):
 if p.is_file():paths[p]=paths.get(p,False)or live
for n in ['source-manifest.json','freeze-import.json']:add(b/'source-388'/n)
for p in(b/'r256-reset53-final-function-audit-392').glob('*.json'):add(p)
for name in ['receipt.json','initial-1-162.json','initial-2-162.json','initial-2-163.json','hierarchical-inputs.json','actual-qualified-top.v','build.log']:add(root/'function'/name)
for folder in(b/'route-selection-102').glob('*'):
 if folder.name.startswith(tuple('sready'+str(n)for n in [389,390,393])):
  for p in folder.rglob('*.json'):add(p)
for seed in [3730,3731,3732,3733,3734,3740,3741,3750,3751,3840,3841,3890,3891,3930,3931]:
 add(root/('acceptance-'+str(seed)+'.json'));base=root/'upper-candidates'/str(seed)/'route'
 for name in ['receipt.json','progress.json','trial-index.json','locked-original-output-search.json','search.json']:add(base/name,True)
 for p in(base.glob('trial-*/router.log')if seed in [3890,3891,3930,3931]else base.glob('trial-0/router.log')):add(p,True)
 add(base/'openroad-search/case-0/openroad.log',True)
for folder in ['dynamic-05/node2','dynamic-02/node3','dynamic-05/node4','dynamic-04/node25','dynamic-07/node7','dynamic-03/node5','dynamic-02/node6','dynamic-06/node26']:
 base=b/folder;add(base/'queue-state.json',True)
 for sub in ['pending','commands','results']:
  for p in(base/sub).glob('*'):
   if any('sready'+str(n)in p.name for n in [389,393]):add(p,True)
 for p in base.glob('*.log'):
  if any('sready'+str(n)in p.name for n in [389,393]):add(p,True)
rows=[]
for p,live in sorted(paths.items()):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for part in iter(lambda:f.read(1048576),b''):h.update(part)
 row=dict(path=str(p),relative=str(p.relative_to(b)),bytes=p.stat().st_size,sha256=h.hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if row['bytes']<=524288 or p==root/'function/receipt.json':
  raw=p.read_bytes();row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode())
 rows.append(row)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False,scope='Actual current reset53 scene359 final23-PG-cell eight-programs allthree initialization runs completed, independent392 exactfullview/topology audit. Source388 optional finite route budgets subtract measured native ground and minimum pin loads through original source-bound helper. Actual389/393 hook fingerprints, genuine partial failed trials, exacttwoown235 obsolete search retirements390, natural dynamic refill393 and full seven-stage successor chains. Earlier native/placement/geometry definition evidence referenced via47/46/current363 rather than recopied. Full M11/M12 geometry/PG/lowbasehighRC300MHz/joint qualification still absent.')))
'''
data=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir();copied=0
for row in data['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 raw=base64.b64decode(encoded);assert len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);copied+=1
helpers=[]
for name in ['control162-budget389.py','control162-retire390.py','control162-retire385.py','control162-budget-failure391.py','control162-function392.py','control162-refill393.py','control162-collect-proof48.py']:
 p=home/name;target=out/'helpers'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(p,target);helpers.append(dict(relative=target.relative_to(out).as_posix(),bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
data.update(helpers=helpers,copied_count=copied);(out/'index.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
with(repo/'.gitattributes').open('a',encoding='utf-8')as f:f.write('\nwork/YUZE-LU/162/continuation-proof-48/** -text\n')
print(json.dumps(dict(indexed=len(data['rows']),copied=copied,helpers=len(helpers),captured_at=data['captured_at'])))
