from pathlib import Path
import json,time,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-451';old=b/'r256-composition-359';root=b/'r256-composition-453';record=b/'route-selection-102/sready453-unused-link-load';assert not root.exists()and not record.exists();root.mkdir();record.mkdir();rows=[];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
sel=old/'selected';manifest=sel/'physical.json';top=root/'topology';graph=top/'boundary-graph.json'
def add(queue,name,script,args,deps,out,memory=32):
 p=b/queue/'pending'/(name+'.json');assert not p.exists()and not out.exists();spec=dict(script=script,source_root=str(source),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args))+['--out',str(out)]);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
reg=root/'contract';add('dynamic-05/node2','00-a-sready453-padding-contract','run.py',['--model','r256_contract','--verify-only'],[],reg)
args=['--manifest',manifest,'--r256-scene','--link-padding-local-reset']
for name in ['macro_1','macro_2','macro_3','macro_4','macro_t','macro_r']:args+=['--link-native-output',name]
for name in ['s_port:dout','controller:task_data','controller:task_last']:args+=['--split-output-fanout',name]
add('dynamic-05/node2','00-b-sready453-padding-topology','topology.py',args,[reg/'receipt.json',sel/'receipt.json'],top)
add('dynamic-05/node2','00-c-sready453-native-sta','system_sta.py',['--manifest',manifest,'--functional-views',sel/'functions.json','--topology',top/'topology.json','--graph',graph,'--stitch-native-access','--audit-native-coverage'],[top/'receipt.json'],root/'native-sta',128)
add('dynamic-04/node25','00-c-sready453-final-programs','final_composition.py',['--manifest',sel/'functions.json','--physical',manifest,'--graph',graph,'--topology',top/'topology.json','--hierarchical'],[top/'receipt.json'],root/'function',128)
place=root/'cap-initial';args=['--manifest',manifest,'--graph',graph,'--pg-wrappers',old/'fixed-pg-wrappers','--cap-lower-bound-only','--pin-aware-placement','--seed',4530,'--channel-gap-um',64]
add('dynamic-04/node25','00-c-sready453-initial-placement','system_upper.py',args,[top/'receipt.json'],place)
config=root/'native-cap-config.json';config.write_text(json.dumps(dict(native_sta=str(root/'native-sta'),placements=[str(place)]),indent=2));res=root/'native-residual';pin=root/'native-pin-load'
add('dynamic-04/node25','00-d-sready453-native-residual','system_upper.py',['--manifest',manifest,'--graph',graph,'--native-cap-residual-config',config],[place/'receipt.json',root/'native-sta/native-system-audit.json'],res)
add('dynamic-04/node25','00-e-sready453-native-pin-load','system_upper.py',['--manifest',manifest,'--graph',graph,'--native-pin-load-residual',res/'native-cap-residual.json'],[res/'receipt.json'],pin)
gates={}
for name in ['system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py']:
 p=source/'project/experiments/control_v1'/name;assert sha(p)==sha(b/'source-435/project/experiments/control_v1'/name);gates[name]=sha(p)
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,source_manifest_sha256=sha(source/'source-manifest.json'),unchanged_actual_acceptance_source_sha256=gates,whole_system_qualified=False,scope='Candidate453 only. Reuse all23 qualified fixed macros unchanged, all345 instances/state owners retained. Actual450 diagnosis267 unused Link8 input pins currently load payload drivers; move only proven unconsumed lanes to their existing reset53 bank. Added reset input load is real and counted exactly, no hidden active upper logic. New actual contraction/consuming-data regression, full topology, current real programs, native full coverage and ground/minimum-pin bounds mandatory; no old scene qualification inheritance. Original359 and all complete route chains retained. Will continue actual placements and full geometry/PG/low-base-high300MHz/function/joint gates; no candidate success yet. Original memory gate and own4x16/6x16 dynamic slots unchanged.'),indent=2));print(json.dumps(dict(queued=len(rows),root=str(root))))
