import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');q=b/'dynamic-02/node6';d=json.loads((q/'queue-state.json').read_text())
for n in d['active']:
 spec=json.loads((q/'pending'/(n+'.json')).read_text());a=spec['args'];row=dict(task=n,source=spec['source_root'])
 if '--graph'in a:
  p=Path(a[a.index('--graph')+1]);g=json.loads(p.read_text());row.update(instances=len(g['instances']),has_R='macro_r'in g['instances'])
 print(json.dumps(row))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
