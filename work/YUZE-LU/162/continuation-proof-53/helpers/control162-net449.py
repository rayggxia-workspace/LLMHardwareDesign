import subprocess,shlex
q="""from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');r=b/'r256-composition-359'
g=json.loads((r/'topology/boundary-graph.json').read_text());print('net7453_connection',json.dumps(g['connections']['7453']))
for key in ['nets','connections']:
 obj=g.get(key)
 if isinstance(obj,dict)and 'net_7453'in obj:print('net7453',json.dumps(obj['net_7453'])[:1500])
 if isinstance(obj,list):
  for row in obj:
   if isinstance(row,dict)and row.get('name')=='net_7453':print('net7453',json.dumps(row)[:1500])
for seed in [4010,4300,4340,4390]:
 p=r/'upper-candidates'/str(seed)/'route/router-input.txt'
 lines=p.read_text().splitlines();print(seed,'header',lines[0]);print('7453',[x for x in lines[1:]if x.startswith('net_7453 ')])
"""
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
