import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');q=b/'dynamic-07/node7';d=json.loads((q/'queue-state.json').read_text());print(json.dumps(dict(time=d['time'],active=d['active'],relevant_finished={k:v for k,v in d['finished'].items()if 'sready718'in k},memory_admissions=d['memory_admissions'])))
p=b/'r256-phase-trace-regression-718'
if p.exists():
 print('reg file count',sum(1 for x in p.rglob('*')if x.is_file()))
 for f in p.glob('*.json'):
  if f.stat().st_size<4000:print(f.name,f.read_text())
for f in q.rglob('*718*'):
 if f.is_file()and f.suffix in ('.log','.stdout','.stderr'):
  with f.open('rb')as h:h.seek(0,2);h.seek(max(0,h.tell()-2500));print(str(f),h.read().decode(errors='replace'))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
