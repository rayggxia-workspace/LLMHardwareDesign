import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-258';root=b/'r256-composition-259';record=b/'route-selection-102/sready259-r256-final-function';assert not record.exists();rows=[]
def add(name,script,args,deps,out,memory):
 p=b/'dynamic-06/node7/pending'/(name+'.json');assert not p.exists()and not out.exists()
 spec=dict(script=script,source_root=str(source),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args))+['--out',str(out)])
 p.write_text(json.dumps(spec));rows.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),spec=spec))
inputs=root/'function-inputs';top=root/'topology'
deps=[b/'r256-native-237/2371/gates/function/receipt.json',b/'r256-native-reuse-251/receipt.json']+[b/('r256-fixed-pg-235/'+str(n)+'/delivery/receipt.json')for n in [2292,2294,2295]]+[b/'r256-fixed-pg-246/2333/delivery/receipt.json',b/'r256-fixed-pg-254/2430/delivery/receipt.json']
add('00-a-sready259-function-inputs','run.py',['--model','r256_function_inputs','--verify-only'],deps,inputs,32)
args=['--manifest',inputs/'physical.json','--r256-scene']
for name in ['macro_1','macro_2','macro_3','macro_4','macro_t','macro_r']:args+=['--link-native-output',name]
for name in ['s_port:dout','controller:task_data','controller:task_last']:args+=['--split-output-fanout',name]
add('00-b-sready259-r256-topology','topology.py',args,[inputs/'receipt.json'],top,32)
add('00-c-sready259-eight-final-programs','final_composition.py',['--manifest',inputs/'functions.json','--physical',inputs/'physical.json','--topology',top/'topology.json','--graph',top/'boundary-graph.json','--hierarchical'],[inputs/'receipt.json',top/'receipt.json'],root/'function',128)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,scope='Overlap actual eight-program final-cell composition with remaining independent C full GDS DRC/fixed PG and R new PG. Five new configs already fixed-PG accepted; C actual finished physical/full-view function passed; original R256 standalone qualification/full ODB view exact. Final joint collector must still bind all genuine final physical/PG/three RC/300MHz gates and compare exact whole topology and every actual final full-view SHA. Input construction/function success cannot grant physical qualification.'),indent=2));print(json.dumps(dict(queued=len(rows))))
'''
compile(q,'r256_function_queue259','exec')
print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=35).decode())
