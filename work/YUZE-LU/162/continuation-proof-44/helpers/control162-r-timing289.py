import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
p=b/'r256-fixed-pg-272/checks/timing'
for n in ['timing-summary.tsv','sta.log','timing.rpt']:
 rows=(p/n).read_text(errors='replace').splitlines()
 print(n,rows[-30:])
print('queue log',[(x.name,x.read_text(errors='replace').splitlines()[-8:])for x in (b/'dynamic-07/node7').glob('*timing*.log')])
'''
compile(q,'cprogress284','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
