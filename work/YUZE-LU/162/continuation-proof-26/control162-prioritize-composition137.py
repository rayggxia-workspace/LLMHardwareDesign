"""Prioritize actual accepted-S composition only after real dependencies pass."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,subprocess,re,time,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');leaf=b/'s-escape-qualified-03/1350';base=b/'s-escape-composition-03/1350';root=b/'route-selection-102/s1350-composition-priority137-node26'
if root.exists():print('Already recorded:',root);raise SystemExit(0)
needed=[leaf/'pg-delivery/receipt.json',base/'topology/boundary-graph.json']
if not all(p.exists()and json.loads(p.read_text()).get('passed')for p in needed):print('ready=false: actual new S PG qualification and topology pending');raise SystemExit(0)
for op in ['physical','function','formal']:
 assert json.loads((b/'s-escape-gates-02/1350'/op/'receipt.json').read_text())['passed']
failed=b/'s-final-evidence-02/1183/physical';failed_receipt=json.loads((failed/'receipt.json').read_text());failed_report=json.loads((failed/'five-macro-physical.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert failed_receipt['passed']is False and failed_report['passed']is False and failed_report['checks']['all_real_timed_endpoints']is False
assert failed_receipt['outputs']['five-macro-physical.json']==sha(failed/'five-macro-physical.json')
assert failed_receipt['producer']==str(b/'s-internal-drive-02/candidate-1183')
prior=b/'s-internal-gates-01/1183/sealed';actual=Path(failed_report['source']);old_seal=json.loads((prior/'receipt.json').read_text());checked_seal=json.loads((actual/'receipt.json').read_text())
assert failed_report['source_receipt_sha256']==sha(actual/'receipt.json')
assert old_seal['producer_receipt_sha256']==checked_seal['producer_receipt_sha256']==failed_receipt['producer_receipt_sha256']
physical_bindings={}
for suffix in ['v','sdc','def','odb','spef']:
 name='flow/results/nangate45/bv1_block_feed_s_macro/base/6_final.'+suffix
 assert old_seal['outputs'][name]==checked_seal['outputs'][name]
 assert(prior/name).stat().st_size==(actual/name).stat().st_size
 physical_bindings[name]=old_seal['outputs'][name]

job=95119;queue=b/'dynamic-02/node26';state=json.loads((queue/'queue-state.json').read_text())
name='00-b-s-1183-formal'
if name not in state['active']:print('No obsolete failed-physical S1183 formal active; no cancellation');raise SystemExit(0)
assert any(n in state['unfinished']for n in ['00-i-s1350-fast137-native-sta','00-i-s1350-fast137-real-programs'])
rejected=[r for r in state['memory_admissions']if r['name']=='00-i-s1350-fast137-real-programs'and not r['admitted']]
if not rejected:print('No current composition memory rejection; preserve old active work');raise SystemExit(0)
assert rejected[0]['required_bytes']>rejected[0]['available_bytes']
details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True)
assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-mix26 'in details and 'NodeList=node26 'in details
steps=subprocess.check_output(['scontrol','show','step',str(job),'-o'],universal_newlines=True)
found=[m.groups()for m in re.finditer(r'StepId=('+str(job)+r'\.\d+).*?SrunHost:Pid=(node\d+):(\d+)',steps)]
code="import os,json;d={}"+chr(10)+"for p in "+repr([r[2]for r in found])+":"+chr(10)+" try:"+chr(10)+"  assert os.stat('/proc/'+p).st_uid==10011;d[p]=open('/proc/'+p+'/cmdline','rb').read().decode().split(chr(0))"+chr(10)+" except OSError:pass"+chr(10)+"print(json.dumps(d))"
procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True))
f=queue/'pending'/(name+'.json');spec=json.loads(f.read_text());assert spec['script']=='gates.py'and spec['forecast_gib']==128
expected=spec['args'][spec['args'].index('--out')+1];assert expected==str(b/'s-internal-gates-01/1183/formal')and spec['args'][0]=='formal'
targets=[]
for step,node,pid in found:
 args=procs.get(pid,[])
 if '--out'in args and args[args.index('--out')+1]==expected and any(x.startswith(str(b/'source-'))and x.endswith('/control_v1/gates.py')for x in args):targets.append(dict(step=step,node=node,pid=pid,args=args))
assert len(targets)==1 and targets[0]['node']=='node26'
root.mkdir();(root/'verified-before.json').write_text(json.dumps(dict(time=time.time(),job=job,job_details=details,queue_state=state,failed_physical_receipt=dict(path=str(failed/'receipt.json'),sha256=sha(failed/'receipt.json')),failed_physical_report=dict(path=str(failed/'five-macro-physical.json'),sha256=sha(failed/'five-macro-physical.json')),same_five_sealed_physical_file_sha256=physical_bindings,target=targets[0],spec_path=str(f),spec_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),prerequisites={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in needed},reason='Prioritize actual fully PG-qualified S1350 composition. S1183 exact same five-file final physical independently failed (s-final-evidence-02), so its obsolete redundant formal cannot qualify that candidate. Stop only this exact own redundant formal attempt; retain all specifications, partial artifacts, actual physical failure and native DRC work. Not a hardware formal failure. All original memory and sixteen-CPU admission rules unchanged.'),indent=2))
subprocess.run(['scancel',targets[0]['step']],check=True)
(root/'cancelled.json').write_text(json.dumps(dict(time=time.time(),steps=[targets[0]['step']])))
print('Stopped exact obsolete failed-physical S1183 formal attempt:',targets[0]['step'])
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
