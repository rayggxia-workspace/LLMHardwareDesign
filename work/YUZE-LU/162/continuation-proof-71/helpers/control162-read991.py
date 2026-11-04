import subprocess,shlex,json
q='''from pathlib import Path
import json,hashlib,subprocess
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');rows=[]
for job,folder,target in [(95341,'dynamic-05/node2',8110),(95391,'dynamic-05/node4',8111)]:
 queue=b/folder;state=json.loads((queue/'queue-state.json').read_text());forecasts=[]
 for name in state['active']:
  p=queue/'pending'/(name+'.json');raw=p.read_bytes();s=json.loads(raw);forecasts.append([name,s['forecast_gib']]);a=s['args']
  if '--out'in a and Path(a[a.index('--out')+1]).parent.name==str(target):rows.append(dict(job=job,folder=folder,path=str(p),sha256=hashlib.sha256(raw).hexdigest(),spec=s))
 print(json.dumps(dict(job=job,forecasts=forecasts)))
out=b/'r256-warm-variant-admission-991';assert not out.exists();out.mkdir();(out/'receipt.json').write_text(json.dumps(dict(rows=rows,whole_system_qualified=False),indent=2));print(json.dumps(rows))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
