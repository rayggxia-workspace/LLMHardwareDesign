import subprocess,shlex
q=r'''from pathlib import Path
import json,statistics,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453/upper-candidates'
for seed in [4760,4850,5010,5120,5190,5191,5192,5260,5400,5450,5451]:
 rounds={};progress=[];failed=[]
 for p in(root/str(seed)/'route').glob('trial-*/router.log'):
  lines=p.read_text().splitlines();events=[]
  for line in lines:
   if line.startswith('{'):
    d=json.loads(line);events.append(d)
    if 'conflict_nodes'in d:rounds.setdefault(d['round'],[]).append(d)
  if events:progress.append(events[-1])
  if lines and not lines[-1].startswith('{'):failed.append(lines[-1])
 last=max(rounds)if rounds else None;rs=rounds.get(last,[]);print(seed,'last_complete_round_cohort',last,'trials',len(rs),'mean_excess',statistics.mean(x['excess_occupancy']for x in rs)if rs else None,'progress',progress[:2],'failed',dict(collections.Counter(failed)))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
