import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,subprocess,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');record=b/'route-selection-102/sready238-pending-refill';assert not record.exists()
state=subprocess.check_output(['squeue','-j','96222','-h','-o','%T'],universal_newlines=True).strip();assert state=='PENDING',state
old=b/'dynamic-06/node26';new=b/'dynamic-06/node7';rows=[]
for p in sorted((old/'pending').glob('*.json')):
 assert not(old/'commands'/p.name).exists()and not(old/'results'/p.name).exists()
 target=new/'pending'/p.name;assert not target.exists();raw=p.read_bytes();p.rename(target);assert target.read_bytes()==raw
 rows.append(dict(previous=str(p),path=str(target),sha256=hashlib.sha256(raw).hexdigest()))
assert len(rows)==15
record.mkdir();(record/'transfer.json').write_text(json.dumps(dict(time=time.time(),moved_unadmitted=rows,reason='Replacement node26 allocation96222 pending Priority; actual node7 has two free sixteen-CPU slots after route8 fixed-PG full delivery. Move only these never-admitted own specs with exact bytes and unchanged output/dependencies/memory forecast. New controller handles glob removal safely. No submitted/admitted work, old immutable evidence or foreign jobs modified.'),indent=2));print(json.dumps(dict(moved=len(rows))))
'''
compile(q,'refill238','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=30).decode())
