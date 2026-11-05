import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-140';record=b/'route-selection-102/s-ready-qualified-composition140.json';assert not record.exists();oldbase=b/'s-escape-composition-03/1350';old=json.loads((oldbase/'selected/physical.json').read_text());rows=[]
def add(node,name,script,args,deps,out,memory=32):
 family=5 if node in (2,4)else 3 if node==5 else 2
 f=b/('dynamic-%02d'%family)/('node'+str(node))/'pending'/(name+'.json');assert f.parent.is_dir()and not f.exists()and not out.exists()
 spec=dict(script=script,source_root=str(source),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args+['--out',out])));tmp=f.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(f);rows.append(dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),spec=spec))
for seed,node,native_node,function_node in [(1390,2,6,7),(1391,4,3,5)]:
 leaf=b/'s-ready-qualified-01'/str(seed);base=b/'s-ready-composition-01'/str(seed);assert not leaf.exists()and not base.exists();leaf.mkdir(parents=True);base.mkdir(parents=True)
 selected_native=leaf/'selected-native';native=b/'s-ready-gates-01'/str(seed)/'deliver'
 add(node,'00-f-sready140-native-select-'+str(seed),'select_leaves.py',['--physical',oldbase/'selected/physical.json','--functions',oldbase/'selected/functions.json','--replacement',native],[native/'receipt.json'],selected_native,16)
 wrapper=leaf/'pg-wrapper';physical=leaf/'pg-physical';timing=leaf/'pg-timing';delivery=leaf/'pg-delivery'
 add(node,'00-g-sready140-pg-wrapper-'+str(seed),'pg_fixed_access.py',['--manifest',selected_native/'physical.json','--leaf','control_adapter_s'],[selected_native/'receipt.json'],wrapper,32)
 common=['--manifest',selected_native/'physical.json','--leaf','control_adapter_s','--wrapper',wrapper]
 add(node,'00-h-sready140-pg-physical-'+str(seed),'pg_fixed_timing.py',common+['--physical-only'],[wrapper/'receipt.json'],physical,32)
 add(node,'00-h-sready140-pg-timing-'+str(seed),'pg_fixed_timing.py',common,[wrapper/'receipt.json'],timing,32)
 add(node,'00-i-sready140-pg-deliver-'+str(seed),'pg_fixed_timing.py',common+['--deliver','--physical-check',physical,'--timing-check',timing],[physical/'receipt.json',timing/'receipt.json'],delivery,32)
 sets=base/'qualified-pg-leaves';wrappers=base/'fixed-pg-wrappers';sets.mkdir();wrappers.mkdir();bindings={}
 for top,row in old['leaves'].items():
  if top=='control_adapter_s':d=delivery;w=wrapper
  else:
   d=Path(row['fixed_pg_delivery']['path']).parent;r=json.loads((d/'delivery.json').read_text());assert r['passed']and r['native_leaf_accepted'];w=Path(r['fixed_pg_receipt']).parent;bindings[str(d/'delivery.json')]=hashlib.sha256((d/'delivery.json').read_bytes()).hexdigest()
  (sets/top).symlink_to(d);(wrappers/top).symlink_to(w)
 (base/'reused-leaves.json').write_text(json.dumps(dict(bindings=bindings,new_adapter=str(delivery),source_commit='0f6c47b9bba177dbf2ac1f223a02dd22a7f6b33f',scope='Exact20 qualified fixedPG types including accepted internal-drive S1350. Only S adapter changes and must pass all new gates. Future paths not accepted until actual receipts.'),indent=2))
 selected=base/'selected';topology=base/'topology'
 add(node,'00-j-sready140-pg-select-'+str(seed),'select_leaves.py',['--physical',selected_native/'physical.json','--functions',selected_native/'functions.json','--pg-deliveries',sets],[delivery/'receipt.json'],selected,16)
 args=['--manifest',selected/'physical.json']
 for n in ['macro_1','macro_2','macro_3','macro_4','macro_t']:args+=['--link-native-output',n]
 for n in ['s_port:dout','controller:task_data','controller:task_last']:args+=['--split-output-fanout',n]
 add(node,'00-k-sready140-topology-'+str(seed),'topology.py',args,[selected/'receipt.json'],topology,16)
 common=['--manifest',selected/'physical.json','--functional-views',selected/'functions.json','--topology',topology/'topology.json','--graph',topology/'boundary-graph.json']
 add(native_node,'00-l-sready140-native-sta-'+str(seed),'system_sta.py',common+['--stitch-native-access','--audit-native-coverage'],[topology/'receipt.json'],base/'native-sta',128)
 add(function_node,'00-l-sready140-real-programs-'+str(seed),'final_composition.py',['--manifest',selected/'functions.json','--physical',selected/'physical.json','--topology',topology/'topology.json','--graph',topology/'boundary-graph.json','--hierarchical'],[topology/'receipt.json'],base/'final-composition',128)
 args=['--manifest',selected/'physical.json','--graph',topology/'boundary-graph.json','--pg-wrappers',wrappers,'--cap-lower-bound-only','--pin-aware-placement']
 add(node,'00-l-sready140-cap-initial-'+str(seed),'system_upper.py',args+['--seed','1352','--channel-gap-um','256'],[topology/'receipt.json'],base/'cap-initial')
 for place,gap in [(1404,64),(1405,256)]:
  out=base/'cap-candidates'/str(place)
  add(node,'00-m-sready140-cap-'+str(seed)+'-'+str(place),'system_upper.py',args+['--electrical-placement-report',base/'cap-initial/wire-cap-lower-bound.json','--seed',str(place),'--channel-gap-um',str(gap)],[base/'cap-initial/receipt.json'],out)
 config=b/'route-selection-102'/('sready140-residual-'+str(seed)+'.json');assert not config.exists();config.write_text(json.dumps(dict(native_sta=str(base/'native-sta'),placements=[str(base/'cap-candidates'/str(p))for p in [1404,1405]]),indent=2))
 add(node,'00-n-sready140-residual-'+str(seed),'system_upper.py',['--manifest',selected/'physical.json','--graph',topology/'boundary-graph.json','--native-cap-residual-config',config],[base/'native-sta/native-system-audit.json',*[base/'cap-candidates'/str(p)/'receipt.json'for p in [1404,1405]]],base/'native-cap-residual')
record.write_text(json.dumps(dict(time=time.time(),tasks=rows,scope='Fresh adapter native/fixedPG and actual new topology/functions/STA/capacitance. Twenty other exact qualified blocks including S1350 preserved. No qualification from pending work, no modification of old queued specs or old evidence.'),indent=2));print('Appended',len(rows),'tasks;20 exact reused types;2 independent full chains',record)
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
