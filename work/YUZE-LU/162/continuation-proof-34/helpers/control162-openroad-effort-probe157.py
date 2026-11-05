"""Replace one measured very slow own search with actual higher-effort probes."""
from pathlib import Path
import ast,subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-regression-launch142.py');q=ast.literal_eval(ast.parse(p.read_text()).body[1].value)
changes={"source=b/'source-142'":"source=b/'source-157'",'415069fbe00e9706eee8bfcfeec842ec4b0ac878':'fbb61e6fb3e1bb7dbff94d3189c33420fe629690',
 'sready142-independent-congestion-regression':'sready157-cugr50-probe',
 "name='00-k-sready140-route-1411'":"name='00-k-sready144product-route-1510'",
 "spec['source_root']==str(b/'source-140')":"spec['source_root']==str(b/'source-144')",
 'upper-candidates/1411/route':'upper-candidates/1510/route',
 "str(b/'source-140/project/experiments/control_v1/system_upper.py')":"str(b/'source-144/project/experiments/control_v1/system_upper.py')",
 'for seed in [1410,1411]':'for seed in [1510,1512]',
 '00-r-sready142-search-regression':'00-r-sready157-openroad-effort-probe',
 'router-congestion-regression-01':'router-openroad-effort-preflight-157',
 "'--route-regression-only'":"'--openroad-router-probe-only','--openroad-congestion-iterations',50",
 'Retire one exact own slow coupled-weight4 ordering search to admit full default-plus-new search-order regression; preserve all old evidence, other search controls, parent allocations and physical gates. Not a completed physical failure.':
 'Only individually verified own source144 product weight4 search1510, measured still first completed round after about two hours and931714 conflicts, while retained weight1 controls progress. Preserve1511/1512 product controls, all parent allocations/old specs/partial results, other tasks and R. Queue actual CUGR50 effort preflight first, then free exact child slot; no acceptance relaxation, incomplete search retirement rather than physical failure.'}
for old,new in changes.items():
 assert old in q,old
 q=q.replace(old,new)
start=q.index("subprocess.run(['scancel'");end=q.index("p=queue/'pending",start);cancel=q[start:end];q=q[:start]+q[end:]
loc=q.index(";print('Appended full search regression")
q=q[:loc]+'\n'+cancel+"print('Queued real higher-effort probe before retiring exact own slow step',targets[0]['step'])\n"
compile(q,'actual_cugr50_probe157','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
