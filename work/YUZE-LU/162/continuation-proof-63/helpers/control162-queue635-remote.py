from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';source=b/'source-633';record=b/'route-selection-102/sready635-directional-bidirectional-controls';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
for name in ['system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py','resource_search.h','r256_scene.py']:
 assert sha(source/'project/experiments/control_v1'/name)==sha(b/'source-587/project/experiments/control_v1'/name)
assert json.loads((b/'r256-zero-pattern-regression-589/receipt.json').read_text())['passed']
def put(folder,name,spec):
 p=b/folder/'pending'/(name+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
reg=b/'r256-directional-bidir-regression-635'
put('dynamic-03/node5','00-f-sready635-directional-bidirectional-regression',dict(script='system_upper.py',source_root=str(source),forecast_gib=16,requires=[str(b/'r256-zero-pattern-regression-589/receipt.json')],args=['--manifest',str(b/'r256-composition-359/selected/physical.json'),'--graph',str(root/'topology/boundary-graph.json'),'--directional-regression-only','--route-regression-baseline',str(b/'source-613/project/experiments/control_v1/tree_router.cpp'),'--out',str(reg)]))
template=[x for x in json.loads((b/'route-selection-102/sready589-zero-pattern-controlled/tasks.json').read_text())['tasks']if '-5890'in Path(x['path']).stem];assert len(template)==7
for seed,weight,folder in [(6360,8,'dynamic-03/node5'),(6361,32,'dynamic-02/node6')]:
 config=root/('acceptance-'+str(seed)+'.json');assert not config.exists();config.write_text((root/'acceptance-5890.json').read_text().replace('/upper-candidates/5890/','/upper-candidates/'+str(seed)+'/'))
 for old in template:
  spec=json.loads(json.dumps(old['spec']));assert spec['source_root']==str(b/'source-587');spec['source_root']=str(source)
  for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/5890/','/upper-candidates/'+str(seed)+'/').replace('acceptance-5890.json','acceptance-'+str(seed)+'.json')for x in spec[key]]
  if spec['script']=='system_upper.py':
   a=spec['args'];assert '--route-ordinary-zero-pattern'in a and '--bidirectional-two-terminal'in a and a[a.index('--route-heuristic-weight')+1]=='256';assert a[a.index('--route-nonpreferred-cost')+1]=='2';a[a.index('--route-nonpreferred-cost')+1]=str(weight);spec['requires']+=[str(reg/'receipt.json')]
  put(folder,Path(old['path']).stem.replace('sready589','sready635').replace('5890',str(seed)),spec)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,scope='Source633 extends existing bidirectional base direction cost2 to checked8/32, preserving reverse destination penalty and balanced reduced-cost invariants. Original100 Dijkstra cases retained plus200 new directional cases, full old actual regression and18 new actual cases/6 cost2 byte replays required before full6360/6361 release. Compared5890 only direction-cost2to8or32; same current453/S5380/RNG4661/h256/scale1/zero-pattern/critical8m16active64attempts and original7 final physical gates.9 final gate sources/resource_search.h/r256_scene.py sameSHA. Old source400/older3594080/4081 exact own slots may be reassigned, all raw/source/spec/partial outputs preserved; active current5890/5640/6140/6141 and independent CUGR3751 retained. No old infeasibility/new speed/convergence/system qualification claim.'),indent=2));print(json.dumps(dict(queued=len(rows),candidates=[6360,6361])))
