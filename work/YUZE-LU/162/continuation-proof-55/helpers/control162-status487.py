import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453/function'
print('function_files',[(p.name,p.stat().st_size,int(time.time()-p.stat().st_mtime))for p in root.glob('initial*')])
for p in root.glob('initial*'):
 if p.stat().st_size<2000:print(p.name,p.read_text())
p=b/'r256-search-phase-profile-484/receipt.json'
if p.exists():
 d=json.loads(p.read_text());print('profile_receipt',{k:d.get(k)for k in ['passed','stage','error','instrumentation_removal_exact']},'trials',len(d.get('trials',[])))
p=b/'r256-search-phase-profile-484/compile.log'
if p.exists():print('profile_compile_tail',p.read_text()[-1600:])
for d in ['dynamic-05/node4','dynamic-04/node25']:
 state=json.loads((b/d/'queue-state.json').read_text());print(d,state['active'])
for seed in [4660,4661,4670,4760,4850]:
 rounds={};progress=[];fails=[]
 for p in(b/'r256-composition-453/upper-candidates'/str(seed)/'route').glob('trial-*/router.log'):
  with p.open('rb')as f:f.seek(max(0,p.stat().st_size-2500));lines=f.read().decode(errors='replace').splitlines()
  events=[]
  for line in lines:
   try:events.append(json.loads(line))
   except ValueError:pass
  if events:
   event=events[-1];progress.append({k:v for k,v in event.items()if k in ['round','routed','conflict_nodes','excess_occupancy','adaptive_search_weight']})
  if lines and not lines[-1].startswith('{'):fails.append(lines[-1])
 print(seed,'trials',len(progress),'last',progress[:3],'failures',fails[:3])
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
