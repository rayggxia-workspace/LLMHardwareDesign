from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';source=b/'source-717';record=b/'route-selection-102/sready718-phase-trace-controls';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
for name in ['system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py','resource_search.h','r256_scene.py']:
 assert sha(source/'project/experiments/control_v1'/name)==sha(b/'source-668/project/experiments/control_v1'/name)
assert json.loads((b/'r256-zero-pattern-regression-589/receipt.json').read_text())['passed']
old=(b/'source-668/project/experiments/control_v1/tree_router.cpp').read_text();new=(source/'project/experiments/control_v1/tree_router.cpp').read_text();start='    if(pareto_wire_budget&&n<locked_count&&wire_limits[n]>=0){';end='    }else if(bidirectional_two_terminal';assert old.split(start,1)[1].split(end,1)[0]==new.split(start,1)[1].split(end,1)[0]
assert json.loads((b/'r256-default-scale-regression-671/receipt.json').read_text())['passed']
def put(folder,name,spec):
 p=b/folder/'pending'/(name+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
reg=b/'r256-phase-trace-regression-718'
put('dynamic-07/node7','00-f-sready718-phase-trace-regression',dict(script='system_upper.py',source_root=str(source),forecast_gib=16,requires=[str(b/'r256-zero-pattern-regression-589/receipt.json')],args=['--manifest',str(b/'r256-composition-359/selected/physical.json'),'--graph',str(root/'topology/boundary-graph.json'),'--directional-regression-only','--route-regression-baseline',str(b/'source-690/project/experiments/control_v1/tree_router.cpp'),'--out',str(reg)]))
template=[x for x in json.loads((b/'route-selection-102/sready589-zero-pattern-controlled/tasks.json').read_text())['tasks']if '-5890'in Path(x['path']).stem];assert len(template)==7
for seed,weight,folder in [(7200,1,'dynamic-07/node7')]:
 config=root/('acceptance-'+str(seed)+'.json');assert not config.exists();config.write_text((root/'acceptance-5890.json').read_text().replace('/upper-candidates/5890/','/upper-candidates/'+str(seed)+'/'))
 for old in template:
  spec=json.loads(json.dumps(old['spec']));assert spec['source_root']==str(b/'source-587');spec['source_root']=str(source)
  for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/5890/','/upper-candidates/'+str(seed)+'/').replace('acceptance-5890.json','acceptance-'+str(seed)+'.json')for x in spec[key]]
  if spec['script']=='system_upper.py':
   a=spec['args'];assert '--route-ordinary-zero-pattern'in a and '--bidirectional-two-terminal'in a and a[a.index('--route-heuristic-weight')+1]=='256';assert a[a.index('--route-nonpreferred-cost')+1]=='2';assert a[a.index('--route-congestion-scale')+1]=='1';a[a.index('--route-congestion-scale')+1]=str(weight);a+=['--route-weighted-bidirectional','--route-trace-phases'];a[a.index('--seed')+1]='4662';spec['forecast_gib']=64;spec['requires']+=[str(reg/'receipt.json')]
  put(folder,Path(old['path']).stem.replace('sready589','sready718').replace('5890',str(seed)),spec)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,scope='Source717 adds only optional bounded phase timing trace; actual full regression718 uses source690 baseline, includes27 cases/3 phase-only byte replays/8 invalid rejects and unchanged older tests. Candidate7200 uses current453/S5380 weighted global1 with new independent RNG4662,16active64attempts. All seven final geometry/PG/3RC300MHz/current function and trace prerequisites retained. No physical qualification inherited. Reallocate only exact own old S4610 placement4760 after guarded read719; preserve source/spec/logs, CUGR3751/all other tasks.'),indent=2));print(json.dumps(dict(queued=len(rows),candidates=[7200])))
