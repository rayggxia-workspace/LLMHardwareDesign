from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';source=b/'source-474';record=b/'route-selection-102/sready476-controlled-high-weight';assert not record.exists();rows=[];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();reg=b/'r256-high-weight-regression-475'
def put(name,spec):
 p=b/'dynamic-07/node7/pending'/(name+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
spec=dict(script='system_upper.py',source_root=str(source),forecast_gib=16,requires=[str(root/'topology/receipt.json')],args=['--manifest',str(b/'r256-composition-359/selected/physical.json'),'--graph',str(root/'topology/boundary-graph.json'),'--directional-regression-only','--route-regression-baseline',str(b/'source-451/project/experiments/control_v1/tree_router.cpp'),'--out',str(reg)])
put('00-f-sready475-high-weight-regression',spec)
template=[x for x in json.loads((b/'route-selection-102/sready466-padding-full-upper/tasks.json').read_text())['tasks']if '-4661'in Path(x['path']).stem];assert len(template)==7
config=root/'acceptance-4760.json';assert not config.exists();config.write_text((root/'acceptance-4661.json').read_text().replace('/upper-candidates/4661/','/upper-candidates/4760/'))
for old in template:
 spec=json.loads(json.dumps(old['spec']));spec['source_root']=str(source)
 for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/4661/','/upper-candidates/4760/').replace('acceptance-4661.json','acceptance-4760.json').replace('r256-critical-partition-regression-438','r256-high-weight-regression-475')for x in spec[key]]
 if spec['script']=='system_upper.py':
  a=spec['args'];assert a[a.index('--seed')+1]=='4661'and a[a.index('--route-nonpreferred-cost')+1]=='2';a[a.index('--route-heuristic-weight')+1]='128'
 put(Path(old['path']).stem.replace('sready466','sready476').replace('4661','4760'),spec)
gates={}
for name in ['system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py']:
 p=source/'project/experiments/control_v1'/name;assert sha(p)==sha(b/'source-451/project/experiments/control_v1'/name);gates[name]=sha(p)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,unchanged_actual_acceptance_source_sha256=gates,whole_system_qualified=False,scope='Controlled candidate4760 vs4661 on actual453 topology: same placement4610/RNG4661/cost2/congestion1/adaptive schedule/critical-first/8million labels/64attempts16active; only initial search weight128 vs16 and mathematically required high-weight annealing to1 differ. Old1..32 annealing identical for1000rounds each, actual default-byte replay and new64/128/256 routes plus envelope rejects mandatory in475 before full search. No source logic or physical constraint changes; whole final geometry/PG/low-base-high300MHz/current453function/joint gates unchanged. New seven-stage chain plus actual regression queued, not passed or complete; no convergence/speed claim. Own existing node7 16CPU slot, old raw/source/spec retained.'),indent=2));print(json.dumps(dict(queued=len(rows),rng_seed=4661,initial_search_weight=128)))
