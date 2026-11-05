import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');p=b/'r256-early-native-283';d=json.loads((p/'native-system-audit.json').read_text());
def brief(v,depth=0):
 if isinstance(v,dict):
  return {k:brief(x,depth+1)for k,x in v.items()if not isinstance(x,(dict,list))or depth<2}if len(v)<40 else {'map_count':len(v)}
 if isinstance(v,list):return {'count':len(v),'examples':v[:3]if all(isinstance(x,str)for x in v[:3])else []}
 return v
print('typed',brief(d['typed']));t=json.loads((p/'native-timing.json').read_text());print('native timing',brief(t))
p=b/'r256-fixed-pg-272/checks/timing';print('r timing',brief(json.loads((p/'receipt.json').read_text())))
print('r timing files',[x.name for x in p.iterdir()])

p=b/'router-adaptive-regression-287';print('regression receipt',json.loads((p/'receipt.json').read_text()).get('passed')if(p/'receipt.json').exists()else'unfinished');print('regression queue tail',(b/'dynamic-02/node3/00-j-sready287-adaptive-regression.log').read_text().splitlines()[-4:])
'''
compile(q,'early_audit288','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
