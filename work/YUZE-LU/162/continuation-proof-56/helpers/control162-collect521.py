from pathlib import Path
import subprocess,shlex,json,hashlib,base64
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-56';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';paths={}
def add(p,live=False):
 if p.is_file():paths[p]=live
for name in ['source-manifest.json','freeze-import.json']:add(b/'source-510'/name)
for folder in ['r256-bidirectional-search-regression-500','r256-ordinary-cost-regression-511','r256-ordinary-cost-controlled-comparison-515']:
 for p in(b/folder).glob('*.json'):add(p)
for prefix in ['sready500','sready511','sready513','sready519','sready520']:
 for folder in(b/'route-selection-102').glob(prefix+'*'):
  for p in folder.glob('*.json'):add(p)
for seed in [5010,5120,5190,5191,5192]:
 base=root/'upper-candidates'/str(seed)/'route'
 for name in ['receipt.json','router-input.txt','router-distance-oracle.json','locked-original-output-search.json','memory-admission.json']:add(base/name,True)
 for p in base.glob('trial-*/router.log'):add(p,True)
for folder in ['dynamic-05/node2','dynamic-02/node3','dynamic-02/node6','dynamic-04/node25']:
 base=b/folder;add(base/'queue-state.json',True)
 for sub in ['pending','commands','results']:
  for p in(base/sub).glob('*'):
   if any(x in p.name for x in ['sready500','sready501','sready511','sready512','sready519']):add(p,True)
rows=[]
for p,live in sorted(paths.items()):
 data=p.read_bytes();row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(data)<=524288 or p.name=='router-search-regression.json':row['base64']=base64.b64encode(data).decode()
 rows.append(row)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False)))
'''
d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir()
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 data=base64.b64decode(encoded);assert len(data)==row['bytes']and hashlib.sha256(data).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
d['helpers']=[]
for n in ['docs504','status506','progress507','queue511','queue511-remote','refill513','refill513-remote','compare515','pool516','verify518','queue519','queue519-remote','refill520','refill520-remote','collect521']:
 p=home/('control162-'+n+'.py');data=p.read_bytes();rel='helpers/'+p.name;t=out/rel;t.parent.mkdir(exist_ok=True);t.write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
for n in [505,510]:
 p=home/('control162-git-data-publish-'+str(n))/'receipt.json';data=p.read_bytes();rel='helpers/publication-'+str(n)+'.json';(out/rel).write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
for name in ['control162-online514-pr-verified.json','control162-online514-issue-verified.json']:
 p=home/name;data=p.read_bytes();rel='helpers/'+name;(out/rel).write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
