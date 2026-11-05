from pathlib import Path
import subprocess,shlex
h=Path(__file__).parent
check="from pathlib import Path;import json;p=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-453/function/receipt.json');print('ready'if p.exists()and json.loads(p.read_text()).get('passed')else 'pending')"
ready=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(check)],universal_newlines=True).strip()
if ready!='ready':print('453function pending; no audit/trace launched');raise SystemExit(0)
for name in ['control162-function472-remote.py','control162-queue473-remote.py']:
 q=(h/name).read_text(encoding='utf-8');print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
