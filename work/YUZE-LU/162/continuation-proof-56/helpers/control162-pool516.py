import subprocess,shlex
q=r'''from pathlib import Path
import json,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');rows=[]
for folder in ['dynamic-05/node2','dynamic-02/node3','dynamic-05/node4','dynamic-03/node5','dynamic-02/node6','dynamic-04/node25','dynamic-07/node7']:
 q=b/folder;state=json.loads((q/'queue-state.json').read_text())
 for n in state['active']:
  spec=json.loads((q/'pending'/(n+'.json')).read_text());a=spec['args']
  if spec['script']!='system_upper.py'or '--seed'not in a:continue
  out=Path(a[a.index('--out')+1]);logs=list(out.glob('trial-*/router.log'));fail=[]
  for p in logs:
   with p.open('rb')as f:f.seek(0,2);end=f.tell();f.seek(max(0,end-300));lines=f.read(300).decode(errors='replace').splitlines()
   if lines and not lines[-1].startswith('{'):fail.append(lines[-1])
  if fail:rows.append(dict(node=folder,seed=a[a.index('--seed')+1],source=Path(spec['source_root']).name,attempt_logs=len(logs),observed_failed=len(fail),errors=dict(collections.Counter(fail)),dynamic_pool='--route-trial-attempts'in a))
print(json.dumps(rows))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
