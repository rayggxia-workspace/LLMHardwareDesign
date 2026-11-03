import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
for folder in ['dynamic-05/node2','dynamic-02/node3','dynamic-05/node4','dynamic-04/node25','dynamic-07/node7']:
 d=json.loads((b/folder/'queue-state.json').read_text());print(folder,'slots',d['slots'],'active',d['active'])
'''
compile(q,'cprogress284','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
