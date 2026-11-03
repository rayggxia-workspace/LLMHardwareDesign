import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');r=b/'r256-composition-453';p=json.loads((r/'cap-candidates/4610/placement.json').read_text());print('keys',list(p));print('selected',{k:v for k,v in p.items()if not isinstance(v,(dict,list))})
m=json.loads((b/'r256-composition-359/selected/physical.json').read_text());g=json.loads((r/'topology/boundary-graph.json').read_text());print('sizes',{n:m['leaves'][g['instances'][n]]['die_um']for n in ['macro_s','s_port']})
for k,v in p.items():
 if isinstance(v,dict):
  print(k,'keys',list(v)[:6])
  for name in ['macro_s','s_port','controller','macro_r']:
   if name in v:print(k,name,v[name])
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
