import subprocess,shlex,json,time
from pathlib import Path
q="""from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');rows=[]
for folder in ['dynamic-08/node6','dynamic-03/node5']:
 queue=b/folder;state=json.loads((queue/'queue-state.json').read_text());active=[]
 for name in state['active']:
  p=queue/'pending'/(name+'.json');s=json.loads(p.read_text());a=s['args'];d=dict(name=name,script=s['script'])
  if any(str(seed)in name for seed in [9060,9061,9062,9063]):
   f=queue/(name+'.log');d['tail']=f.read_text()[-1600:]if f.exists()else None;c=queue/'commands'/(name+'.json');d['command']=json.loads(c.read_text())if c.exists()else None
  active.append(d)
 rows.append(dict(folder=folder,active=active,pending_new=[n for n in state.get('pending',[])if 'sready902'in n],finished_new={k:v for k,v in state['finished'].items()if 'sready902'in k}))
print(json.dumps(dict(time=time.time(),rows=rows)))
"""
raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]);out=Path(__file__).parent/'control162-admission919';out.mkdir(exist_ok=True);(out/(str(time.time_ns())+'.json')).write_bytes(raw);d=json.loads(raw)
for row in d['rows']:
 for a in row['active']:
  if 'command'in a:a['command']=dict(admission=a['command'].get('admission'),pid=a['command'].get('pid'))
print(json.dumps(d))
