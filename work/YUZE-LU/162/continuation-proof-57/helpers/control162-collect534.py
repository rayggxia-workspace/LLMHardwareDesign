from pathlib import Path
import subprocess,shlex,json,hashlib,base64
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-57';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');paths={}
def add(p,live=False):
 if p.is_file():paths[p]=live
for folder in ['r256-padding-program-events-473','r256-padding-program-event-audit-480','r256-ordinary-window-regression-525','r256-s-pair-span-532']:
 for p in(b/folder).glob('*'):add(p)
for prefix in ['sready480','sready525','sready527']:
 for folder in(b/'route-selection-102').glob(prefix+'*'):
  for p in folder.glob('*'):add(p)
for name in ['source-manifest.json','freeze-import.json']:add(b/'source-524'/name)
base=b/'r256-composition-453/upper-candidates/5260/route'
for name in ['receipt.json','router-distance-oracle.json','router-input.txt','locked-original-output-search.json','memory-admission.json']:add(base/name,True)
for p in base.glob('trial-*/router.log'):add(p,True)
for folder in ['dynamic-02/node3','dynamic-04/node25']:
 base=b/folder;add(base/'queue-state.json',True)
 for sub in ['pending','commands','results']:
  for p in(base/sub).glob('*'):
   if any(x in p.name for x in ['sready525','sready526','sready473']):add(p,True)
rows=[]
for p,live in sorted(paths.items()):
 # Do not read compiled binaries/archives as evidence transport.
 if p.suffix not in ['.json','.jsonl','.cpp','.stdout','.log','.txt']:continue
 data=p.read_bytes();row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(data)<=524288 or(p.parent.name=='r256-padding-program-events-473'and p.suffix=='.jsonl'):row['base64']=base64.b64encode(data).decode()
 rows.append(row)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False)))
'''
d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir()
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 data=base64.b64decode(encoded);assert len(data)==row['bytes']and hashlib.sha256(data).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
d['helpers']=[]
for n in ['docs522','queue525','queue525-remote','refill527','refill527-remote','span528','place529','s-span532','s-span532-remote','prepare480','ready480','ready480-remote','event-audit480-remote','collect534']:
 p=home/('control162-'+n+'.py');data=p.read_bytes();rel='helpers/'+p.name;t=out/rel;t.parent.mkdir(exist_ok=True);t.write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
for n in [523,524]:
 p=home/('control162-git-data-publish-'+str(n))/'receipt.json';data=p.read_bytes();rel='helpers/publication-'+str(n)+'.json';(out/rel).write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
