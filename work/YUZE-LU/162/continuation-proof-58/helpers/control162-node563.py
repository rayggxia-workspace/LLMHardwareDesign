import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');q=b/'dynamic-07/node7';state=json.loads((q/'queue-state.json').read_text())
for n in state['active']:
 s=json.loads((q/'pending'/(n+'.json')).read_text());a=s['args'];print(n,'source',Path(s['source_root']).name,'args',a)
 p=q/(n+'.log')
 if p.exists():
  with p.open('rb')as f:f.seek(max(0,p.stat().st_size-800));print('tail',f.read().decode(errors='replace'))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
