import subprocess,shlex
q=r'''from pathlib import Path
import json,subprocess
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');q=b/'dynamic-06/node26';rows=[]
for p in(q/'pending').glob('*.json'):
 s=json.loads(p.read_text());done=(q/'results'/p.name).exists();requirements=[]
 for path in s.get('requires',[]):
  pp=Path(path)
  try:passed=json.loads(pp.read_text()).get('passed')is True
  except(OSError,ValueError):passed=False
  requirements.append(passed)
 if not done:rows.append(dict(name=p.stem,ready=all(requirements),dependency_count=len(requirements)))
print(json.dumps(dict(pending_unfinished=len(rows),ready=sum(x['ready']for x in rows),state_exists=(q/'queue-state.json').exists())))
q=b/'dynamic-03/node5';s=json.loads((q/'queue-state.json').read_text());print('node5_active',s['active'])
for name in s['active']:
 if 'sready545'in name:
  p=q/'pending'/(name+'.json');spec=json.loads(p.read_text());a=spec['args'];out=Path(a[a.index('--out')+1]);receipt=out/'route/memory-admission.json';print(name,'memory',json.loads(receipt.read_text())if receipt.exists()else'route pool receipt not yet present')
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
