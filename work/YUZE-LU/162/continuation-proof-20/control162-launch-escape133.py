import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,subprocess,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-133';plan=b/'route-selection-102/s-escape-repair-source133.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
data=json.loads(plan.read_text());assert data['tasks']and sha(source/'source-manifest.json')==data['source_manifest_sha256']
node=2;oldjob=95097;queue=b/'dynamic-05/node2';root=b/'route-selection-102/s-escape-memory133-node2';assert not root.exists()
for count in [48,64]:assert (b/('s-reset-probe-06/'+str(count))/'receipt.json').exists()
oldqueue=b/'dynamic-02/node2';state=json.loads((oldqueue/'queue-state.json').read_text());oldspecs=[]
for name in state['active']:
 p=oldqueue/'pending'/(name+'.json');spec=json.loads(p.read_text());assert spec['script']=='system_upper.py'
 assert spec['args'][spec['args'].index('--graph')+1]==str(b/'composition-drive-pg-01/topology/boundary-graph.json')
 oldspecs.append(dict(name=name,path=str(p),sha256=sha(p),spec=spec))
details=subprocess.check_output(['scontrol','show','job',str(oldjob),'-o'],universal_newlines=True)
assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-mix2 'in details and 'NodeList=node2 'in details and 'JobState=RUNNING'in details
for row in data['tasks']:assert sha(row['path'])==row['sha256']and row['spec']['source_root']==str(source)
root.mkdir();(root/'verified-before.json').write_text(json.dumps(dict(time=time.time(),old_job=oldjob,old_scontrol=details,old_state=state,old_active=oldspecs,new_plan_sha256=sha(plan),reason='Only this own c64 allocation is replaced after both diagnostic probes closed. Retire obsolete external-S-Link8 composition searches on this allocation, preserve all evidence and other7allocations. Actual native S LEC peaked145GiB; fresh final report/strict LEC budget256GiB, memory rule unchanged,16CPU and4dynamic slots.'),indent=2))
subprocess.run(['scancel',str(oldjob)],check=True);(root/'cancelled.json').write_text(json.dumps(dict(time=time.time(),jobs=[oldjob])))
command=['sbatch','--parsable','--partition=c64','--cpus-per-task=64','--mem=0','--exclusive','--nodelist=node2','--job-name=yzl-ctl162-smem2','--output='+str(queue/'slurm.log'),str(source/'project/experiments/control_v1/dynamic_queue.sh'),str(source),str(queue)]
job=subprocess.check_output(command,universal_newlines=True).strip();assert job.isdigit()
newdetails=subprocess.check_output(['scontrol','show','job',job,'-o'],universal_newlines=True)
assert 'UserId=yuzelu(10011)'in newdetails and 'JobName=yzl-ctl162-smem2 'in newdetails
submission=dict(time=time.time(),old_job=oldjob,job=job,command=command,scontrol=newdetails,forecast_cap_gib=256,slots=4,cpus_per_slot=16)
(root/'submitted.json').write_text(json.dumps(submission,indent=2));print(json.dumps(submission))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
