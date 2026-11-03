"""Verify and release only exact own1462 child after both diagnostics queued."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,subprocess,re,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391';record=b/'route-selection-102/sready201-complete-path-refill';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();new=b/'route-selection-102/sready200-complete-path-diagnostic/tasks.json';nr=json.loads(new.read_text());assert len(nr['tasks'])==2
for row in nr['tasks']:
 assert sha(row['path'])==row['sha256']and row['spec']['source_root']==str(b/'source-199')and row['spec']['script']=='router_conflict_snapshot.py'
 assert sha(row['config'])==row['config_sha256']
queue=b/'dynamic-04/node25';name='00-k-sready140-route-1462';old=queue/'pending'/(name+'.json');s=json.loads(old.read_text());a=s['args'];out=a[a.index('--out')+1]
assert s['source_root']==str(b/'source-142')and s['script']=='system_upper.py'and out==str(c/'upper-candidates/1462/route')
assert a[a.index('--route-trials')+1]=='16'and a[a.index('--route-heuristic-weight')+1]=='16'and a[a.index('--route-congestion-scale')+1]=='1'
state=json.loads((queue/'queue-state.json').read_text());assert name in state['active']and len(state['active'])==6
job=95204;details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and'JobName=yzl-ctl162-'in details and'NodeList=node25 'in details
steps=subprocess.check_output(['scontrol','show','step',str(job),'-o'],universal_newlines=True);found=[m.groups()for m in re.finditer(r'StepId=('+str(job)+r'\.\d+).*?SrunHost:Pid=(node\d+):(\d+)',steps)]
code="import os,json;d={}"+chr(10)+"for p in "+repr([r[2]for r in found])+":"+chr(10)+" try:"+chr(10)+"  assert os.stat('/proc/'+p).st_uid==10011;d[p]=open('/proc/'+p+'/cmdline','rb').read().decode().split(chr(0))"+chr(10)+" except OSError:pass"+chr(10)+"print(json.dumps(d))"
procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));targets=[]
for step,host,pid in found:
 cmd=procs.get(pid,[])
 if '--out'in cmd and cmd[cmd.index('--out')+1]==out and str(b/'source-142/project/experiments/control_v1/system_upper.py')in cmd:targets.append(dict(step=step,host=host,pid=pid,command=cmd))
assert len(targets)==1 and targets[0]['host']=='node25'
log=Path(out)/'trial-0/router.log';raw=log.read_bytes();rounds=[json.loads(l)for l in raw.decode().splitlines()if l.startswith('{')and'"conflict_nodes"'in l];assert rounds and rounds[-1]['conflict_nodes']>0
record.mkdir();(record/'verified-before.json').write_text(json.dumps(dict(time=time.time(),target=targets[0],old_spec=str(old),old_spec_sha256=sha(old),old_log=dict(path=str(log),bytes=len(raw),prefix_sha256=hashlib.sha256(raw).hexdigest(),last_completed_rounds=rounds[-3:]),replacement_record=str(new),replacement_record_sha256=sha(new),queue_state=state,job_details=details,reason='Complete original16 full-path replays needed to distinguish local pin escape from cross-cluster congestion. Both exact source-bound diagnostic stages queued first. Retire only this verified old duplicate own child; retain all old specs/partials, other controls, eight parents, R/foreign tasks. One existing c96 16CPU slot, same six-slot dynamic queue and original memory guard. Incomplete search retirement, not final physical failure.'),indent=2))
subprocess.run(['scancel',targets[0]['step']],check=True)
(record/'cancelled.json').write_text(json.dumps(dict(time=time.time(),step=targets[0]['step'])))
print(json.dumps(dict(retired_exact_step=targets[0]['step'],last_actual_round=rounds[-1],whole_system_qualified=False)))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
