import subprocess,shlex
q='''import json,hashlib
from pathlib import Path
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/source-972')
m=json.loads((b/'source-manifest.json').read_text());f=json.loads((b/'freeze-import.json').read_text())
assert m['commit']=='7620434e568dfba16a7229642ffa8cd8b85f7132'and len(m['files'])==1010
assert f['archive_sha256']=='dbee549d02c668de6c6a1c6f4ac33227af8f67dddfe8bb1ef51ad542e70fd093'
assert all(hashlib.sha256((b/p).read_bytes()).hexdigest()==v for p,v in m['files'].items())
print('source972 manifest1010/freeze verified')
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
