from pathlib import Path
import subprocess,shlex,json,hashlib,base64,time
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');h=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-59';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');rows=[]
for folder in ['r256-final-chain-binding-audit-579','r256-final-chain-binding-audit-581']:
 p=b/folder/'receipt.json';raw=p.read_bytes();rows.append(dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode()))
print(json.dumps(dict(time=time.time(),rows=rows,whole_system_qualified=False)))
'''
d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45));out.mkdir()
for row in d['rows']:
 raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True);p.write_bytes(raw);row['copied']=True
d['helpers']=[]
materials={('helpers/control162-'+n):h/('control162-'+n)for n in ['lane575.py','watch577.py','config579.py','config579-remote.py','read580.py','prepare581.py','config581.py','config581-remote.py','verify578.py','proof583.py','online576-issue-verified.json','online576-pr-request.json','online576-pr-verified.json','c64status573.py']}
materials['lane-diagnostic/receipt.json']=h/'LLMHardwareDesign-deliveries/issue-162/lane-assignment-diagnostic-575/receipt.json';materials['helpers/publication-572.json']=h/'control162-git-data-publish-572/receipt.json'
for name,p in materials.items():
 raw=p.read_bytes();t=out/name;t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(raw);d['helpers'].append(dict(relative=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
d['known_failed_metadata_assertion']=dict(receipt='r256-final-chain-binding-audit-579/receipt.json',cause="Diagnostic assumed pg and sta-low instead of declared pg-audit and timing/low. No stage specification, acceptance config, source, output or live job changed.581 independently matches actual queued-stage output arguments, all12configs/84specs and current453 exact wired top/function receipt.")
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),helpers=len(d['helpers']))))
