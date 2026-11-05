from pathlib import Path
import subprocess,shlex,json,hashlib,base64
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-54';assert not out.exists()
q="""from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';paths={}
def add(p,live=False):
 if p.is_file():paths[p]=live
for folder in ['native-sta','native-residual','native-pin-load','function','topology']:
 for p in(root/folder).glob('*.json'):add(p,folder=='function')
for name in ['timing-summary.tsv','electrical-worst.rpt','electrical-violations.rpt','critical-first.rpt']:add(root/'native-sta'/name)
for seed in [4610,4611]:
 for p in(root/'cap-candidates'/str(seed)).glob('*.json'):add(p)
 for stage in ['native-residual','native-pin-load']:
  for p in(root/'cap-necessary-461'/str(seed)/stage).glob('*.json'):add(p)
for folder in ['r256-padding-bank-unit-slurm-462']:
 for p in(b/folder).glob('*'):add(p)
for prefix in ['sready461','sready463','sready464','sready466','sready467']:
 for folder in(b/'route-selection-102').glob(prefix+'*'):
  for p in folder.glob('*.json'):add(p)
for seed in [4660,4661,4670]:
 base=root/'upper-candidates'/str(seed)/'route'
 for name in ['receipt.json','router-input.txt','router-distance-oracle.json','locked-original-output-search.json','memory-admission.json']:add(base/name,True)
 for p in base.glob('trial-*/router.log'):add(p,True)
for folder in ['dynamic-05/node2','dynamic-05/node4','dynamic-04/node25']:
 base=b/folder;add(base/'queue-state.json',True)
 for sub in ['pending','commands','results']:
  for p in(base/sub).glob('*'):
   if any(x in p.name for x in ['sready461','sready466','sready467']):add(p,True)
rows=[]
for p,live in sorted(paths.items()):
 data=p.read_bytes();row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(data)<=524288 or p==root/'topology/boundary-graph.json':row['base64']=base64.b64encode(data).decode()
 rows.append(row)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False)))
"""
d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir()
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 data=base64.b64decode(encoded);assert len(data)==row['bytes']and hashlib.sha256(data).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
d['helpers']=[]
for n in ['queue461','queue461-remote','test462','refill463','refill463-remote','diagnose463','refill464','refill464-remote','status465','queue466','queue466-remote','queue467','queue467-remote','collect468']:
 p=home/('control162-'+n+'.py');data=p.read_bytes();rel='helpers/'+p.name;t=out/rel;t.parent.mkdir(exist_ok=True);t.write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
p=home/'control162-git-data-publish-460/receipt.json';data=p.read_bytes();rel='helpers/publication-460.json';(out/rel).write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
