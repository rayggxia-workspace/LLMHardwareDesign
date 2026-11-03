import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
import hashlib,re,time
queue=b/'dynamic-07/node7';root=b/'r256-composition-359';source=b/'source-358';record=b/'route-selection-102/sready369-reset53-native-aware-placement';assert not record.exists();record.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rows=[]
pin=root/'native-pin-load';assert json.loads((pin/'receipt.json').read_text())['passed'];original=json.loads((pin/'native-pin-load.json').read_text());assert all(any(row['violations'].values())for row in original['placements'])
def add(name,script,args,deps,out,memory=64):
 queue=b/('dynamic-05/node2'if 'placement-3690'in name else'dynamic-02/node3'if 'placement-3691'in name else'dynamic-05/node4'if 'placement-3692'in name else'dynamic-04/node25'if 'placement-3693'in name else'dynamic-07/node7')
 target=queue/'pending'/(name+'.json');assert re.fullmatch('[a-z0-9_-]+',name)and not target.exists()and not out.exists();spec=dict(script=script,source_root=str(source),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args))+['--out',str(out)]);tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(target);rows.append(dict(path=str(target),sha256=sha(target),spec=spec))
places=[]
for seed,gap,density in [(3690,64,0),(3691,256,0),(3692,64,1000000000),(3693,256,1000000000)]:
 out=root/'cap-candidates'/str(seed);places.append(out);args=['--manifest',root/'selected/physical.json','--graph',root/'topology/boundary-graph.json','--pg-wrappers',root/'fixed-pg-wrappers','--cap-lower-bound-only','--pin-aware-placement','--seed',seed,'--channel-gap-um',gap,'--electrical-placement-report',root/'cap-initial/wire-cap-lower-bound.json','--placement-residual-budget',pin/'native-pin-load.json','--placement-capacity-target','.35']
 if density:args+=['--placement-local-density-weight',density,'--placement-local-density-model','exact']
 add('00-d-sready369-placement-'+str(seed),'system_upper.py',args,[pin/'receipt.json'],out)
config=root/'native-cap-config369.json';assert not config.exists();config.write_text(json.dumps(dict(native_sta=str(root/'native-sta'),placements=list(map(str,places))),indent=2))
add('00-e-sready369-native-residual','system_upper.py',['--manifest',root/'selected/physical.json','--graph',root/'topology/boundary-graph.json','--native-cap-residual-config',config],[p/'receipt.json'for p in places]+[root/'native-sta/native-system-audit.json'],root/'native-residual369',32)
add('00-f-sready369-native-pin-load','system_upper.py',['--manifest',root/'selected/physical.json','--graph',root/'topology/boundary-graph.json','--native-pin-load-residual',root/'native-residual369/native-cap-residual.json'],[root/'native-residual369/receipt.json'],root/'native-pin-load369',32)
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,actual_previous_min_pin_receipt_sha256=sha(pin/'receipt.json'),whole_system_qualified=False,reason='All three reset53 initial placements genuinely failed stronger high necessary capacitance by5/1/3 nets. Newactual full native all-endpoint/electrical diagnostic passed. Four independent original fixed-block placement searches now include actual native ground and minimum actual input pin capacitance in finite wire budgets, with/without existing exact local-density penalty. Every original actual cap/native/electrical/geometry/PG/RC300MHz gate unchanged. Same23 accepted reset53 scene types/345 instances/11147 nets. Existing own node2/node3/node4/node25 independent placement slots; dependent residual/input-pin audit uses node7, original4x16 and memory gate, no cancellation/other task changes.'),indent=2));print('queued',len(rows),'independent placements',len(places))
'''
compile(q,'cprogress284','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
