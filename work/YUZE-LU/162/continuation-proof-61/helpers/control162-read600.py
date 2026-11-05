import subprocess,shlex
code=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-453/upper-candidates')
for n in [5640,5890]:
 p=b/str(n)/'route/trial-0/input.txt'
 with p.open()as f:print(n,'header',f.readline().strip())
 p=p.with_name('router.log')
 with p.open('rb')as f:
  print('begin',f.read(600).decode(errors='replace'));f.seek(0,2);f.seek(max(0,f.tell()-600));print('tail',f.read().decode(errors='replace'))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],universal_newlines=True))
