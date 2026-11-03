from pathlib import Path
import subprocess,shlex
code=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-zero-pattern-regression-589'
for p in [out/'receipt.json',out/'directional-regression.json']:
 if p.exists():
  d=json.loads(p.read_text());print(p.name, json.dumps({k:v for k,v in d.items() if k in ['passed','stage','error','exception','traceback']}))
print('files',len(list(out.rglob('*'))) if out.exists() else 0)
q=b/'dynamic-07/node7';state=json.loads((q/'queue-state.json').read_text());print('active',state['active'])
for p in q.glob('*589*'):
 if p.is_file() and p.suffix=='.log':
  with p.open('rb')as f:f.seek(0,2);f.seek(max(0,f.tell()-3500));print(p.name,f.read().decode(errors='replace'))
for p in sorted(out.rglob('*.log'),key=lambda p:p.stat().st_mtime)[-3:]:
 if p.stat().st_size:
  with p.open('rb')as f:f.seek(0,2);f.seek(max(0,f.tell()-200));print(str(p.relative_to(out)),f.read().decode(errors='replace')[-200:])
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],universal_newlines=True))
