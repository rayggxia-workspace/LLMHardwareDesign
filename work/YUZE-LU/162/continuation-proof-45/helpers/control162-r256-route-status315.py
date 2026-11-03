import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
import time
root=b/'r256-composition-274/upper-candidates'
for seed in [2670,2671,2672,2950,2951,3140,3141,3142]:
 p=root/str(seed)/'route';r=p/'receipt.json';d=json.loads(r.read_text())if r.exists()else{};logs=list(p.glob('trial-*/router.log'));completed=[];progress=[]
 for log in logs:
  rows=[json.loads(line)for line in log.read_text().splitlines()if line.startswith('{')]
  completed +=[x['conflict_nodes']for x in rows if 'conflict_nodes'in x]
  if rows:progress.append({k:v for k,v in rows[-1].items()if k in ['round','routed','adaptive_search_weight']})
 print(seed,'receipt',d.get('passed'),'trials',len(logs),'best_completed_conflicts',min(completed)if completed else None,'progress',progress[:2])
 if not logs:
  files=sorted(p.glob('*.log'),key=lambda x:x.stat().st_mtime);print('startup',[(x.name,round(time.time()-x.stat().st_mtime,1))for x in files[-1:]])
 f=p/'openroad-search/case-0/openroad.log'
 if f.exists():print('openroad',f.read_text().splitlines()[-2:])
'''
compile(q,'cprogress284','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
