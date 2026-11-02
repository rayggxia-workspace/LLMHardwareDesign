"""Prioritize actual accepted-S composition only after real dependencies pass."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,subprocess,re,time,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');leaf=b/'s-escape-qualified-03/1350';base=b/'s-escape-composition-03/1350';root=b/'route-selection-102/s1350-composition-priority137'
if root.exists():print('Already recorded:',root);raise SystemExit(0)
needed=[leaf/'pg-delivery/receipt.json',base/'topology/boundary-graph.json']
if not all(p.exists()and json.loads(p.read_text()).get('passed')for p in needed):print('ready=false: actual new S PG qualification and topology pending');raise SystemExit(0)
for op in ['physical','function','formal']:
 assert json.loads((b/'s-escape-gates-02/1350'/op/'receipt.json').read_text())['passed']
assert json.loads((b/'s-internal-gates-01/1182/physical/receipt.json').read_text())['passed']is False
job=95119;queue=b/'dynamic-02/node26';state=json.loads((queue/'queue-state.json').read_text())
name='00-b-s-1182-function'
if name not in state['active']:print('No obsolete failed-physical S1182 default function active; no cancellation');raise SystemExit(0)
assert any(n in state['unfinished']for n in ['00-i-s1350-fast137-native-sta','00-i-s1350-fast137-real-programs'])
details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True)
assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-mix26 'in details and 'NodeList=node26 'in details
steps=subprocess.check_output(['scontrol','show','step',str(job),'-o'],universal_newlines=True)
found=[m.groups()for m in re.finditer(r'StepId=('+str(job)+r'\.\d+).*?SrunHost:Pid=(node\d+):(\d+)',steps)]
code="import os,json;d={}"+chr(10)+"for p in "+repr([r[2]for r in found])+":"+chr(10)+" try:"+chr(10)+"  assert os.stat('/proc/'+p).st_uid==10011;d[p]=open('/proc/'+p+'/cmdline','rb').read().decode().split(chr(0))"+chr(10)+" except OSError:pass"+chr(10)+"print(json.dumps(d))"
procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True))
f=queue/'pending'/(name+'.json');spec=json.loads(f.read_text());assert spec['script']=='gates.py'and spec['forecast_gib']==128
expected=spec['args'][spec['args'].index('--out')+1];assert expected==str(b/'s-internal-gates-01/1182/function')and spec['args'][0]=='function'
targets=[]
for step,node,pid in found:
 args=procs.get(pid,[])
 if '--out'in args and args[args.index('--out')+1]==expected and any(x.startswith(str(b/'source-'))and x.endswith('/control_v1/gates.py')for x in args):targets.append(dict(step=step,node=node,pid=pid,args=args))
assert len(targets)==1 and targets[0]['node']=='node26'
root.mkdir();(root/'verified-before.json').write_text(json.dumps(dict(time=time.time(),job=job,job_details=details,queue_state=state,target=targets[0],spec_path=str(f),spec_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),prerequisites={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in needed},reason='Prioritize actual fully PG-qualified S1350 composition. S1182 final physical already failed, so its obsolete default aggregate function cannot qualify that candidate. Stop only this exact own redundant compile; retain all specifications, partial artifacts, actual physical failure and native DRC work. Not a hardware function failure. All original memory and sixteen-CPU admission rules unchanged.'),indent=2))
subprocess.run(['scancel',targets[0]['step']],check=True)
(root/'cancelled.json').write_text(json.dumps(dict(time=time.time(),steps=[targets[0]['step']])))
print('Stopped exact obsolete failed-physical S1182 default compilation:',targets[0]['step'])
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
