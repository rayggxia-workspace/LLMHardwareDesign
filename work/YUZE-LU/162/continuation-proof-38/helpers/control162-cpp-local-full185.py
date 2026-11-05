"""Queue exact C++ kernel on the new measured/local-density placement, full gates."""
from pathlib import Path
import subprocess,shlex

p=Path(r'D:\Data\电路实验\control162-fastroute-full177.py');scope={}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output',1)[0],str(p),'exec'),scope);q=scope['q']
for a,b in [('s-ready-fastroute24phase-source172.json','s-ready-cpp-localdensity-source172.json'),('options=[(1770,4,1,valid[1702])]','options=[(1850,2,1,valid[1702])]'),('assert node==4','assert node==2'),("('dynamic-05/node4')","('dynamic-05/node2')"),('for node,job in [(4,95391)]','for node,job in [(2,95341)]'),('sready177fast-','sready185cpp-'),("'--route-trials',1,'--router','openroad','--openroad-congestion-iterations',50,'--openroad-global-router','fastroute','--openroad-guide-pitch-um',1.6","'--route-trials',16"),("assert len(state['active'])<=3","assert len(state['active'])<=4")]:
    assert a in q,a;q=q.replace(a,b)
start=q.index("regression=b/'router-fastroute24phase-preflight-172/receipt.json'")
end=q.index("for name in ['system_geometry.py'",start)
q=q[:start]+'''regression=b/'router-segment-regression-01/receipt.json'
reg=json.loads(regression.read_text());assert reg['passed']and reg['stage']=='route-search-regression-only'and not reg['whole_system_qualified']
report=regression.parent/'router-search-regression.json';assert reg['outputs'][report.name]==sha(report)
for name in ['tree_router.cpp','tree_router_cpp.py','router_regression.py']:
 old=b/'source-145/project/experiments/control_v1'/name;current=source/'project/experiments/control_v1'/name;assert reg['inputs'][str(old)]==sha(old)==sha(current)
'''+q[end:]
old='One actual235-instance/8990-net FastRoute candidate1770 on original1702 measured-budget/local-density placement, after actual172 three fixture detailed routes and original phase/grid/checkerboard/flood/9 negative checks pass. Earlier170 coarse global overflow and171 off-grid failures retained; no waiver/remapping/allow_congestion. Only search guides change:24um guide tiles and exact original190/140DBU phase, real M11/M12 tracks4um and all final geometry/PG/RC300MHz gates unchanged.'
assert old in q
q=q.replace(old,'Actual235-instance/8990-net C++ negotiated router1850 with16 independent single-thread trials inside one16CPU slot, reuses exactly the same native-ground/minimum-pin-bound-cleared1702 placement as1770 FastRoute. Unlike preferred-direction global routers the original checked grid kernel supports both Manhattan directions on each original layer. Exact source145 successful regression kernel/reader SHA reused, all original583 weak-source wire budgets and all seven full geometry/PG/three-RC300MHz/delivery gates remain mandatory. Waits for an existing node2 slot after181 diagnostic, no job cancellation/new node/R changes. Local-density placement is a new search input, never qualification.')
compile(q,'actual_cpp_local_density_full1850','exec')
if __name__=='__main__':
    print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
