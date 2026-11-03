from pathlib import Path
import subprocess,shlex,json,hashlib,base64,time
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');h=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-60';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');files=[]
reg=b/'r256-zero-pattern-regression-589';assert json.loads((reg/'receipt.json').read_text())['passed'];files+=list(reg.rglob('*'))
for name in ['sready589-zero-pattern-controlled','sready590-zero-pattern-refill']:files+=list((b/'route-selection-102'/name).rglob('*'))
for name in ['r256-final-chain-binding-audit-592','r256-zero-pattern-active-pool-audit-593']:files+=list((b/name).rglob('*'))
files+=[b/'source-587/source-manifest.json',b/'source-587/freeze-import.json',b/'r256-composition-453/acceptance-5890.json']
tasks=json.loads((b/'route-selection-102/sready589-zero-pattern-controlled/tasks.json').read_text())['tasks'];files += [Path(t['path'])for t in tasks]
rows=[]
for p in sorted(set(files)):
 if not p.is_file():continue
 raw=p.read_bytes();copy=p.suffix in ['.json','.txt','.log','.cpp','.h']and len(raw)<1000000
 row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),copied=copy)
 if copy:row['base64']=base64.b64encode(raw).decode()
 rows.append(row)
print(json.dumps(dict(time=time.time(),rows=rows,whole_system_qualified=False)))
'''
d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45));out.mkdir()
for row in d['rows']:
 if row['copied']:
  raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
d['helpers']=[]
names=['prepare589.py','queue589-remote.py','prepare590.py','refill590-remote.py','check591.py','prepare592.py','config592-remote.py','prepare593.py','audit593.py','progress594.py','proof595.py']
for name in names:
 raw=(h/('control162-'+name)).read_bytes();p=out/'helpers'/('control162-'+name);p.parent.mkdir(exist_ok=True);p.write_bytes(raw);d['helpers'].append(dict(relative=str(p.relative_to(out)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
p=h/'control162-git-data-publish-588/receipt.json';raw=p.read_bytes();target=out/'helpers/publication-588.json';target.write_bytes(raw);d['helpers'].append(dict(relative=str(target.relative_to(out)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
d['scope']='Actual full589 regression, immutable source587 binding,8 task specs, exact own4050 step reallocation guard,592 final-chain binding and593 actual16PID/input-pair/memory audit. Candidate5890 physical search still running; all final physical/RC/300MHz gates required. Executables retained remote by hash; copied text raw bytes preserved.'
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
