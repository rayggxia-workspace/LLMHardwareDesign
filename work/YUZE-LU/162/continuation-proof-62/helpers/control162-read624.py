import subprocess,shlex
code=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
for seed,folder in [(6140,'dynamic-05/node4'),(6141,'dynamic-04/node25')]:
 out=b/'r256-composition-453/upper-candidates'/str(seed)/'route';q=b/folder;state=json.loads((q/'queue-state.json').read_text());print(seed,'inputs',len(list(out.glob('trial-*/input.txt'))),'active',state['active'])
 for p in q.glob('*614*log'):
  with p.open('rb')as f:f.seek(0,2);f.seek(max(0,f.tell()-800));print(p.name,f.read().decode(errors='replace'))
 for p in out.glob('receipt.json'):print(p.read_text()[:1000])
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],universal_newlines=True))
