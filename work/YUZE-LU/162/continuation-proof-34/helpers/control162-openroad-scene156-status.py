"""Read mature-router candidate and exact queued memory decision, no mutations."""
import subprocess,shlex,sys
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');queue=b/'dynamic-05/node2';d=json.loads((queue/'queue-state.json').read_text());print('active',d['active'])
cmd=queue/'commands/00-k-sready156openroad-route-1513.json'
if cmd.exists():print('memory',json.dumps(json.loads(cmd.read_text())['admission']))
p=b/'s-ready-composition-01/1391/upper-candidates/1513'
for stage in ['route','geometry','pg-audit','timing/low','timing/base','timing/high','delivery']:
 r=p/stage/'receipt.json'
 if r.exists():print(stage,json.loads(r.read_text()).get('passed'))
for f in [p/'route/openroad-search/case-0/openroad.log',queue/'00-k-sready156openroad-route-1513.log']:
 if f.exists():
  lines=f.read_text().splitlines();selected=[s for s in lines if any(k in s for k in ['Number of violations','Completing','optimization iteration','ERROR','Runtime:','Total wire length ='])]
  print(str(f),f.stat().st_size,'age',round(time.time()-f.stat().st_mtime),'\n'.join(selected[-10:]or lines[-6:]))
'''
if len(sys.argv)>1:
 assert sys.argv[1]in ['1514','1515'];q=q.replace('1513',sys.argv[1]).replace('node2','node4')
 if sys.argv[1]=='1515':q=q.replace('sready156openroad','sready157openroad')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
