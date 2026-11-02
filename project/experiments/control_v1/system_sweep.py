"""Six independent 16-CPU negotiated-route trials with immediate slot refill."""
import json,os,subprocess,sys,time
from pathlib import Path
root,manifest,graph,out,image=sys.argv[1:];out=Path(out);out.mkdir(parents=True,exist_ok=False)
assert os.environ.get('SLURM_JOB_ID') and int(os.environ['SLURM_CPUS_PER_TASK'])==96
memory={k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
budget=dict(available_bytes=memory['MemAvailable'],workers=6,forecast_gib_per_worker=32,guard_gib=16,headroom=1.2)
assert budget['available_bytes']>(6*32*1.2+16)*1024**3
(out/'memory-admission.json').write_text(json.dumps(budget,indent=2)+'\n')
pending=list(range(6));active={};finished={};logs={}
while pending or active:
    for seed,p in list(active.items()):
        rc=p.poll()
        if rc is not None:finished[seed]=rc;logs[seed].close();del active[seed]
    while pending and len(active)<6:
        seed=pending.pop(0);logs[seed]=(out/('seed-'+str(seed)+'.log')).open('w')
        cmd=['srun','--exclusive','--ntasks=1','--cpus-per-task=16','--cpu-bind=cores','singularity','exec','--cleanenv','--bind','/public/home/yuzelu','--pwd',root,
             '--env','OMP_NUM_THREADS=16','--env','OPENBLAS_NUM_THREADS=1','--env','SLURM_JOB_ID='+os.environ['SLURM_JOB_ID'],image,
             'bash','-c','set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 "$@"','bash',
             str(Path(root)/'project/experiments/control_v1/upper_link.py'),'--c',c,'--queue',endpoint,'--out',str(out/('seed-'+str(seed))),'--seed',str(seed)]
        active[seed]=subprocess.Popen(cmd,stdout=logs[seed],stderr=subprocess.STDOUT)
    (out/'queue-state.json').write_text(json.dumps(dict(active=sorted(active),pending=pending,exit_codes=finished,slots=6,cpus_per_slot=16,time=time.time()),indent=2)+'\n')
    if active:time.sleep(2)
assert all(rc==0 for rc in finished.values()),finished
