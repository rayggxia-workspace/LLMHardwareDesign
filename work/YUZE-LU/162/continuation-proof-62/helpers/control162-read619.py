import subprocess,shlex
code=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-pattern-weight-regression-614'
for p in [out/'receipt.json',out/'weight-cases/receipt.json']:
 if p.exists():
  d=json.loads(p.read_text());print(p.name,json.dumps({k:v for k,v in d.items()if k in ['passed','error','traceback','stage']}));print('cases',len(d.get('cases',[])))
q=b/'dynamic-05/node4';print('active',json.loads((q/'queue-state.json').read_text())['active']);p=q/'00-f-sready614-pattern-weight-regression.log'
if p.exists():
 with p.open('rb')as f:f.seek(0,2);f.seek(max(0,f.tell()-1800));print('task-log',f.read().decode(errors='replace'))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],universal_newlines=True))
