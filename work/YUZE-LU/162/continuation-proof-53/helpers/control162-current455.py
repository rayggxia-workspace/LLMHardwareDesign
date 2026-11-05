import subprocess,shlex,json
q="""from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');r=b/'r256-composition-453'
for stage in ['contract','topology','native-sta','cap-initial','function','native-residual','native-pin-load']:
 p=r/stage/'receipt.json'
 if p.exists():
  d=json.loads(p.read_text());print(stage,json.dumps({k:d[k]for k in ['passed','execution_passed','stage','error','exception','real_program_count']if k in d}))
 else:print(stage,'pending')
for folder in ['dynamic-05/node2','dynamic-04/node25']:
 q=b/folder;s=json.loads((q/'queue-state.json').read_text());print(folder,'active',s['active'])
 for p in q.glob('*sready453*.log'):
  with p.open('rb')as h:h.seek(max(0,p.stat().st_size-600));tail=h.read().decode(errors='replace')
  print(p.name,tail[-600:])
for folder in ['native-sta','function']:
 d=r/folder
 if folder=='native-sta':print('native_files',[(p.name,p.stat().st_size)for p in d.iterdir()if p.is_file()][:15])
 for p in d.glob('*.log'):
  with p.open('rb')as h:h.seek(max(0,p.stat().st_size-350));tail=h.read().decode(errors='replace')
  print(folder,p.name,p.stat().st_size,tail[-350:])
"""
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
