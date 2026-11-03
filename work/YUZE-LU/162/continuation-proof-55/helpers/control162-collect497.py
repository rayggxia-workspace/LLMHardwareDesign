from pathlib import Path
import subprocess,shlex,json,hashlib,base64
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-55';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';paths={}
def add(p,live=False):
 if p.is_file():paths[p]=live
for n in [474,483,489]:
 for name in ['source-manifest.json','freeze-import.json']:add(b/('source-'+str(n))/name)
for folder in ['r256-high-weight-regression-475','r256-controlled-high-weight-comparison-481','r256-rectilinear-ratio-bound-482','r256-padding-final-function-audit-472','r256-search-phase-analysis-498','r256-bidirectional-search-regression-500']:
 for p in(b/folder).glob('*.json'):add(p)
for prefix in ['sready476','sready477','sready484','sready486','sready490','sready494','sready495','sready500']:
 for folder in(b/'route-selection-102').glob(prefix+'*'):
  for p in folder.glob('*'):add(p)
for folder in ['r256-search-phase-profile-494','r256-composition-453/function']:
 for p in(b/folder).glob('*.json'):add(p,True)
for p in(b/'r256-search-phase-profile-494/profile').glob('*'):
 if p.suffix in ['.json','.log','.cpp']:add(p,True)
for p in(b/'r256-search-phase-profile-494/profile').glob('trial-*/profile.log'):add(p,True)
for seed in [4760,4850]:
 base=root/'upper-candidates'/str(seed)/'route'
 for name in ['receipt.json','router-input.txt','router-distance-oracle.json','locked-original-output-search.json','memory-admission.json']:add(base/name,True)
 for p in base.glob('trial-*/router.log'):add(p,True)
for folder in ['dynamic-05/node4','dynamic-02/node6','dynamic-04/node25','dynamic-07/node7']:
 base=b/folder;add(base/'queue-state.json',True)
 for sub in ['pending','commands','results']:
  for p in(base/sub).glob('*'):
   if any(x in p.name for x in ['sready475','sready476','sready484','sready485','sready490','sready494','sready500','sready501']):add(p,True)
rows=[]
for p,live in sorted(paths.items()):
 data=p.read_bytes();row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(data)<=524288:row['base64']=base64.b64encode(data).decode()
 rows.append(row)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False)))
'''
d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir()
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 data=base64.b64decode(encoded);assert len(data)==row['bytes']and hashlib.sha256(data).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
d['helpers']=[]
for n in ['queue476','queue476-remote','refill477','refill477-remote','compare481','bound482','queue484','queue484-remote','refill486','refill486-remote','status487','inspect488','queue490','queue490-remote','inspect491','proc492','inspect493','queue494','queue494-remote','refill495','refill495-remote','profile496','prepare480','ready472','ready480','event-audit480-remote','analyse498','analyse498-remote','detail499','queue500','queue500-remote','collect497']:
 p=home/('control162-'+n+'.py');data=p.read_bytes();rel='helpers/'+p.name;t=out/rel;t.parent.mkdir(exist_ok=True);t.write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
for n in [471,474,483,489]:
 p=home/('control162-git-data-publish-'+str(n))/'receipt.json';data=p.read_bytes();rel='helpers/publication-'+str(n)+'.json';(out/rel).write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
for name in ['control162-online479-pr-verified.json','control162-online479-issue-verified.json']:
 p=home/name
 if p.exists():
  data=p.read_bytes();rel='helpers/'+name;(out/rel).write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
