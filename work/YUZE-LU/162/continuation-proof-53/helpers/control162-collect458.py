from pathlib import Path
import subprocess,shlex,json,hashlib,base64
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-53';assert not out.exists()
q="""from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');paths={};root=b/'r256-composition-453'
def add(p,live=False):
 if p.is_file():paths[p]=live
for name in ['source-manifest.json','freeze-import.json']:add(b/'source-451'/name)
for folder in ['r256-controlled-priority-comparison-445','r256-full-axis-cut-446','r256-unused-link-input-load-450','r256-padding-load-count-456','r256-padding-whole-topology-audit-457']:
 for p in(b/folder).glob('*.json'):add(p)
for folder in ['sready453-unused-link-load','sready454-unused-link-load-refill']:
 for p in(b/'route-selection-102'/folder).glob('*.json'):add(p)
for folder in ['contract','topology','cap-initial','native-sta','native-residual','native-pin-load','function']:
 for p in(root/folder).glob('*.json'):add(p,folder in ['native-sta','function'])
for name in ['combined.v','extract.log']:add(root/'topology'/name)
for folder in ['dynamic-05/node2','dynamic-04/node25']:
 d=b/folder;add(d/'queue-state.json',True)
 for sub in ['pending','commands','results']:
  for p in(d/sub).glob('*sready453*'):add(p,True)
 for p in d.glob('*sready453*.log'):add(p,True)
for candidate in [4340,4390]:
 for p in(b/'r256-composition-359/upper-candidates'/str(candidate)/'route').glob('trial-*/router.log'):add(p,True)
rows=[]
for p,live in sorted(paths.items()):
 data=p.read_bytes();row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(data)<=524288:row['base64']=base64.b64encode(data).decode()
 rows.append(row)
tails=[]
for folder in ['function','native-sta']:
 for p in(root/folder).glob('*.log'):
  size=p.stat().st_size;offset=max(0,size-4096)
  with p.open('rb')as f:f.seek(offset);data=f.read(4096)
  tails.append(dict(relative='bounded-tails/'+folder+'-'+p.name,source=str(p),source_size_at_capture=size,offset=offset,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),base64=base64.b64encode(data).decode(),scope='Bounded tail window only, not full log or a completed run'))
print(json.dumps(dict(captured_at=time.time(),rows=rows,tails=tails,whole_system_qualified=False)))
"""
d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir()
for row in d['rows']+d['tails']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is None:continue
 data=base64.b64decode(encoded);assert len(data)==row['bytes']and hashlib.sha256(data).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
d['helpers']=[]
for n in ['compare445','compare445-remote','axis446','net449','pad450','queue453','queue453-remote','refill454','refill454-remote','current455','pad456','audit457','collect458']:
 p=home/('control162-'+n+'.py');data=p.read_bytes();rel='helpers/'+p.name;t=out/rel;t.parent.mkdir(exist_ok=True);t.write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
online=json.loads((home/'control162-online447-issue-verified.json').read_text(encoding='utf-8'));pr=json.loads((home/'control162-online447-pr-readback.json').read_text(encoding='utf-8'));expected=(home/'control162-online447-pr-expected.md').read_text(encoding='utf-8');assert pr['body'].rstrip()==expected.rstrip();online.update(pr_body_exact=True,pr_draft=pr['draft'],pr_merged=pr['merged'],pr_head_at_readback=pr['head']['sha'],pr_body_sha256=hashlib.sha256(pr['body'].encode()).hexdigest());data=(json.dumps(online,indent=2)+'\n').encode();p=out/'helpers/online-readback.json';p.write_bytes(data);d['helpers'].append(dict(relative='helpers/online-readback.json',bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
for label in ['435','442','448','451']:
 p=home/('control162-git-data-publish-'+label)/'receipt.json';data=p.read_bytes();rel='helpers/publication-'+label+'.json';(out/rel).write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),tails=len(d['tails']),helpers=len(d['helpers']))))
