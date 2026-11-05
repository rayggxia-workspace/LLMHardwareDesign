"""Six new native blocks, each full original seven-stage backend chain."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-350';record=b/'route-selection-102/sready353-reset53-native';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();m=json.loads((source/'source-manifest.json').read_text());assert m['commit']=='1d9605d95374a2b2576840f3a80e140b5b296af4'
for name,digest in [('r_stream_local.sv','dc41d52eb88efe6cc592683b788d09da980c1c01e779ab54db9fb647d730363d'),('r_state_store.sv','7b50c3abae20587ac49726fed375da6390fc1d4a260ae299939fc6725dae1d40')]:assert sha(source/'project/rtl/r_local_state'/name)==digest
rows=[]
def add(node,name,script,args,deps,out,memory):
 family='dynamic-07';p=b/family/('node'+str(node))/'pending'/(name+'.json');assert not p.exists()and not out.exists()
 spec=dict(script=script,source_root=str(source),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args))+['--out',str(out)])
 temp=p.with_suffix('.tmp');temp.write_text(json.dumps(spec));temp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
for number,node,model in [(3530,7,'reset_r53')]:
 root=b/'r256-native-353'/str(number);raw=root/'native';g=root/'gates'
 add(node,'00-a-sready353-native-'+str(number),'run.py',['--model',model,'--physical','--strong-output-drivers'],[],raw,64 if model=='c_r8' else 32)
 common=['--producer',raw,'--source-root',source]
 add(node,'00-b-sready353-seal-'+str(number),'gates.py',['seal',*common],[raw/'receipt.json'],g/'sealed',16)
 for op,mem in [('physical',64),('drc',32),('function',32),('formal',64)]:
  deps=[g/'sealed/receipt.json']+([g/'function/receipt.json']if op=='formal'else[])
  add(node,'00-c-sready353-'+op+'-'+str(number),'gates.py',[op,*common,'--sealed',g/'sealed','--gates',g],deps,g/op,mem)
 add(node,'00-d-sready353-deliver-'+str(number),'gates.py',['deliver',*common,'--sealed',g/'sealed','--gates',g],[g/op/'receipt.json'for op in ['physical','drc','function','formal']],g/'deliver',32)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,source_commit=m['commit'],reused_pr=168,reused_commit='55f2553bdacbca971b1505a11675a0b1eb12fcad',whole_system_qualified=False,scope='Reuse already99/99 tested R256 implementation/programs, no new R1024 ABI. One necessary repaired physical reset distribution:53 outputs from the same single registered reset state,28 original leaves plus25 separate Link8 banks. Originalfour candidate high-RC lower bound proves reset23 infeasible; no thresholds relaxed. Existing main six and qualified R/control blocks reused. Each original RTL3initial/mapping/P&R plus sealed physical/complete DRC/final-cell3initial/strict formal/delivery, seven tasks each. All states belong fixed M1-M10 native blocks. Old235-instance searches and qualified21 packages remain baseline only. Existing own node7 four16CPU slots, unchanged memory admission, no new node/R166/PR168/foreign worktree or job modified. No hardware qualification until actual original gates pass.'),indent=2))
print(json.dumps(dict(queued=len(rows),record=str(record),new_native_blocks=1,whole_system_qualified=False)))
'''
compile(q,'r256_native_queue229','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
