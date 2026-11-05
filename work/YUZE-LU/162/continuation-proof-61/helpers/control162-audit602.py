import subprocess,shlex
code=r'''from pathlib import Path
import json,hashlib,subprocess,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-pending-c96-controller-audit-602';assert not out.exists();source=b/'source-236/project/experiments/control_v1';batch=b/'dynamic-06/node26/batch.sh';q=source/'dynamic_queue.py';s=source/'dynamic_queue.sh';text=q.read_text();shell=s.read_text();batch_text=batch.read_text();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert 'SLURM_CPUS_PER_TASK'in text and 'slots=min(6,'in text and '//16)'in text and "'-c16'"in text and "'--exclusive'"in text
assert 'forecast*1.2+16'in text and 'MemAvailable'in text
assert not any(x in text+shell for x in ['node26','--nodelist','SLURM_JOB_NODELIST','socket.gethostname'])
details=subprocess.check_output(['scontrol','show','job','96222','-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and'JobState=PENDING'in details and'Partition=c96'in details and'NumCPUs=96'in details and'ReqNodeList=(null)'in details
assert str(source.parent.parent)in batch_text and str(b/'dynamic-06/node26')in batch_text
out.mkdir();r=dict(passed=True,time=time.time(),whole_system_qualified=False,job_details=details,files=[dict(path=str(p),sha256=sha(p))for p in [batch,q,s]],scope='Read-only audit of actual pending eighth-job source236 batch and controller: queue directory node26 is a label; actual controller has no hostname/node26/nodelist restriction, derives min(6,allocatedCPUs//16), launches exclusive16CPU child steps and retains actual1.2forecast+16GiB MemAvailable admission. Same pending96CPU own c96 job96222 has no ReqNodeList. No job/script/source/queue modification and no physical acceptance implied.')
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(passed=True,controller_slots_for_96=6,physical_acceptance=False)))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],universal_newlines=True))
