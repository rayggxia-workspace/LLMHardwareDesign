from pathlib import Path
import subprocess,shlex,json,hashlib,base64
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-57';index=out/'index.json';d=json.loads(index.read_text(encoding='utf-8'));assert 'translation_supplement'not in d
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');paths={}
def add(p,live=False):
 if p.is_file():paths[p]=live
for folder in ['r256-s-only-local-placement-531','r256-composition-453/cap-candidates/5380','r256-composition-453/cap-necessary-538/5380/native-residual','r256-composition-453/cap-necessary-538/5380/native-pin-load']:
 for p in(b/folder).glob('*'):add(p)
for prefix in ['sready531','sready538','sready540']:
 for folder in(b/'route-selection-102').glob(prefix+'*'):
  for p in folder.glob('*'):add(p)
for n in [530,537]:
 for name in ['source-manifest.json','freeze-import.json']:add(b/('source-'+str(n))/name)
base=b/'r256-composition-453/upper-candidates/5400/route'
for name in ['receipt.json','router-distance-oracle.json','router-input.txt','locked-original-output-search.json','memory-admission.json']:add(base/name,True)
for p in base.glob('trial-*/router.log'):add(p,True)
for sub in ['pending','commands','results']:
 for p in(b/'dynamic-04/node25'/sub).glob('*'):
  if any(x in p.name for x in ['sready538','sready540']):add(p,True)
rows=[]
for p,live in sorted(paths.items()):
 if p.suffix not in ['.json','.log','.txt','.stdout']:continue
 data=p.read_bytes();row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),capture_time=time.time(),active_prefix_snapshot=live)
 if len(data)<=524288:row['base64']=base64.b64encode(data).decode()
 rows.append(row)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False)))
'''
s=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55))
for row in s['rows']:
 row['relative']='S-translation-supplement/'+row['relative'];encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is not None:
  data=base64.b64decode(encoded);assert hashlib.sha256(data).hexdigest()==row['sha256'];p=out/row['relative'];assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
d['rows']+=s['rows'];d['translation_supplement']={k:v for k,v in s.items()if k!='rows'}
for name in ['preserve535.py','deliver536.py','launch531.py','launch531-remote.py','queue538.py','queue538-remote.py','queue540.py','queue540-remote.py','resource541.py','supplement542.py','capture535-failure.json']:
 p=home/('control162-'+name);data=p.read_bytes();rel='helpers/'+p.name;t=out/rel;assert not t.exists();t.write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
for n in [530,537]:
 p=home/('control162-git-data-publish-'+str(n))/'receipt.json';data=p.read_bytes();rel='helpers/publication-'+str(n)+'.json';assert not(out/rel).exists();(out/rel).write_bytes(data);d['helpers'].append(dict(relative=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
index.write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(total_rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']),whole_system_qualified=False)))
