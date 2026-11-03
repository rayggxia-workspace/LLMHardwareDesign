import subprocess,shlex
q="""from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');s=json.loads((b/'dynamic-05/node4/queue-state.json').read_text())
for name in s['active']:
 p=b/'dynamic-05/node4/pending'/(name+'.json');d=json.loads(p.read_text());a=d['args']
 if '--seed'in a and a[a.index('--seed')+1]=='1840':
  out=Path(a[a.index('--out')+1]);print(out);print([(str(p.relative_to(out)),p.stat().st_size)for p in out.rglob('*.log')if 'pg-access-'not in p.name][:12])
"""
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
