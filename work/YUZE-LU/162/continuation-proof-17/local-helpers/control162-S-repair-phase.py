import subprocess, shlex
q=r'''from pathlib import Path
import re
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
for seed in [1181,1182]:
 p=b/'s-internal-drive-02'/('candidate-'+str(seed))/'04-do-route.log'
 data=p.read_bytes()[:2000000].decode(errors='replace');lines=data.splitlines()
 print('candidate',seed)
 interesting=[i for i,l in enumerate(lines)if re.search(r'repair_timing|[Hh]old|[Ss]etup|WNS|TNS|Worst Slack|Worst Endpoint',l)]
 for i in interesting[-15:]:print('\n'.join(lines[max(0,i-1):i+3]))
 print('latest', '\n'.join(lines[-7:]))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
