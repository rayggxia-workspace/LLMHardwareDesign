import subprocess,shlex
q=r'''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-search-phase-profile-494';print('out_exists',root.exists())
for p in [root/'receipt.json',root/'profile/receipt.json']:
 if p.exists():
  d=json.loads(p.read_text());print(str(p),{k:d.get(k)for k in ['passed','stage','instrumentation_removal_exact','error']},'trials',len(d.get('trials',[])))
p=root/'profile/compile.log'
if p.exists():print('compile_tail',p.read_text()[-1000:])
for p in list((root/'profile').glob('trial-*/profile.log'))[:2]:
 with p.open('rb')as f:f.seek(max(0,p.stat().st_size-300));print(p.name,p.parent.name,f.read().decode(errors='replace'))
p=b/'dynamic-02/node6/00-f-sready494-supported-search-profile.log'
if p.exists():print('launcher_tail',p.read_text()[-2000:])
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
