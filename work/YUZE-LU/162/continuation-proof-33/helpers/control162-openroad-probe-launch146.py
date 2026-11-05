"""Queue first, then retire one individually verified own duplicate step."""
from pathlib import Path
import ast,subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-regression-launch142.py')
q=ast.literal_eval(ast.parse(p.read_text()).body[1].value)
changes={"source=b/'source-142'":"source=b/'source-146'",
 '415069fbe00e9706eee8bfcfeec842ec4b0ac878':'HEAD146',
 'sready142-independent-congestion-regression':'sready146-openroad-search-preflight',
 'dynamic-05/node4':'dynamic-05/node2','1411':'1440','1410':'1430',
 "+1]=='4'":"+1]=='1'",'95391':'95341','node4':'node2',
 'router-congestion-regression-01':'router-openroad-preflight-01',
 '00-r-sready142-search-regression':'00-r-sready146-openroad-preflight',
 '--route-regression-only':'--openroad-router-probe-only',
 'Retire one exact own slow coupled-weight4 ordering search to admit full default-plus-new search-order regression; preserve all old evidence, other search controls, parent allocations and physical gates. Not a completed physical failure.':
 'Only individually verified own duplicate source140 weight1 search1440, same placement1420 as retained1430/1442/1446. Append small exact-technology OpenROAD preflight before retiring its exact child step. Preserve all parent allocations, old specs/partial evidence, other searches/tasks and R. No acceptance change; no real OpenROAD scene before independent physical checks.'}
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo).decode().strip()
for old,new in changes.items():
 assert old in q,old
 q=q.replace(old,new)
q=q.replace('HEAD146',head)
# Queue the replacement atomically before freeing the verified child slot.
start=q.index("subprocess.run(['scancel'");end=q.index("p=queue/'pending",start)
cancel=q[start:end];q=q[:start]+q[end:]
loc=q.index(";print('Appended full search regression")
q=q[:loc]+'\n'+cancel+"print('Appended OpenROAD preflight; retired exact own duplicate',targets[0]['step'])\n"
compile(q,'openroad_probe_admission146','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
