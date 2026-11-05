"""Finite per-leaf Slurm queue: three 16-CPU slots, immediate dependency refill."""
import json,os,re
from pathlib import Path
import subprocess,sys,time
root,source_root,producer,out,image,*allocation=sys.argv[1:];out=Path(out)
job=allocation[0] if allocation else os.environ.get('SLURM_JOB_ID')
assert job and str(job).isdigit()
# A controller may schedule new steps in this task's existing allocation;
# only its actual 16-CPU Slurm children execute EDA, never the login process.
details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True)
assert re.search(r'UserId=\S+\('+str(os.getuid())+r'\)',details)
assert 'JobName=yzl-ctl162-' in details and 'JobState=RUNNING' in details
assert int(re.search(r'NumCPUs=(\d+)',details).group(1))>=48
(out/'allocation.json').write_text(json.dumps(dict(job=job,scontrol=details,controller_is_scheduler_only=True),indent=2)+'\n')
def command(op):
    return ['srun','--jobid='+str(job),'--exclusive','--ntasks=1','--cpus-per-task=16','--cpu-bind=cores',
        '/public/software/singularity-ce-4.3.4/bin/singularity','exec','--cleanenv','--bind','/public/home/yuzelu','--pwd',root,
        '--env','OMP_NUM_THREADS=16','--env','OPENBLAS_NUM_THREADS=1',
        '--env','SLURM_JOB_ID='+str(job),image,'bash','-c',
        'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 "$@"',
        'bash',str(Path(root)/'project/experiments/control_v1/gates.py'),op,
        '--source-root',source_root,'--producer',producer,'--out',str(out/op),'--sealed',str(out/'seal'),'--gates',str(out)]
with (out/'seal-worker.log').open('w') as f:
    p=subprocess.run(command('seal'),stdout=f,stderr=subprocess.STDOUT)
assert p.returncode==0,'seal failed'
active={};states={};logs={};pending=['physical','drc','function','formal']
while pending or active:
    for op in list(pending):
        if len(active)==3:break
        if op=='formal' and not (out/'function/physical-functional-proof.json').exists():
            if states.get('function',0)!=0:states[op]=-1;pending.remove(op)
            continue
        logs[op]=(out/(op+'-worker.log')).open('w')
        active[op]=subprocess.Popen(command(op),stdout=logs[op],stderr=subprocess.STDOUT);pending.remove(op)
    for op,p in list(active.items()):
        rc=p.poll()
        if rc is not None:states[op]=rc;logs[op].close();del active[op]
    (out/'queue-state.json').write_text(json.dumps(dict(active=list(active),pending=pending,exit_codes=states,time=time.time()),indent=2)+'\n')
    if active:time.sleep(2)
assert len(states)==4 and all(v==0 for v in states.values()),states
with (out/'deliver-worker.log').open('w') as f:
    p=subprocess.run(command('deliver'),stdout=f,stderr=subprocess.STDOUT)
assert p.returncode==0,'delivery failed'
