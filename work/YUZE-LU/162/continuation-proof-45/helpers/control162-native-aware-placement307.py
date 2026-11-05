import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
import hashlib,re,time
queue=b/'dynamic-07/node7';root=b/'r256-composition-274';source=b/'source-305';record=b/'route-selection-102/sready307-native-aware-placement';assert not record.exists();record.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rows=[]
pin=root/'native-pin-load302';assert json.loads((pin/'receipt.json').read_text())['passed'];original=json.loads((pin/'native-pin-load.json').read_text());assert all(any(row['violations'].values())for row in original['placements'])
def add(name,script,args,deps,out,memory=64):
 target=queue/'pending'/(name+'.json');assert re.fullmatch('[a-z0-9_-]+',name)and not target.exists()and not out.exists();spec=dict(script=script,source_root=str(source),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args))+['--out',str(out)]);tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(target);rows.append(dict(path=str(target),sha256=sha(target),spec=spec))
places=[]
for seed,gap,density in [(3070,64,0),(3071,256,0),(3072,64,1000000000),(3073,256,1000000000)]:
 out=root/'cap-candidates'/str(seed);places.append(out);args=['--manifest',root/'selected/physical.json','--graph',root/'topology/boundary-graph.json','--pg-wrappers',root/'fixed-pg-wrappers','--cap-lower-bound-only','--pin-aware-placement','--seed',seed,'--channel-gap-um',gap,'--electrical-placement-report',root/'cap-initial/wire-cap-lower-bound.json','--placement-residual-budget',pin/'native-pin-load.json','--placement-capacity-target','.35']
 if density:args+=['--placement-local-density-weight',density,'--placement-local-density-model','exact']
 add('00-d-sready307-placement-'+str(seed),'system_upper.py',args,[pin/'receipt.json'],out)
config=root/'native-cap-config307.json';assert not config.exists();config.write_text(json.dumps(dict(native_sta=str(root/'native-sta'),placements=list(map(str,places))),indent=2))
add('00-e-sready307-native-residual','system_upper.py',['--manifest',root/'selected/physical.json','--graph',root/'topology/boundary-graph.json','--native-cap-residual-config',config],[p/'receipt.json'for p in places]+[root/'native-sta/native-system-audit.json'],root/'native-residual307',32)
add('00-f-sready307-native-pin-load','system_upper.py',['--manifest',root/'selected/physical.json','--graph',root/'topology/boundary-graph.json','--native-pin-load-residual',root/'native-residual307/native-cap-residual.json'],[root/'native-residual307/receipt.json'],root/'native-pin-load307',32)
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,actual_previous_min_pin_receipt_sha256=sha(pin/'receipt.json'),whole_system_qualified=False,reason='All three old placements genuinely failed high necessary capacitance by1/2/8 nets; two near limits, chiefly reset branches with169/206 physical sinks. Four independent original fixed-block placement searches now include actual native ground and minimum actual input pin capacitance in finite wire budgets, with/without existing exact local-density penalty. Every original actual cap/native/electrical/geometry/PG/RC300MHz gate unchanged. Same23 accepted types/345 instances/11122 nets. Existing node7 slots, original4x16 and memory gate, no cancellation/other task changes.'),indent=2));print('queued',len(rows),'independent placements',len(places))
'''
compile(q,'cprogress284','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
