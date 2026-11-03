import subprocess,shlex
q="from pathlib import Path;import json;b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-453');print((b/'acceptance-5400.json').read_text());print((b.parent/'r256-final-chain-binding-audit-579/receipt.json').read_text())"
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
