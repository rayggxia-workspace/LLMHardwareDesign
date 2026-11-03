import subprocess,shlex
code=r'''from pathlib import Path
import json,statistics
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
for folder,seed in [('dynamic-05/node4',3732),('dynamic-04/node25',4011)]:
 q=b/folder;state=json.loads((q/'queue-state.json').read_text())
 for name in state['active']:
  spec=json.loads((q/'pending'/(name+'.json')).read_text());a=spec['args']
  if '--seed'not in a or a[a.index('--seed')+1]!=str(seed):continue
  out=Path(a[a.index('--out')+1]);rounds={};progress=[]
  for p in out.glob('trial-*/router.log'):
   last={}
   for line in p.read_text().splitlines():
    if not line.startswith('{'):continue
    d=json.loads(line)
    if 'conflict_nodes'in d:rounds.setdefault(d['round'],[]).append(d['excess_occupancy'])
    if 'routed'in d:last=d
   if last:progress.append((last['round'],last['routed']))
  print(json.dumps(dict(folder=folder,name=name,source=spec['source_root'],graph=a[a.index('--graph')+1],trial_count=a[a.index('--route-trials')+1],rounds={k:dict(trials=len(v),excess=statistics.mean(v))for k,v in rounds.items()},progress=[min(progress),max(progress)]if progress else[])))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],universal_newlines=True))
