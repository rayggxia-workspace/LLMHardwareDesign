import subprocess,shlex
q=r'''from pathlib import Path
import json,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');r=b/'r256-composition-359'
for seed in [3730,3731,3732,3733,3734,3840,3841,3890,3891,3930,3931,4010,4011]:
 p=r/'upper-candidates'/str(seed)/'route';logs=list(p.glob('trial-*/router.log'));rounds=[];failed=collections.Counter();progress=[]
 for f in logs:
  lines=f.read_text().splitlines();rows=[json.loads(x)for x in lines if x.startswith('{')]
  completed=[x for x in rows if'conflict_nodes'in x]
  if completed:rounds.append(completed[-1])
  if rows and'routed'in rows[-1]:progress.append(rows[-1]['routed'])
  if lines and not lines[-1].startswith('{'):failed[lines[-1]]+=1
 print(json.dumps(dict(seed=seed,trials=len(logs),failed_trials=sum(failed.values()),failure_examples=dict(list(failed.items())[:2]),completed_round_trials=len(rounds),minimum_conflicts=min((v['conflict_nodes']for v in rounds),default=None),maximum_round=max((v['round']for v in rounds),default=None),route_progress_range=[min(progress),max(progress)]if progress else None)))
'''
print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=35).decode())
