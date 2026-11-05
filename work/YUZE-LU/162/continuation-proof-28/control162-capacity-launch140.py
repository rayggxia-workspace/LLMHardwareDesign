import subprocess,shlex
q=r'''from pathlib import Path
import json,time,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');base=b/'s-ready-composition-01/1391';record=b/'route-selection-102/sready140-capacity-placements1420-1425.json';assert not record.exists();rows=[]
assert json.loads((base/'native-sta/native-system-audit.json').read_text())['passed']and json.loads((base/'native-sta/receipt.json').read_text())['typed_native_timing_passed']
for seed,node,gap,target in [(1420,2,64,.45),(1421,4,256,.45),(1422,2,256,.55),(1423,4,512,.55),(1424,2,256,.65),(1425,4,512,.65)]:
 f=b/('dynamic-05/node'+str(node))/'pending'/('00-p-sready140-capacity-'+str(seed)+'.json');out=base/'cap-capacity-candidates'/str(seed);assert not f.exists()and not out.exists()
 args=['--manifest',base/'selected/physical.json','--graph',base/'topology/boundary-graph.json','--pg-wrappers',base/'fixed-pg-wrappers','--cap-lower-bound-only','--pin-aware-placement','--electrical-placement-report',base/'cap-initial/wire-cap-lower-bound.json','--placement-capacity-target',str(target),'--seed',str(seed),'--channel-gap-um',str(gap),'--out',out]
 spec=dict(script='system_upper.py',source_root=str(b/'source-140'),forecast_gib=32,requires=[str(base/'cap-initial/receipt.json')],args=list(map(str,args)));tmp=f.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(f);rows.append(dict(spec=str(f),spec_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),out=str(out),seed=seed,node=node,gap=gap,placement_objective_target=target))
record.write_text(json.dumps(dict(time=time.time(),tasks=rows,reason='Current qualified1391/1404 actual signal HPWL requires 4185403 grid edges across5300768 two-layer nodes, an optimistic79percent occupancy before detours/vias/PG. Preserve four existing exact routes and run more spacious placement diagnostics in free own sixteen-CPU slots. Capacity target changes search objective only, never any acceptance threshold or block masks. Same exact qualified21 types and same actual235instance graph.'),indent=2));print('Appended',len(rows),'independent same-hardware placement diagnostics')
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
