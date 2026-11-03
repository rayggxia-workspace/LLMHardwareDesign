from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';source=b/'source-668';record=b/'route-selection-102/sready671-default-congestion-control';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
for name in ['tree_router.cpp','tree_router_cpp.py','ordinary_zero_pattern.h','resource_search.h','system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py','r256_scene.py']:
 assert sha(source/'project/experiments/control_v1'/name)==sha(b/'source-633/project/experiments/control_v1'/name)
assert json.loads((b/'r256-zero-pattern-regression-589/receipt.json').read_text())['passed']
def put(folder,name,spec):
 p=b/folder/'pending'/(name+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
assert json.loads((b/'r256-directional-bidir-regression-635/receipt.json').read_text())['passed']
assert json.loads((b/'r256-pattern-scale-regression-655/receipt.json').read_text())['passed']
reg=b/'r256-default-scale-regression-671'
put('dynamic-02/node6','00-f-sready671-pattern-scale-regression',dict(script='system_upper.py',source_root=str(source),forecast_gib=16,requires=[str(b/'r256-zero-pattern-regression-589/receipt.json')],args=['--manifest',str(b/'r256-composition-359/selected/physical.json'),'--graph',str(root/'topology/boundary-graph.json'),'--pattern-scale-regression-only','--out',str(reg)]))
template=[x for x in json.loads((b/'route-selection-102/sready589-zero-pattern-controlled/tasks.json').read_text())['tasks']if '-5890'in Path(x['path']).stem];assert len(template)==7
for seed,weight,folder in [(6720,0,'dynamic-02/node6')]:
 config=root/('acceptance-'+str(seed)+'.json');assert not config.exists();config.write_text((root/'acceptance-5890.json').read_text().replace('/upper-candidates/5890/','/upper-candidates/'+str(seed)+'/'))
 for old in template:
  spec=json.loads(json.dumps(old['spec']));assert spec['source_root']==str(b/'source-587');spec['source_root']=str(source)
  for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/5890/','/upper-candidates/'+str(seed)+'/').replace('acceptance-5890.json','acceptance-'+str(seed)+'.json')for x in spec[key]]
  if spec['script']=='system_upper.py':
   a=spec['args'];assert '--route-ordinary-zero-pattern'in a and '--bidirectional-two-terminal'in a and a[a.index('--route-heuristic-weight')+1]=='256';assert a[a.index('--route-congestion-scale')+1]=='1';a[a.index('--route-congestion-scale')+1]=str(weight);spec['requires']+=[str(reg/'receipt.json')]
  put(folder,Path(old['path']).stem.replace('sready589','sready671').replace('5890',str(seed)),spec)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,scope='Existing default congestion_scale0 at fixed h256 means effective256, not zero penalty. Source668 changes only scale preflight to18cases including0 normalization; all14 production router/physical sources exactSHA from633.6720 differs5890 only global congestion_scale1to0/default256, same current453/S5380/h256/cost2/bidirectional/zero-pattern/RNG4661/finite8m16active64attempts/physical wire limits. Requires actual18case671 preflight after actual15case655 and full635. All original seven final geometry/nativeXOR/PG/threeRC300MHz/current453function/joint gates remain mandatory. Reassign only complete-spec664 verified own old359/source4294300 slot after UID/job/node/PID/cmd/out/graph/source/specSHA guard; retain all prior17+failed/partial logs, source/spec, current453 searches, CUGR3751, parents and externalR/foreign jobs. No speed/convergence/physical qualification claim.'),indent=2));print(json.dumps(dict(queued=len(rows),candidates=[6720])))
