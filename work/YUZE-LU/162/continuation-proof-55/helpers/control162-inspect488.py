import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');p=b/'dynamic-05/node4/00-f-sready484-bounded-search-phase-profile.log';print('log',p.exists())
if p.exists():print(p.read_text()[-4000:])
d=json.loads((b/'dynamic-05/node4/queue-state.json').read_text());print('keys',list(d))
for k,v in d.items():
 if k!='active'and isinstance(v,(dict,list)):
  print(k,[str(x)[:700]for x in(v.values()if isinstance(v,dict)else v)if '484'in str(x)])
print('runner',[(str(p),p.stat().st_size)for p in(b/'dynamic-05').glob('*.py')])
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
