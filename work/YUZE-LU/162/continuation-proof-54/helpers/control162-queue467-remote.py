from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');old=b/'r256-composition-359';root=b/'r256-composition-453';source=b/'source-451';record=b/'route-selection-102/sready467-padding-full-upper';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
template=json.loads((b/'route-selection-102/sready434-compact-upper/tasks.json').read_text())['tasks'];assert len(template)==7
reg=b/'r256-critical-partition-regression-438/receipt.json';rp=json.loads(reg.read_text());assert rp['passed'];reused={}
for p,digest in rp['inputs'].items():
 if p.startswith(str(b/'source-435')+'/'):
  target=source/Path(p).relative_to(b/'source-435');assert sha(target)==digest;reused[str(target)]=digest
summary=[]
for seed,cost,folder in [(4670,8,'dynamic-05/node4')]:
 place=root/'cap-candidates/4611';native=root/'cap-necessary-461/4611/native-pin-load';proof=json.loads((native/'receipt.json').read_text());assert proof['passed'];report=json.loads((native/'native-pin-load.json').read_text());assert len(report['placements'])==1;row=report['placements'][0];assert row['placement']==str(place)and all(n==0 for n in row['violations'].values());worst=max(r['optimistic_total_with_minimum_pin_ff']['high']/r['max_capacitance_ff']for r in row['rows']);p=json.loads((place/'placement.json').read_text());summary.append(dict(seed=seed,placement=4611,width_um=p['width_um'],height_um=p['height_um'],area_um2=p['width_um']*p['height_um'],necessary_high_worst_ratio=worst,necessary_receipt_sha256=sha(native/'receipt.json')))
 def paths(s):
  return s.replace(str(old),str(root)).replace(str(root/'selected'),str(old/'selected')).replace(str(root/'fixed-pg-wrappers'),str(old/'fixed-pg-wrappers')).replace('/upper-candidates/4340/','/upper-candidates/'+str(seed)+'/').replace('acceptance-4340.json','acceptance-'+str(seed)+'.json')
 config=root/('acceptance-'+str(seed)+'.json');assert not config.exists();config.write_text(paths((old/'acceptance-4340.json').read_text()))
 for previous in template:
  spec=json.loads(json.dumps(previous['spec']));spec['source_root']=str(source)
  for key in ['args','requires']:spec[key]=[paths(x)for x in spec[key]]
  if spec['script']=='system_upper.py':
   a=spec['args'];a[a.index('--seed')+1]=str(seed);a[a.index('--reuse-placement')+1]=str(place);a[a.index('--route-residual-budget')+1]=str(native/'native-pin-load.json');a[a.index('--route-nonpreferred-cost')+1]=str(cost);a+=['--route-critical-first'];spec['requires']=[str(native/'receipt.json'),str(root/'topology/receipt.json'),str(reg)]
  # No stale current359 event/function prerequisite grants candidate453 a pass.
  assert all('r256-current-program-event-audit-422'not in x for x in spec['requires'])
  path=b/folder/'pending'/(Path(previous['path']).stem.replace('sready434','sready467').replace('4340',str(seed))+'.json');assert not path.exists();tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(path);rows.append(dict(path=str(path),sha256=sha(path),spec=spec))
gates={}
for name in ['system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py']:
 p=source/'project/experiments/control_v1'/name;assert sha(p)==sha(b/'source-435/project/experiments/control_v1'/name);gates[name]=sha(p)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,actual_candidates=summary,reused_actual_route_regression_inputs=reused,unchanged_actual_acceptance_source_sha256=gates,whole_system_qualified=False,scope='Candidate453 full physical chain4670 uses actual4611 placement with zero original low/base/high native-ground/minimum-pin/strong-tree necessary violations, actual source451 topology/contract and native coverage completed. Same23 qualified fixed macros and345 instances/state,267 actual unused input loads transferred to existing reset banks and fully counted. Cost8, heuristic16/congestion1,8million labels,64finite attempts16active, every-round constrained priority. Actual438 routing implementation inputs byte-identical and explicitly rehashed for reuse. Original final geometry/nativeXOR/PG/threeRC300MHz/current453function/joint gates unchanged. Current453 full final-cell programs still compiling; no original359 function/event qualification inherited. Old initial453 high5 violations and original359 all27 chains retained. Node4 completed placement slot naturally refills, no cancellation or new parents.'),indent=2));print(json.dumps(dict(queued=len(rows),candidates=summary)))
