import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
for seed in [1390,1391]:
 p=b/'s-ready-qualified-01'/str(seed)/'pg-wrapper';r=p/'receipt.json';print(seed,'PG',json.loads(r.read_text()).get('passed')if r.exists()else'active')
 for name in ['full-deck.log','native-drc.log']:
  f=p/name
  if f.exists():print(name,'age',round(time.time()-f.stat().st_mtime),'tail',f.read_text().splitlines()[-3:])
for node in [2,3,4,5,6,7,25,26]:
 fam=5 if node in (2,4)else 3 if node==5 else 4 if node==25 else 2
 p=b/('dynamic-%02d'%fam)/('node'+str(node))/'queue-state.json';d=json.loads(p.read_text());reject=[r for r in d['memory_admissions']if not r['admitted']and'sready140'in r['name']];print('node',node,'own_active',d['active'],'new_memory_rejections',reject)
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
