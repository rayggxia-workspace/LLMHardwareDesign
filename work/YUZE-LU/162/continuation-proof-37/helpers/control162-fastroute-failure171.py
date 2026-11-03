import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');p=b/'dynamic-05/node4/00-j-sready171-fastroute24um-probe.log'
print(p.read_text()[-5500:])
f=b/'router-fastroute24-preflight-171/case-2/drc.rpt';print('drc_bytes',f.stat().st_size)
f=b/'router-fastroute24-preflight-171/probe-progress.json';print(f.read_text())
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
