import subprocess,shlex
code=r'''from pathlib import Path
import json,subprocess
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');q=b/'dynamic-06/node26';s=json.loads((q/'queue-state.json').read_text());print('state',json.dumps({k:v for k,v in s.items()if k in ['job','slots','cpus_per_slot','active','memory_admissions']}));print(subprocess.check_output(['scontrol','show','job','96222','-o'],universal_newlines=True))
for n in s['active']:
 p=q/'commands'/(n+'.json');d=json.loads(p.read_text());print('admission',n,json.dumps(d['admission']))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],universal_newlines=True))
