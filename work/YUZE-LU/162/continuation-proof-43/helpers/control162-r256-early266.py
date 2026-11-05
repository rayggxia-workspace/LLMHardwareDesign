import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-early-electrical-266';record=b/'route-selection-102/sready266-early-electrical';assert not record.exists();record.mkdir();rows=[];source=b/'source-258';inputs=b/'r256-composition-259/function-inputs';top=b/'r256-composition-259/topology';common=['--manifest',inputs/'physical.json','--graph',top/'boundary-graph.json','--cap-lower-bound-only','--pin-aware-placement']
def add(name,args,deps,out):
 p=b/'dynamic-06/node7/pending'/(name+'.json');assert not p.exists()and not out.exists();s=dict(script='system_upper.py',source_root=str(source),forecast_gib=32,requires=list(map(str,deps)),args=list(map(str,args))+['--out',str(out)]);t=p.with_suffix('.tmp');t.write_text(json.dumps(s));t.rename(p);rows.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),spec=s))
add('00-c-sready266-R-early-cap',common+['--seed',2660,'--channel-gap-um',256],[top/'receipt.json',inputs/'receipt.json'],root/'initial')
add('00-d-sready266-R-early-placement',common+['--seed',2661,'--channel-gap-um',64,'--electrical-placement-report',root/'initial/wire-cap-lower-bound.json','--placement-capacity-target','.35'],[root/'initial/receipt.json'],root/'optimized')
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,native_leaf_qualified=False,scope='Failure-only actual output/shortest-wire necessary diagnostics, independent of remaining C/R PG. Exact actual candidate pins/RTL and R rigid phase retained. No PG/source rebind or final-scene qualification; final263 all gates still required. Existing idle own16CPU slot and unchanged memory gate.'),indent=2));print(json.dumps(dict(queued=len(rows))))
'''
compile(q,'early266','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
