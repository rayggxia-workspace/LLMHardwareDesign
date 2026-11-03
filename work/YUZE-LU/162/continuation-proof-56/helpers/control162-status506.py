import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
for folder in ['r256-bidirectional-search-regression-500','r256-ordinary-cost-regression-511','r256-padding-program-events-473','r256-padding-program-event-audit-480']:
 p=b/folder/'receipt.json'
 if p.exists():
  r=json.loads(p.read_text());print(folder,{k:r.get(k)for k in ['passed','stage','error']})
 else:print(folder,'pending')
 if 'events'in folder:print('event_files',[(p.name,p.stat().st_size)for p in(b/folder).glob('initial*')])
for folder in ['dynamic-02/node6','dynamic-04/node25']:
 d=json.loads((b/folder/'queue-state.json').read_text());print(folder,d['active'])
 for p in(b/folder).glob('*sready511*.log'):
  with p.open('rb')as f:f.seek(0,2);pos=f.tell();f.seek(max(0,pos-1200));print(p.name,f.read(1200).decode(errors='replace'))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
