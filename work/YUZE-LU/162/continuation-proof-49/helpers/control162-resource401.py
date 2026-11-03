import subprocess,shlex
q=r'''from pathlib import Path
import json,time,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-359';source=b/'source-400';record=b/'route-selection-102/sready401-resource-frontier';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
reg=b/'r256-resource-regression-401';spec=dict(script='system_upper.py',source_root=str(source),forecast_gib=16,requires=[str(root/'selected/receipt.json')],args=['--manifest',str(root/'selected/physical.json'),'--graph',str(root/'topology/boundary-graph.json'),'--directional-regression-only','--route-regression-baseline',str(b/'source-388/project/experiments/control_v1/tree_router.cpp'),'--out',str(reg)])
def put(queue,name,spec):
 p=b/queue/'pending'/(name+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
put('dynamic-05/node4','00-f-sready401-resource-regression',spec)
template=[r for r in json.loads((b/'route-selection-102/sready389-measured-route-budget/tasks.json').read_text())['tasks']if '-3890'in Path(r['path']).name];assert len(template)==7
for seed,cost,weight,queue in [(4010,8,16,'dynamic-05/node4'),(4011,2,4,'dynamic-04/node25')]:
 config=root/('acceptance-'+str(seed)+'.json');assert not config.exists();config.write_text((root/'acceptance-3890.json').read_text().replace('/upper-candidates/3890/','/upper-candidates/'+str(seed)+'/'))
 for row in template:
  spec=json.loads(json.dumps(row['spec']));spec['source_root']=str(source)
  for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/3890/','/upper-candidates/'+str(seed)+'/').replace('acceptance-3890.json','acceptance-'+str(seed)+'.json')for x in spec[key]]
  if spec['script']=='system_upper.py':
   a=spec['args'];a[a.index('--seed')+1]=str(seed);a[a.index('--route-nonpreferred-cost')+1]=str(cost);a[a.index('--route-heuristic-weight')+1]=str(weight);spec['requires']+=[str(reg/'receipt.json'),str(b/'r256-reset53-final-function-audit-392/receipt.json')]
  put(queue,Path(row['path']).stem.replace('sready389','sready401').replace('3890',str(seed)),spec)
gates={}
for name in ['system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py']:
 p=source/'project/experiments/control_v1'/name;assert sha(p)==sha(b/'source-388/project/experiments/control_v1'/name);gates[name]=sha(p)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,source_manifest_sha256=sha(source/'source-manifest.json'),unchanged_actual_acceptance_source_sha256=gates,whole_system_qualified=False,scope='Fix optional measured-budget branch search only: retain nondominated(cost,wire) labels and immutable parent labels. Independent full(vertex,wire) product-graph Dijkstra120 cases and3 actual finite-budget routed fixtures required, plus original9direction cases/3default byte replays/11rejections. Exact per-branch feasibility frontier is bounded at4million labels (memory envelope), and greedy multi-terminal tree remains non-complete; no whole-system feasibility/optimality claim. All original final geometry/PG/threeRC300MHz/current8program/joint gates unchanged; old failed raw and sources retained. Two current345instance full7stage chains wait for actual new preflight.'),indent=2));print(json.dumps(dict(queued=len(rows),record=str(record))))
'''
compile(q,'resource401','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
