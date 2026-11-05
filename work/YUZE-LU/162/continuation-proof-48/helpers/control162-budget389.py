import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time,sys,math
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-359';source=b/'source-388';record=b/'route-selection-102/sready389-measured-route-budget';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
sys.path.insert(0,str(source/'project/experiments/control_v1'));from placement_residual_budget import budgets
place=root/'cap-candidates/3690';bound=json.loads((place/'wire-cap-lower-bound.json').read_text());drivers={r['net']:r for r in bound['rows']};report=root/'native-pin-load369/native-pin-load.json';remaining,bindings=budgets(report,drivers)
for p in [root/'selected/physical.json',root/'topology/boundary-graph.json']:
 r=json.loads((report.parent/'receipt.json').read_text());assert r['inputs'][str(p)]==sha(p)
reg=b/'r256-directional-regression-384/receipt.json';assert json.loads(reg.read_text())['passed'];priority=b/'r256-reset53-priority-regression-375/receipt.json';assert json.loads(priority.read_text())['passed']
template=[r for r in json.loads((b/'route-selection-102/sready373-reset53-upper/tasks.json').read_text())['tasks']if '-3730'in Path(r['path']).name];assert len(template)==7;rows=[]
for seed,cost,queue in [(3890,8,'dynamic-05/node2'),(3891,2,'dynamic-02/node3')]:
 config=root/('acceptance-'+str(seed)+'.json');assert not config.exists();config.write_text((root/'acceptance-3730.json').read_text().replace('/upper-candidates/3730/','/upper-candidates/'+str(seed)+'/'))
 for row in template:
  spec=json.loads(json.dumps(row['spec']));spec['source_root']=str(source)
  for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/3730/','/upper-candidates/'+str(seed)+'/').replace('acceptance-3730.json','acceptance-'+str(seed)+'.json')for x in spec[key]]
  if spec['script']=='system_upper.py':
   a=spec['args'];a[a.index('--seed')+1]=str(seed);a+=['--route-residual-budget',str(report),'--route-nonpreferred-cost',str(cost)];spec['requires']+=[str(reg),str(priority)]
  p=b/queue/'pending'/(Path(row['path']).stem.replace('sready373','sready389').replace('3730',str(seed))+'.json');assert not p.exists();t=p.with_suffix('.tmp');t.write_text(json.dumps(spec));t.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
gates={}
for name in ['system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py']:
 p=source/'project/experiments/control_v1'/name;assert p.exists()and sha(p)==sha(b/'source-358/project/experiments/control_v1'/name);gates[name]=sha(p)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,source_manifest_sha256=sha(source/'source-manifest.json'),unchanged_actual_acceptance_source_sha256=gates,measured_bindings=bindings,actual_driver_count=len(remaining),smallest_native_and_minimum_input_residual_ff=min(remaining.values()),whole_system_qualified=False,scope='Actual345instance reset53 composition and original7stage chains. Finite priority source wire budgets now subtract measured native ground and minimum actual input load using original bound helper; original maxcap unchanged, finite cpp checks unchanged. New option validated by source/hash/cross-placement agreement and17 local unit tests. Actual vias/coupling/input cap and threeRC300MHz still mandatory. Two real directional/non-directional current searches queued before retiring exactly own obsolete235 duplicate searches. No foreign/R/task changes and no system pass.'),indent=2));print(json.dumps(dict(queued=len(rows),drivers=len(remaining),minimum_residual_ff=min(remaining.values()))))
'''
compile(q,'budget389','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
