import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-258';root=b/'r256-composition-263';record=b/'route-selection-102/sready263-final-qualified-scene';assert not root.exists()and not record.exists();root.mkdir();record.mkdir();rows=[]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
configs={
 'control_c_r8':str(b/'r256-fixed-pg-261/2371/delivery'),
 'control_route_r8':str(b/'r256-fixed-pg-235/2292/delivery'),
 'control_status_r8':str(b/'r256-fixed-pg-235/2294/delivery'),
 'control_reset_distribution_r28':str(b/'r256-fixed-pg-235/2295/delivery'),
 'control_s_arbiter_r7':str(b/'r256-fixed-pg-246/2333/delivery'),
 'control_adapter_r':str(b/'r256-fixed-pg-254/2430/delivery'),
 'r_stream_local':str(b/'r256-fixed-pg-257/delivery')}
config=root/'configurations.json';config.write_text(json.dumps(configs,indent=2))
wrappers=root/'fixed-pg-wrappers';wrappers.mkdir();old=b/'s-ready-composition-01/1391/selected';m=json.loads((old/'physical.json').read_text());replace={'control_c','control_route','control_s_arbiter','control_status','control_reset_distribution'}
for top,row in m['leaves'].items():
 if top in replace:continue
 d=json.loads(Path(row['fixed_pg_delivery']['path']).read_text());assert d['passed'];(wrappers/top).symlink_to(Path(d['fixed_pg_receipt']).parent)
for top,folder in configs.items():(wrappers/top).symlink_to(Path(folder).parent/'wrapper')
assert len(list(wrappers.iterdir()))==23

def add(name,script,args,deps,out,memory=32):
 p=b/'dynamic-06/node7/pending'/(name+'.json');assert not p.exists()and not out.exists()
 spec=dict(script=script,source_root=str(source),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args))+['--out',str(out)])
 t=p.with_suffix('.tmp');t.write_text(json.dumps(spec));t.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
sel=root/'selected';top=root/'topology';g=top/'boundary-graph.json';manifest=sel/'physical.json'
add('00-a-sready263-qualified-selection','select_leaves.py',['--physical',old/'physical.json','--functions',old/'functions.json','--r256-configurations',config],[Path(p)/'receipt.json'for p in configs.values()],sel)
args=['--manifest',manifest,'--r256-scene']
for n in ['macro_1','macro_2','macro_3','macro_4','macro_t','macro_r']:args+=['--link-native-output',n]
for n in ['s_port:dout','controller:task_data','controller:task_last']:args+=['--split-output-fanout',n]
add('00-b-sready263-final-topology','topology.py',args,[sel/'receipt.json'],top)
add('00-c-sready263-native-sta','system_sta.py',['--manifest',manifest,'--functional-views',sel/'functions.json','--topology',top/'topology.json','--graph',g,'--stitch-native-access','--audit-native-coverage'],[top/'receipt.json'],root/'native-sta',128)
common=['--manifest',manifest,'--graph',g,'--pg-wrappers',wrappers,'--cap-lower-bound-only','--pin-aware-placement']
initial=root/'cap-initial'
add('00-c-sready263-initial-placement','system_upper.py',common+['--seed',2630,'--channel-gap-um',256],[top/'receipt.json'],initial)
places=[]
for n,gap in [(2631,64),(2632,256),(2633,512)]:
 place=root/'cap-candidates'/str(n);places.append(place)
 add('00-d-sready263-placement-'+str(n),'system_upper.py',common+['--seed',n,'--channel-gap-um',gap,'--electrical-placement-report',initial/'wire-cap-lower-bound.json','--placement-capacity-target','.35'],[initial/'receipt.json'],place)
resconf=root/'native-cap-config.json';resconf.write_text(json.dumps(dict(native_sta=str(root/'native-sta'),placements=list(map(str,places))),indent=2))
res=root/'native-residual';pin=root/'native-pin-load'
add('00-e-sready263-native-residual','system_upper.py',['--manifest',manifest,'--graph',g,'--native-cap-residual-config',resconf],[root/'native-sta/native-system-audit.json']+[p/'receipt.json'for p in places],res)
add('00-f-sready263-native-pin-load','system_upper.py',['--manifest',manifest,'--graph',g,'--native-pin-load-residual',res/'native-cap-residual.json'],[res/'receipt.json'],pin)
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,configurations_sha256=sha(config),whole_system_qualified=False,scope='23 actual accepted fixed-PG types, exact seven-native R256 graph, actual full-native/300MHz diagnostics and three physical placements with all native/wire/input-pin necessary gates. Original final full geometry/PG/three-RC/program/300MHz acceptance mandatory. No proxy or early physical qualification. Own existing dynamic node7 four sixteen-core slots; memory gate unchanged.'),indent=2));print(json.dumps(dict(queued=len(rows),source_manifest_sha256=sha(source/'source-manifest.json'),root=str(root))))
'''
compile(q,'final_scene263','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
