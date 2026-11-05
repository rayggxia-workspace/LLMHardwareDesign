import subprocess,shlex
q=r'''from pathlib import Path
import json,collections,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-359';g=json.loads((root/'topology/boundary-graph.json').read_text());p=json.loads((root/'cap-candidates/3690/placement.json').read_text());report=json.loads((root/'native-pin-load369/native-pin-load.json').read_text());native={r['net']:r for place in report['placements']if Path(place['placement']).name=='3690'for r in place['rows']}
for seed in [3890,3891]:
 route=root/'upper-candidates'/str(seed)/'route';limit=json.loads((route/'locked-original-output-search.json').read_text());failed=collections.Counter();rounds=[]
 for f in route.glob('trial-*/router.log'):
  lines=f.read_text().splitlines()
  if lines and lines[-1].startswith('disconnected tree: '):failed[lines[-1].split(': ',1)[1]]+=1
 print('seed',seed,'failed_trials',sum(failed.values()),'failure_nets',dict(failed))
 for net,count in failed.items():
  r=native[net];ends=p['terminals'][net];print(json.dumps(dict(net=net,failed_trials=count,driver=g['connections'][net[4:]]['driver'],physical_driver=r.get('physical_driver'),native_ground_ff=r['native_ground_cap_ff'],minimum_input_ff=r['minimum_input_pin_cap_ff'],max_ff=r['max_capacitance_ff'],original_hpwl_um=4*(max(x for x,y in ends)-min(x for x,y in ends)+max(y for x,y in ends)-min(y for x,y in ends)),finite_wire_edges=limit['wire_limits_grid_edges'][net],terminal_points=ends)))
'''
print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=30).decode())
