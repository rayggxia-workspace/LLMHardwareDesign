"""Read actual iteration violation tables and CUGR statistics."""
import subprocess,shlex
q=r'''from pathlib import Path
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/s-ready-composition-01/1391/upper-candidates')
for seed in [1513,1514,1515]:
 p=b/str(seed)/'route/openroad-search/case-0/openroad.log'
 if not p.exists():continue
 lines=p.read_text().splitlines();print('SCENE',seed)
 for i,s in enumerate(lines):
  if 'Total congestion:'in s or s.startswith('Total ')and('  'in s):print(s)
  if 'Number of violations ='in s:print('\n'.join(lines[i:i+10]))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
