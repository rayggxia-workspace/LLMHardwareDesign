from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';source=b/'source-608';record=b/'route-selection-102/sready609-pattern-weight-controls';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
for name in ['tree_router.cpp','tree_router_cpp.py','ordinary_zero_pattern.h','resource_search.h','system_upper.py','system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py','r256_scene.py']:
 assert sha(source/'project/experiments/control_v1'/name)==sha(b/'source-587/project/experiments/control_v1'/name)
assert json.loads((b/'r256-zero-pattern-regression-589/receipt.json').read_text())['passed']
def put(folder,name,spec):
 p=b/folder/'pending'/(name+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
reg=b/'r256-pattern-weight-regression-609'
put('dynamic-05/node4','00-f-sready609-pattern-weight-regression',dict(script='pattern_weight_regression.py',source_root=str(source),forecast_gib=16,requires=[str(b/'r256-zero-pattern-regression-589/receipt.json')],args=['--out',str(reg)]))
template=[x for x in json.loads((b/'route-selection-102/sready589-zero-pattern-controlled/tasks.json').read_text())['tasks']if '-5890'in Path(x['path']).stem];assert len(template)==7
for seed,weight,folder in [(6090,64,'dynamic-05/node4'),(6091,128,'dynamic-04/node25')]:
 config=root/('acceptance-'+str(seed)+'.json');assert not config.exists();config.write_text((root/'acceptance-5890.json').read_text().replace('/upper-candidates/5890/','/upper-candidates/'+str(seed)+'/'))
 for old in template:
  spec=json.loads(json.dumps(old['spec']));assert spec['source_root']==str(b/'source-587');spec['source_root']=str(source)
  for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/5890/','/upper-candidates/'+str(seed)+'/').replace('acceptance-5890.json','acceptance-'+str(seed)+'.json')for x in spec[key]]
  if spec['script']=='system_upper.py':
   a=spec['args'];assert '--route-ordinary-zero-pattern'in a and '--bidirectional-two-terminal'in a and a[a.index('--route-heuristic-weight')+1]=='256';a[a.index('--route-heuristic-weight')+1]=str(weight);spec['requires']+=[str(reg/'receipt.json')]
  put(folder,Path(old['path']).stem.replace('sready589','sready609').replace('5890',str(seed)),spec)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,scope='Only expand actual589-passed same source587 router to initial weights64/128; source608 adds nine-case compute-node preflight script only,15 routing/physical sources exactSHAunchanged.6090/6091 each differ5890 only initial heuristic weight, same current453/S5380/RNG4661/cost2/scale1/zero-pattern/bidirectional/critical finite8m/16active64attempts. Requires actual full589 and nine new weight/mode cases before route. Original complete7 final gates/current453 actualfunction/473480trajectory mandatory. Queue before own older359 source3583732 and source4004011 reallocation, all raw/source/spec/partial results preserved; no old failure/infeasibility or new convergence/final qualification claim.'),indent=2));print(json.dumps(dict(queued=len(rows),candidates=[6090,6091])))
