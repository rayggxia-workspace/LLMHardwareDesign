from pathlib import Path
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';source=b/'source-510';record=b/'route-selection-102/sready511-separate-ordinary-cost';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
assert json.loads((b/'r256-padding-final-function-audit-472/receipt.json').read_text())['passed'];assert json.loads((b/'r256-search-phase-analysis-498/receipt.json').read_text())['passed']
def put(name,spec):
 p=b/'dynamic-02/node6/pending'/(name+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
reg=b/'r256-ordinary-cost-regression-511'
put('00-f-sready511-separate-ordinary-cost-regression',dict(script='system_upper.py',source_root=str(source),forecast_gib=16,requires=[],args=['--manifest',str(b/'r256-composition-359/selected/physical.json'),'--graph',str(root/'topology/boundary-graph.json'),'--directional-regression-only','--route-regression-baseline',str(b/'source-474/project/experiments/control_v1/tree_router.cpp'),'--out',str(reg)]))
template=[x for x in json.loads((b/'route-selection-102/sready484-search-phase-profile/tasks.json').read_text())['tasks']if '-4850'in Path(x['path']).stem];assert len(template)==7
config=root/'acceptance-5120.json';assert not config.exists();config.write_text((root/'acceptance-4850.json').read_text().replace('/upper-candidates/4850/','/upper-candidates/5120/'))
for old in template:
 spec=json.loads(json.dumps(old['spec']));spec['source_root']=str(source)
 for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/4850/','/upper-candidates/5120/').replace('acceptance-4850.json','acceptance-5120.json')for x in spec[key]]
 if spec['script']=='system_upper.py':
  a=spec['args'];assert a[a.index('--seed')+1]=='4661'and a[a.index('--route-heuristic-weight')+1]=='256'and a[a.index('--route-congestion-scale')+1]=='1';a+=['--route-ordinary-congestion-scale','64'];spec['requires']+=[str(reg/'receipt.json')]
 put(Path(old['path']).stem.replace('sready485','sready512').replace('4850','5120'),spec)
gates={}
for name in ['system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py','resource_search.h']:
 p=source/'project/experiments/control_v1'/name;assert sha(p)==sha(b/'source-474/project/experiments/control_v1'/name);gates[name]=sha(p)
old=(b/'source-474/project/experiments/control_v1/tree_router.cpp').read_text();new=(source/'project/experiments/control_v1/tree_router.cpp').read_text();start='    if(pareto_wire_budget&&n<locked_count&&wire_limits[n]>=0){';end='    }else if(bidirectional_two_terminal';assert old.split(start,1)[1].split(end,1)[0]==new.split(start,1)[1].split(end,1)[0]
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,unchanged_final_gate_and_resource_source_sha256=gates,finite_resource_branch_byte_identical=True,whole_system_qualified=False,scope='Test actual494 S-bus/PG ordinary-search cost hypothesis after real453 programs passed. Keep finite native-output search scale1 and every physical wire budget, override only ordinary n>=locked_count congestion scale64. Default0 must replay474 route/log bytes; three real mixed cases prove actual ordinary cost steps with finite scale1 plus6rejects, all existing cases/oracles retained. Full5120 same placement4610/RNG4661/cost2/weight256/adaptive/critical-first/8million labels/64attempts16active as4850; only optional ordinary cost64 differs. All original7 final geometry/PG/threeRC300MHz/current453function/joint gates and resource search code unchanged. Queue/preflight/search are not convergence, speed or physical qualification. Own node6 slot replaces one exact older-source359 search after identity guards; original evidence preserved, no foreign task or parent cancellation.'),indent=2));print(json.dumps(dict(queued=len(rows),candidate=5120)))
'''
compile(q,'queue511','exec');Path(__file__).with_name('control162-queue511-remote.py').write_bytes(q.encode());print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
