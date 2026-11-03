from pathlib import Path
import subprocess,shlex,json,hashlib,base64,time
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');h=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-61';assert not out.exists()
code=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');rows=[]
for name in ['r256-pending-c96-controller-audit-602','r256-zero-pattern-source-invariance-603']:
 p=b/name/'receipt.json';raw=p.read_bytes();assert json.loads(raw.decode())['passed'];rows.append(dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode()))
print(json.dumps(dict(time=time.time(),rows=rows,whole_system_qualified=False)))
'''
d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],timeout=45));out.mkdir()
for row in d['rows']:
 raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True);p.write_bytes(raw);row['copied']=True
d['helpers']=[]
items={('helpers/control162-'+n):h/('control162-'+n)for n in ['online598-issue-verified.json','online598-pr-request.json','online598-pr-verified.json','verify599.py','read600.py','watch601.py','audit602.py','audit603.py','proof604.py']}
items['helpers/publication-597.json']=h/'control162-git-data-publish-597/receipt.json'
snapshots=sorted((h/'control162-watch601').glob('*.json'))
for p in [snapshots[0],snapshots[-1]]:items['selected-running-snapshots/'+p.name]=p
for name,p in items.items():
 raw=p.read_bytes();t=out/name;t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(raw);d['helpers'].append(dict(relative=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
d['scope']='Read-only exact source invariance and pending c96-controller audits, exact online body readbacks/publication and two explicitly selected still-running snapshots. No full route/physical/300MHz acceptance implied.'
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),helpers=len(d['helpers']))))
