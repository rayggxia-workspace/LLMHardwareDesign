"""Release one own redundant sequential PG attempt after actual main PG acceptance."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,subprocess,re,time,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');qualified=b/'s-escape-qualified-03/1350/pg-delivery';root=b/'route-selection-102/s1350-pg-default-retire137';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if root.exists():print('Already recorded',root);raise SystemExit(0)
p=qualified/'receipt.json'
if not p.exists()or not json.loads(p.read_text()).get('passed'):print('ready=false: actual main PG delivery not accepted');raise SystemExit(0)
r=json.loads(p.read_text());d=json.loads((qualified/'delivery.json').read_text());assert r['native_leaf_qualified']and d['passed']and d['native_leaf_accepted']and r['outputs']['delivery.json']==sha(qualified/'delivery.json')and d['S_internal_drive']['all_four_gates_fresh']
for label in ['fresh_physical_receipt','fresh_timing_receipt','fixed_pg_receipt']:
 f=Path(d[label]);assert sha(f)==d[label+'_sha256']and json.loads(f.read_text())['passed']
job=95391;queue=b/'dynamic-05/node4';state=json.loads((queue/'queue-state.json').read_text());name='00-d-s1350-wrapper136'
if name not in state['active']:print('Redundant sequential PG step no longer active; nothing stopped');raise SystemExit(0)
details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-smem4 'in details and 'NodeList=node4 'in details
text=subprocess.check_output(['scontrol','show','step',str(job),'-o'],universal_newlines=True);found=[m.groups()for m in re.finditer(r'StepId=('+str(job)+r'\.\d+).*?SrunHost:Pid=(node\d+):(\d+)',text)]
code="import os,json;d={}"+chr(10)+"for p in "+repr([r[2]for r in found])+":"+chr(10)+" try:"+chr(10)+"  assert os.stat('/proc/'+p).st_uid==10011;d[p]=open('/proc/'+p+'/cmdline','rb').read().decode().split(chr(0))"+chr(10)+" except OSError:pass"+chr(10)+"print(json.dumps(d))"
procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));f=queue/'pending'/(name+'.json');spec=json.loads(f.read_text());assert spec['script']=='pg_fixed_access.py'and spec['forecast_gib']==64
expected=spec['args'][spec['args'].index('--out')+1];assert expected==str(b/'s-escape-qualified-02/1350/pg-wrapper')
targets=[]
for step,node,pid in found:
 args=procs.get(pid,[])
 if '--out'in args and args[args.index('--out')+1]==expected and any(x.startswith(str(b/'source-'))and x.endswith('/control_v1/pg_fixed_access.py')for x in args):targets.append(dict(step=step,node=node,pid=pid,args=args))
assert len(targets)==1 and targets[0]['node']=='node4'
root.mkdir();(root/'verified-before.json').write_text(json.dumps(dict(time=time.time(),job_details=details,queue_state=state,target=targets[0],spec_path=str(f),spec_sha256=sha(f),accepted_pg_receipt=dict(path=str(p),sha256=sha(p)),accepted_delivery=dict(path=str(qualified/'delivery.json'),sha256=sha(qualified/'delivery.json')),reason='Main same-S native and fixed-PG chain actually fully qualified. Release only exact own now-redundant sequential PG construction/full-deck attempt to free independent-task capacity for actual upper routing. Original specifications, all partial outputs/logs and waiting dependencies retained. No qualification inferred for this backup attempt and no hardware failure declared. Parent allocation, all other tasks and all acceptance/memory rules unchanged.'),indent=2))
subprocess.run(['scancel',targets[0]['step']],check=True);(root/'cancelled.json').write_text(json.dumps(dict(time=time.time(),steps=[targets[0]['step']])));print('Stopped exact redundant own PG attempt',targets[0]['step'])
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
