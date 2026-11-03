import subprocess,shlex
q=r'''from pathlib import Path
import json,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');q=b/'dynamic-04/node25';d=json.loads((q/'queue-state.json').read_text())
for n in d['active']:
 spec=json.loads((q/'pending'/(n+'.json')).read_text());a=spec['args']
 if '--seed'not in a or a[a.index('--seed')+1]!='4011':continue
 print('source',spec['source_root']);out=Path(a[a.index('--out')+1]);errors=[]
 for p in out.glob('trial-*/router.log'):
  lines=p.read_text().splitlines()
  if lines and not lines[-1].startswith('{'):errors.append(lines[-1])
 print('failures',len(errors),dict(collections.Counter(errors)))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
