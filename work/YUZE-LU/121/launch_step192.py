"""One-off M hold repair in released CPUs of our existing allocation.

No new allocation or mutation of queue191. Count EVERY unfinished191 task,
including dependency-blocked tasks, before reserving this one16CPU step.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

BASE=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121')
RUN=BASE/'block-v1-20261027-192'
PARENT=BASE/'block-v1-20261027-191'
TASK=RUN/'tasks/five-macro-repair-m-hold'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(name,data):(RUN/name).write_text(json.dumps(data,indent=2)+'\n')


if len(sys.argv)>1 and sys.argv[1]=='--step':
    assert os.environ['SLURM_JOB_ID']=='92449' and int(os.environ['SLURM_CPUS_PER_TASK'])==16
    memory={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key,value=line.split(':',1)
        if key in ('MemTotal','MemAvailable'):memory[key]=int(value.split()[0])*1024
    assert memory['MemAvailable']>int((32*1.2+16)*1024**3),'Actual node RAM insufficient for32GiB estimate+20%+guard'
    save('actual-step.json',dict(job_id=os.environ['SLURM_JOB_ID'],step_id=os.environ['SLURM_STEP_ID'],
         node=os.uname().nodename,cpus=16,memory=memory,time=time.time()))
    code=subprocess.call(['bash',str(RUN/'src/project/experiments/block_v1/worker.sh'),str(RUN/'src'),'five-macro-repair-m-hold'])
    sys.exit(code)

assert Path(__file__).resolve().parent==RUN
manifest=json.loads((RUN/'step-manifest.json').read_text())
assert sha(__file__)==manifest['launcher_sha256']
assert sha(RUN/'source.tar')==manifest['source_archive_sha256']
spec_path=PARENT/'node-queue.json';spec=json.loads(spec_path.read_text())
state=json.loads((PARENT/'node-queue-state.json').read_text())
assert sha(spec_path)==state['manifest_sha256']==manifest['parent_queue_sha256']
for key,status in [('m-physical','FAILED'),('m-final-function','PASSED'),('m-formal','PASSED')]:
    assert state['tasks'][key]['status']==status
live=subprocess.check_output(['squeue','-h','-j','92449','-o','%i|%u|%j|%T|%C|%N'],universal_newlines=True).strip()
assert live=='92449|yuzelu|yzl-bv1-native-node-queue|RUNNING|96|node26',live
pending=[t for t in spec['tasks'] if state['tasks'].get(t['id'],{}).get('status') not in ('PASSED','FAILED','BLOCKED')]
cpu_bound=sum(t['cpus'] for t in pending)+16
memory_bound=int((sum(t['memory_gib'] for t in pending)+32)*1.2*1024**3)+16*1024**3
snapshot=json.loads((PARENT/'tasks/native-node-queue/queue-live.json').read_text())
assert cpu_bound<=96 and memory_bound<snapshot['memory']['MemTotal']
assert not (RUN/'step-state.json').exists(),'Do not duplicate an uncertain or existing step'
claim=dict(status='STARTING',started=time.time(),job_id='92449',cpus=16,new_allocation=False,
           parent_queue_sha256=sha(spec_path),unfinished_parent_tasks=[t['id'] for t in pending],
           all_future_parent_plus_step_cpu_bound=cpu_bound,
           all_future_parent_plus_step_memory_with_margin_and_guard_bytes=memory_bound,
           node_memory_bytes=snapshot['memory']['MemTotal'],repair_memory_estimate_gib=32,
           memory_basis='Provisional32GiB allowance based on original M full-flow groupHWM~3.8GiB and tool peak~3.4GiB; not a measured repair peak',
           source_commit=manifest['source_commit'],source_archive_sha256=manifest['source_archive_sha256'])
with (RUN/'step-state.json').open('x') as stream:json.dump(claim,stream,indent=2)
TASK.mkdir(parents=True,exist_ok=False)
command=['srun','--jobid=92449','--overlap','--nodes=1','--ntasks=1','--cpus-per-task=16',
         '--cpu-bind=none','--chdir='+str(TASK),'python3',str(Path(__file__).resolve()),'--step']
with (RUN/'step-launch.log').open('w') as stream:
    code=subprocess.call(command,stdout=stream,stderr=subprocess.STDOUT)
claim.update(finished=time.time(),returncode=code,status='PASSED' if code==0 else 'FAILED',argv=command)
if (TASK/'receipt.json').is_file():
    r=json.loads((TASK/'receipt.json').read_text());claim['receipt_sha256']=sha(TASK/'receipt.json')
    assert bool(r['passed'])==(code==0)
save('step-state.json',claim)
print(json.dumps(claim))
