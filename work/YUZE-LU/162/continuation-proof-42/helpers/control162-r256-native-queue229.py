"""Six new native blocks, each full original seven-stage backend chain."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-228';record=b/'route-selection-102/sready229-r256-native';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();m=json.loads((source/'source-manifest.json').read_text());assert m['commit']=='87d73be1c1dec04c273d9552f7a098a84ecb2a05'
for name,digest in [('r_stream_local.sv','dc41d52eb88efe6cc592683b788d09da980c1c01e779ab54db9fb647d730363d'),('r_state_store.sv','7b50c3abae20587ac49726fed375da6390fc1d4a260ae299939fc6725dae1d40')]:assert sha(source/'project/rtl/r_local_state'/name)==digest
for name in ['system_geometry.py','system_accept.py','system_sta.py','system_pg_audit.py','system_native_audit.py','upper_rc_network.py','native_stitch.py','boundary_links.py']:
 assert sha(source/'project/experiments/control_v1'/name)==sha(b/'source-220/project/experiments/control_v1'/name)
rows=[]
def add(node,name,script,args,deps,out,memory):
 family='dynamic-02';p=b/family/('node'+str(node))/'pending'/(name+'.json');assert not p.exists()and not out.exists()
 spec=dict(script=script,source_root=str(source),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args))+['--out',str(out)])
 temp=p.with_suffix('.tmp');temp.write_text(json.dumps(spec));temp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
for number,node,model in [(2290,7,'adapter_r'),(2291,7,'c_r8'),(2292,7,'route_r8'),(2293,26,'s_arbiter_r7'),(2294,26,'status_r8'),(2295,26,'reset_r28')]:
 root=b/'r256-native-229'/str(number);raw=root/'native';g=root/'gates'
 add(node,'00-a-sready229-native-'+str(number),'run.py',['--model',model,'--physical','--strong-output-drivers'],[],raw,64 if model=='c_r8' else 32)
 common=['--producer',raw,'--source-root',source]
 add(node,'00-b-sready229-seal-'+str(number),'gates.py',['seal',*common],[raw/'receipt.json'],g/'sealed',16)
 for op,mem in [('physical',64),('drc',32),('function',32),('formal',64)]:
  deps=[g/'sealed/receipt.json']+([g/'function/receipt.json']if op=='formal'else[])
  add(node,'00-c-sready229-'+op+'-'+str(number),'gates.py',[op,*common,'--sealed',g/'sealed','--gates',g],deps,g/op,mem)
 add(node,'00-d-sready229-deliver-'+str(number),'gates.py',['deliver',*common,'--sealed',g/'sealed','--gates',g],[g/op/'receipt.json'for op in ['physical','drc','function','formal']],g/'deliver',32)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,source_commit=m['commit'],reused_pr=168,reused_commit='55f2553bdacbca971b1505a11675a0b1eb12fcad',whole_system_qualified=False,scope='Reuse already99/99 tested R256 implementation/programs, no new R1024 ABI. Six necessary new physical blocks: R adapter, C8, route8, arbiter7, status8, reset28. Each original RTL3initial/mapping/P&R plus sealed physical/complete DRC/final-cell3initial/strict formal/delivery, seven tasks each. All states belong fixed M1-M10 native blocks. Old235-instance searches and qualified21 packages remain baseline only. Existing own node7 four16CPU slots/node26 six16CPU slots, unchanged memory admission, no new node/R166/PR168/foreign worktree or job modified. No hardware qualification until actual original gates pass.'),indent=2))
print(json.dumps(dict(queued=len(rows),record=str(record),new_native_blocks=6,whole_system_qualified=False)))
'''
compile(q,'r256_native_queue229','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
