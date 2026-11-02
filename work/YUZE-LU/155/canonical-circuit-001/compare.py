import json,hashlib,re,os
from pathlib import Path
assert os.environ.get('SLURM_JOB_ID')
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155')
a=b/'delay-probe-002/stages49/trimmed.sp';c=b/'generate-008/openram-temp/trimmed.sp'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parse(p):
 lines=[]
 for line in p.read_text().splitlines():
  line=line.strip()
  if not line or line.startswith('*'):continue
  if line.startswith('+'):assert lines;lines[-1]+=' '+line[1:]
  else:lines.append(line)
 cells={};current=None
 for line in lines:
  line=' '.join(line.lower().split())
  if line.startswith('.subckt '):
   assert current is None;words=line.split();current=words[1];assert current not in cells;cells[current]=dict(ports=words[2:],elements=[])
  elif line.startswith('.ends'):
   assert current is not None
   words=line.split();cells[current]['end_tokens']=words[1:];current=None
  else:assert current is not None,line;cells[current]['elements'].append(line)
 assert current is None
 for cell in cells.values():cell['elements'].sort()
 return cells
inputs={str(p):sha(p) for p in (a,c)};x,y=parse(a),parse(c)
different=[n for n in sorted(set(x)|set(y)) if x.get(n)!=y.get(n)]
r=dict(passed=not different,qualified=False,scope='Canonical named-device and ordered-port SPICE comparison only; permits comments, whitespace, case and definition/element ordering, not device or node substitutions; no internal wire PEX or timing qualification',inputs=inputs,subcircuits_old=len(x),subcircuits_new=len(y),different_cells=different)
for n in different[:4]:
 r.setdefault('differences',{})[n]=dict(old_only=sorted(set(x.get(n,{}).get('elements',[]))-set(y.get(n,{}).get('elements',[])))[:6],new_only=sorted(set(y.get(n,{}).get('elements',[]))-set(x.get(n,{}).get('elements',[])))[:6])
assert all(sha(Path(p))==h for p,h in inputs.items())
(b/'canonical-circuit-001.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))


