from pathlib import Path
import subprocess,shlex
p=Path(__file__).with_name('control162-queue555-remote.py');remote='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/queue555.py';subprocess.run(['scp',str(p),'yuzelu@10.129.166.172:'+remote],check=True);print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 '+shlex.quote(remote)],universal_newlines=True))
