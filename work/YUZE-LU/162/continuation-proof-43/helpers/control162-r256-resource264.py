import subprocess,shlex
q=r'''from pathlib import Path
import json,subprocess,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
for p in [b/'r256-fixed-pg-272/wrapper/complete-checker/receipt.json',b/'r256-fixed-pg-272/wrapper/complete-checker/native-complete/receipt.json']:
 if p.exists():
  d=json.loads(p.read_text());print(str(p.relative_to(b)),{k:v for k,v in d.items()if k in ['passed','all_artifacts','whole_die_native_drc_zero','positive_controls_passed','checks','native_report']})
g=json.loads((b/'r256-composition-259/topology/boundary-graph.json').read_text());print('R256 actual graph',dict(instances=len(g['instances']),nets=len(g['connections']),links=len(g['boundary_links']['links']),types=len(set(g['instances'].values()))))
print(subprocess.check_output(['squeue','-j','95341,95391,95098,95155,95101,95204,96297,96222','-o','%.12i %.12j %.10T %.10M %.8C %.14R'],universal_newlines=True))
p=b/'dynamic-07/node7/queue-state.json';s=json.loads(p.read_text());print('own_node7',dict(active=s['active'],age_sec=time.time()-s['time'],admissions=s.get('memory_admissions',[])[-4:]))
'''
compile(q,'resources264','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
