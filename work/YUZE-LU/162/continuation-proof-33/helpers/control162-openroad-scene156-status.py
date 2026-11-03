"""Read mature-router candidate and exact queued memory decision, no mutations."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');queue=b/'dynamic-05/node2';d=json.loads((queue/'queue-state.json').read_text());print('active',d['active'])
for r in d['memory_admissions']:
 if 'sready156openroad'in r['name']:print('memory',json.dumps(r))
p=b/'s-ready-composition-01/1391/upper-candidates/1513'
for stage in ['route','geometry','pg-audit','timing/low','timing/base','timing/high','delivery']:
 r=p/stage/'receipt.json'
 if r.exists():print(stage,json.loads(r.read_text()).get('passed'))
for f in [p/'route/openroad-search/case-0/openroad.log',queue/'00-k-sready156openroad-route-1513.log']:
 if f.exists():print(str(f),f.stat().st_size,'age',round(time.time()-f.stat().st_mtime),f.read_text()[-3500:])
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
