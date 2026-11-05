from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';source=b/'source-653';record=b/'route-selection-102/sready655-congestion-scale-controls';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
for name in ['tree_router.cpp','tree_router_cpp.py','ordinary_zero_pattern.h','resource_search.h','system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py','r256_scene.py']:
 assert sha(source/'project/experiments/control_v1'/name)==sha(b/'source-633/project/experiments/control_v1'/name)
assert json.loads((b/'r256-zero-pattern-regression-589/receipt.json').read_text())['passed']
def put(folder,name,spec):
 p=b/folder/'pending'/(name+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
assert json.loads((b/'r256-directional-bidir-regression-635/receipt.json').read_text())['passed']
reg=b/'r256-pattern-scale-regression-655'
put('dynamic-05/node2','00-f-sready655-pattern-scale-regression',dict(script='system_upper.py',source_root=str(source),forecast_gib=16,requires=[str(b/'r256-zero-pattern-regression-589/receipt.json')],args=['--manifest',str(b/'r256-composition-359/selected/physical.json'),'--graph',str(root/'topology/boundary-graph.json'),'--pattern-scale-regression-only','--out',str(reg)]))
template=[x for x in json.loads((b/'route-selection-102/sready589-zero-pattern-controlled/tasks.json').read_text())['tasks']if '-5890'in Path(x['path']).stem];assert len(template)==7
for seed,weight,folder in [(6560,4,'dynamic-05/node2'),(6561,8,'dynamic-02/node3'),(6562,16,'dynamic-04/node25'),(6563,32,'dynamic-05/node4')]:
 config=root/('acceptance-'+str(seed)+'.json');assert not config.exists();config.write_text((root/'acceptance-5890.json').read_text().replace('/upper-candidates/5890/','/upper-candidates/'+str(seed)+'/'))
 for old in template:
  spec=json.loads(json.dumps(old['spec']));assert spec['source_root']==str(b/'source-587');spec['source_root']=str(source)
  for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/5890/','/upper-candidates/'+str(seed)+'/').replace('acceptance-5890.json','acceptance-'+str(seed)+'.json')for x in spec[key]]
  if spec['script']=='system_upper.py':
   a=spec['args'];assert '--route-ordinary-zero-pattern'in a and '--bidirectional-two-terminal'in a and a[a.index('--route-heuristic-weight')+1]=='256';assert a[a.index('--route-congestion-scale')+1]=='1';a[a.index('--route-congestion-scale')+1]=str(weight);spec['requires']+=[str(reg/'receipt.json')]
  put(folder,Path(old['path']).stem.replace('sready589','sready655').replace('5890',str(seed)),spec)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,scope='Reuse byte-identical actual635-passed source633 router in source653; add only15case scale preflight/dispatcher. Four controlled6560..6563 differ5890 only existing global congestion_scale1to4/8/16/32 at fixed h256/cost2/bidirectional/zero-pattern/current453/S5380/RNG4661/critical8m/16active64attempts. This changes both constrained and ordinary search penalties, never physical wire-length/electrical limits. Requires real15case preflight and all original seven final physical stages/current453 function/473480trajectory.14 router/physical source files exactSHAunchanged from633. Four proposed old359/source41116active64attempt slots were independently fully read back654, then exact UID/job/node/PID/cmd/out/graph/source/specSHA guards must recheck before task-local reallocation. Preserve every prior log/source/spec/partial output and independent CUGR3751; no old infeasibility or new speed/convergence/physical claim.'),indent=2));print(json.dumps(dict(queued=len(rows),candidates=[6560,6561])))
