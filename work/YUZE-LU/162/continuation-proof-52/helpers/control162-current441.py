import subprocess,shlex
q="""from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
r=b/'r256-critical-partition-regression-438/receipt.json'
print('regression',r.read_text()[:1800]if r.exists()else 'pending')
s=json.loads((b/'dynamic-02/node3/queue-state.json').read_text());print('node3_active',json.dumps(s['active']))
p=b/'dynamic-02/node3/00-f-sready438-critical-regression.log'
if p.exists():
 with p.open('rb')as h:h.seek(max(0,p.stat().st_size-1600));print('reglog',h.read().decode(errors='replace'))
for seed in [3931,4010,4081,4250,4270,4300,4340,4390]:
 p=b/'r256-composition-359/upper-candidates'/str(seed)/'route';r=p/'receipt.json';rows=[]
 for f in p.glob('trial-*/router.log'):
  with f.open('rb')as h:h.seek(max(0,f.stat().st_size-2048));tail=h.read().decode(errors='replace').splitlines()
  rr=[]
  for line in tail:
   try:
    row=json.loads(line)
    if 'conflict_nodes'in row or 'constrained_priority_prefix'in row:rr.append(row)
   except ValueError:pass
  if rr:rows.append(dict(trial=f.parent.name,last=rr[-1]))
 print(seed,'receipt',r.read_text()[:300]if r.exists()else 'none','tail',json.dumps(rows[:2]))
"""
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
