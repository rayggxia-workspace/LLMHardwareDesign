import subprocess,shlex
q=r'''from pathlib import Path
import json,statistics
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-453/upper-candidates')
for seed in [4760,4850,5010,5400,5450,5451,5550,5551]:
 rows=[]
 for p in(b/str(seed)/'route').glob('trial-*/router.log'):
  for line in p.read_text().splitlines():
   if line.startswith('{'):
    d=json.loads(line)
    if d.get('round')==0 and'conflict_nodes'in d:rows.append(d);break
 print(seed,'completed_first_round',len(rows),'mean_excess',statistics.mean(x['excess_occupancy']for x in rows)if rows else None,'mean_conflict_nodes',statistics.mean(x['conflict_nodes']for x in rows)if rows else None)
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-359/upper-candidates')
for seed in [3750,3751]:
 p=b/str(seed)/'route/openroad-search/case-0/openroad.log'
 with p.open('rb')as f:f.seek(max(0,p.stat().st_size-1800));tail=f.read().decode(errors='replace')
 print('CUGR',seed,'bytes',p.stat().st_size,'tail',tail)
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
