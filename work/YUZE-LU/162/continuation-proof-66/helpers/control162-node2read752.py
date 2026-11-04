import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');q=b/'dynamic-05/node2';s=json.loads((q/'queue-state.json').read_text());print(json.dumps(dict(time=s['time'],active=s['active'],memory=s['memory_admissions'],relevant_finished={k:v for k,v in s['finished'].items()if 'sready736'in k})))
f=q/'00-g-sready736-r256-route-7371.log'
if f.exists():
 with f.open('rb')as h:h.seek(0,2);h.seek(max(0,h.tell()-2000));print(h.read().decode(errors='replace'))
p=b/'r256-composition-453/upper-candidates/7371/route';print('output files', [f.name for f in p.iterdir()]if p.exists()else'not created')
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
