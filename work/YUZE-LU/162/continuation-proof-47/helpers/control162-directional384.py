import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-359';source=b/'source-383';record=b/'route-selection-102/sready384-directional';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
old=json.loads((b/'route-selection-102/sready373-reset53-upper/tasks.json').read_text())['tasks']
template=[r for r in old if '-3730' in Path(r['path']).name];assert len(template)==7
gates={}
for name in ['system_geometry.py','system_sta.py','system_function.py','upper_cap_bound.py','native_pin_load.py']:
 p=source/'project/experiments/control_v1'/name
 if p.exists():assert sha(p)==sha(b/'source-358/project/experiments/control_v1'/name);gates[name]=sha(p)
rows=[]
def put(queue,name,spec):
 p=b/queue/'pending'/(name+'.json');assert not p.exists();t=p.with_suffix('.tmp');t.write_text(json.dumps(spec));t.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
reg=b/'r256-directional-regression-384';put('dynamic-03/node5','00-f-sready384-directional-regression',dict(script='system_upper.py',source_root=str(source),forecast_gib=16,requires=[str(root/'selected/receipt.json'),str(root/'topology/receipt.json')],args=['--manifest',str(root/'selected/physical.json'),'--graph',str(root/'topology/boundary-graph.json'),'--directional-regression-only','--route-regression-baseline',str(b/'source-358/project/experiments/control_v1/tree_router.cpp'),'--out',str(reg)]))
for seed,cost,queue in [(3840,8,'dynamic-03/node5'),(3841,32,'dynamic-04/node25')]:
 newroot=root/'upper-candidates'/str(seed);assert not newroot.exists()
 config=root/('acceptance-'+str(seed)+'.json');oldconfig=root/'acceptance-3730.json';assert not config.exists();config.write_text(oldconfig.read_text().replace('/upper-candidates/3730/','/upper-candidates/'+str(seed)+'/'))
 for row in template:
  spec=json.loads(json.dumps(row['spec']));spec['source_root']=str(source)
  for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/3730/','/upper-candidates/'+str(seed)+'/').replace('acceptance-3730.json','acceptance-'+str(seed)+'.json')for x in spec[key]]
  if spec['script']=='system_upper.py':
   a=spec['args'];a[a.index('--seed')+1]=str(seed);a+=['--route-nonpreferred-cost',str(cost)];spec['requires']+=[str(reg/'receipt.json')]
  name=Path(row['path']).stem.replace('sready373','sready384').replace('3730',str(seed));put(queue,name,spec)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,unchanged_acceptance_sources=gates,source_manifest_sha256=sha(source/'source-manifest.json'),whole_system_qualified=False,scope='Nine real small search comparisons/three exact default output+log replays/nine rejection controls required before two full current345instance reset53 searches. Compare only nonpreferred M11 vertical/M12 horizontal search cost8/32 against old2. Selected3690 necessaryhighratio0.910436 retained. Every actual geometry/PG/three-RC300MHz/current359eight-program/full joint delivery gate unchanged. No system qualification from search regression.'),indent=2));print(json.dumps(dict(queued=len(rows),record=str(record))))
'''
compile(q,'queue384','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
