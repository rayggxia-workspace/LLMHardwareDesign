"""Append one actual mature-router candidate plus all six unchanged full gates."""
from pathlib import Path
import subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-halo-route142.py');scope={}
exec(compile(p.read_text(encoding='utf-8').split("if '--submit' in sys.argv:",1)[0],str(p),'exec'),scope)
q=scope['q']
changes={"source=b/'source-142'":"source=b/'source-156'","source='source-142'":"source='source-156'",
 's-ready-halo-routes-source142.json':'s-ready-openroad-source156.json',
 'options=[(seed,5,4,valid[n])for seed,n in [(1480,1470),(1481,1473),(1482,1474)]if n in valid]':'options=[(1513,2,1,valid[1470])]',
 'assert node==5':'assert node==2',"('dynamic-03/node5')":"('dynamic-05/node2')",
 'sready142halo-':'sready156openroad-',
 "'--route-trials',16":"'--route-trials',1,'--router','openroad'",
 "required+[regression],route,32)":"required+[regression],route,64)"}
for old,new in changes.items():
 assert old in q,old
 q=q.replace(old,new)
start=q.index("regression=b/'router-congestion-regression-01/receipt.json'")
end=q.index('rows=[]',start)
proof=r'''regression=b/'router-openroad-preflight-156/receipt.json'
reg=json.loads(regression.read_text());assert reg['passed']and not reg['whole_system_qualified']and reg['stage']=='openroad-small-search-preflight-only'
report=regression.parent/'openroad-probe.json';assert reg['outputs'][report.name]==sha(report)
proof=json.loads(report.read_text());assert proof['passed']and proof['independent_grid_verification_passed']and len(proof['cases'])==3 and proof['parser_regression']['negative_cases']==9
for case in proof['cases']:
 assert case['returncode']==0
 folder=regression.parent/('case-'+str(case['case']))
 for name,digest in case['outputs'].items():assert sha(folder/name)==digest
 gp=json.loads((folder/'grid-proof.json').read_text());assert gp['final_conflicts']==0 and gp['independent_tree_flood']and gp['independent_cross_net_occupancy']
 assert not(folder/'drc.rpt').read_text().strip()
for name in ['openroad_router_probe.py','openroad_grid.py','system_upper.py']:
 path=source/'project/experiments/control_v1'/name;assert reg['inputs'][str(path)]==sha(path)
for name in ['system_geometry.py','system_accept.py','system_sta.py','system_pg_audit.py','system_native_audit.py','upper_rc_network.py','native_stitch.py','tree_router.py','boundary_links.py']:
 assert sha(source/'project/experiments/control_v1'/name)==sha(b/'source-140/project/experiments/control_v1'/name)
import subprocess
state=json.loads((b/'dynamic-05/node2/queue-state.json').read_text());assert len(state['active'])<=3
details=subprocess.check_output(['scontrol','show','job','95341','-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node2 'in details
required_base.append(regression)
'''
q=q[:start]+proof+q[end:]
q=q.replace('Actual externally expanded halo scenes with all native relative placements fixed; each scene requires executed native-ground plus actual minimum final-ODB input-load bounds clear at all three corners and actual selected1391 function pass. Independent real routes and six complete downstream gates per scene; actual area charged and all physical acceptance unchanged',
 'One actual235-instance/8990-net CUGR/TritonRoute candidate on existing1470 exact qualified halo placement, after three real mixed-phase/PG-like/three-sink fixtures and nine negative parser cases pass. Search-only passive markers, original margin/grid/via checks, original583 source wire budgets and all six downstream full geometry/PG/three-RC300MHz/delivery gates unchanged. 64GiB route forecast reserves memory for millions of search-only cut guards; original measured-memory admission unchanged. No new node, no qualification before complete joint acceptance, R and other tasks untouched.')
compile(q,'actual_openroad_candidate156','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
