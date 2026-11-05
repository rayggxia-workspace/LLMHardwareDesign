"""Three source213 full graph schedules, each with all original seven gates."""
from pathlib import Path
import subprocess,shlex
home=Path(r'D:\Data\电路实验');s=(home/'control162-cpp-local-full185.py').read_text(encoding='utf-8').split("if __name__=='__main__':",1)[0]
scope={};exec(compile(s,'source185helper','exec'),scope);q=scope['q']
pairs=[("source=b/'source-172'","source=b/'source-213'"),("source='source-172'","source='source-213'"),
 ('s-ready-cpp-localdensity-source172.json','s-ready-initial-order-source213.json'),
 ('options=[(1850,2,1,valid[1702])]','options=[(2150,25,1,valid[1702]),(2151,25,1,valid[1702]),(2152,25,1,valid[1702])]'),
 ('for node,job in [(2,95341)]','for node,job in [(25,95204)]'),
 ("b/'dynamic-05'/('node'+str(node))","b/'dynamic-04'/('node'+str(node))"),
 ("assert len(state['active'])<=4","assert len(state['active'])<=6"),('assert node==2','assert node==25'),
 ("('dynamic-05/node2')","('dynamic-04/node25')"),('sready185cpp-','sready215order-'),
 ("'--route-trials',16","'--route-trials',16,'--route-initial-order',seed-2149")]
for a,b in pairs:
 assert a in q,a;q=q.replace(a,b)
start=q.index("regression=b/'router-segment-regression-01/receipt.json'");end=q.index("for name in ['system_geometry.py'",start)
q=q[:start]+'''regression=b/'router-initial-order-regression-214/receipt.json'
reg=json.loads(regression.read_text());assert reg['passed']and reg['stage']=='route-search-regression-only'and not reg['whole_system_qualified']
report=regression.parent/'router-search-regression.json';assert reg['outputs'][report.name]==sha(report)
proof=json.loads(report.read_text());assert proof['passed']and len(proof['initial_order_cases'])==9
assert len(proof['default_previous_source_byte_replay'])==3 and proof['initial_order_impossible_wire_budget_rejected']==[1,2,3]
for name in ['tree_router.cpp','tree_router_cpp.py','router_regression.py']:
 current=source/'project/experiments/control_v1'/name;assert reg['inputs'][str(current)]==sha(current)
old=b/'source-211/project/experiments/control_v1/tree_router.cpp';assert reg['inputs'][str(old)]==sha(old)==sha(b/'source-172/project/experiments/control_v1/tree_router.cpp')
'''+q[end:]
start=q.index("scope='")+len('scope=');end=q.index("'",start+1)
q=q[:start]+repr('Actual235-instance/8990-net source213 searches with initial geometry-span ascending, descending, and fanout descending schedules, each16 independent1thread seeds within an existing16CPU queue slot. Same actual1702 placement, original583 physical wire budgets, all8 original geometry/PG/RC acceptors SHA unchanged. Actual214 full old regression plus9 new ordered fixtures,3 impossible budget rejections and3 old-source route/log byte replays must pass before admission. Actual native-ground/minimum-pin low/base/high bounds and original function suite bound. All7 physical/final delivery stages required for each. Queue on existing own node25 six-slot scheduler, unchanged memory guard, no job cancellation/new nodes/R/foreign changes. No qualification inferred from diagnostics.')+q[end+1:]
compile(q,'actual_ordered_full215','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
