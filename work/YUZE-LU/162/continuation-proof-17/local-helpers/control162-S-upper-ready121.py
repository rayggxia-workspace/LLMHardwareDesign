"""Append exact new-S upper routes only after actual qualification/diagnostics."""
import subprocess, shlex

q = r'''from pathlib import Path
import hashlib,json,os,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
base=b/'s-internal-composition-01/1182';source=b/'source-121'
required=[b/'s-internal-qualified-02/1182/pg-delivery/receipt.json',base/'selected/receipt.json',
 base/'topology/receipt.json',base/'native-sta/native-system-audit.json',base/'cap-preflight/receipt.json',
 base/'native-cap-residual/receipt.json']
missing=[str(p)for p in required if not p.exists()]
if missing:print(json.dumps(dict(ready=False,missing=missing)));raise SystemExit(0)
assert all(json.loads(p.read_text())['passed']for p in required)
manifest=base/'selected/physical.json';signal=base/'topology/boundary-graph.json'
m=json.loads(manifest.read_text());g=json.loads(signal.read_text())
assert g['passed']and g['S_external_link_instances']==0
assert g['S_internal_drive']==m['leaves']['block_feed_s_macro']['S_internal_drive']
assert g['S_internal_drive']['all_four_gates_fresh']
assert not any(n.startswith('link_macro_s_')for n in g['instances'])
residual=json.loads((base/'native-cap-residual/native-cap-residual.json').read_text())
assert residual['passed']and len(residual['placements'])==1
row=residual['placements'][0]
assert row['placement']==str(base/'cap-preflight')
assert set(row['violations'])=={'low','base','high'}
assert not any(row['violations'].values()),row['violations']
cap=json.loads((base/'cap-preflight/wire-cap-lower-bound.json').read_text())
assert all(v<=row['physical_driver']['max_capacitance_ff']+1e-9 for row in cap['rows']for v in row['wire_capacitance_lower_bound_ff'].values())
regression=b/'router-weight-regression-09/receipt.json'
assert json.loads(regression.read_text())['passed']
for name in ['tree_router.cpp','tree_router_cpp.py','tree_router.py','router_regression.py']:
 assert hashlib.sha256((source/'project/experiments/control_v1'/name).read_bytes()).hexdigest()==hashlib.sha256((b/'source-114/project/experiments/control_v1'/name).read_bytes()).hexdigest(),name
record=b/'route-selection-102/s1182-upper-routes-source121.json';assert not record.exists()
rows=[]
def append(node,name,script,args,requires,out,memory=64):
 queue=b/('dynamic-04/node25'if node==25 else'dynamic-02/node26')/'pending'
 p=queue/(name+'.json');assert not p.exists()and not out.exists()
 spec=dict(script=script,source_root=str(source),forecast_gib=memory,requires=list(map(str,requires)),args=list(map(str,args))+['--out',str(out)])
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));os.rename(str(tmp),str(p))
 rows.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),spec=spec))
for seed,node,weight in [(1230,25,1),(1231,26,4),(1232,25,8),(1233,26,16)]:
 folder=base/'upper-candidates'/str(seed);route=folder/'route';geo=folder/'geometry';pg=folder/'pg-audit'
 append(node,'00-k-s1182-route-'+str(seed),'system_upper.py',[
  '--manifest',manifest,'--graph',signal,'--pg-wrappers',base/'fixed-pg-wrappers',
  '--pin-aware-placement','--reuse-placement',base/'cap-preflight','--seed',seed,
  '--route-trials',16,'--route-heuristic-weight',weight,'--negotiate-priority-routes',
  '--defer-access-vias','--lock-native-output-routes'],required+[regression],route,32)
 common=['--manifest',manifest,'--graph',route/'physical-graph.json','--route',route]
 append(node,'00-l-s1182-geometry-'+str(seed),'system_geometry.py',common,[route/'receipt.json'],geo)
 append(node,'00-m-s1182-pg-'+str(seed),'system_geometry.py',common+['--pg-audit',geo],[geo/'receipt.json'],pg,32)
 timing={}
 for corner in ['low','base','high']:
  out=folder/'timing'/corner;timing[corner]=str(out)
  append(node,'00-n-s1182-sta-'+str(seed)+'-'+corner,'system_sta.py',[
   '--manifest',manifest,'--functional-views',base/'selected/functions.json',
   '--topology',base/'topology/topology.json','--graph',signal,'--upper-geometry',geo,
   '--stitch-native-access','--audit-native-coverage','--rc-variant',corner],
   [geo/'receipt.json',pg/'receipt.json'],out)
 config=b/'route-selection-102'/('s1182-acceptance-'+str(seed)+'.json');assert not config.exists()
 config.write_text(json.dumps(dict(geometry=str(geo),pg_audit=str(pg),function_run=str(base/'final-composition'),
  topology=str(base/'topology/topology.json'),signal_graph=str(signal),timing=timing),indent=2))
 append(node,'00-o-s1182-delivery-'+str(seed),'system_geometry.py',common+['--acceptance',config],
  [geo/'receipt.json',pg/'receipt.json',base/'final-composition/receipt.json']+
  [Path(out)/'native-system-audit.json'for out in timing.values()],folder/'delivery')
record.write_text(json.dumps(dict(time=time.time(),tasks=rows,instance_count=len(g['instances']),
 source='source-121',prerequisites={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in required},
 scope='Four independent routes and24 downstream gates for freshly qualified S1182 exact actual graph. Actual native-ground+upper necessary diagnostics clear; complete function/geometry/PG/low-base-high RC still mandatory. No old335 function result reused; no qualification inferred.'),indent=2))
print(json.dumps(dict(ready=True,appended=len(rows),actual_instances=len(g['instances']),record=str(record))))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
