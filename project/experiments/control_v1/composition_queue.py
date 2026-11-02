"""Six independent 16-CPU slots: final-cell composition plus native PG inspections."""
import json,os,subprocess,sys,time
from pathlib import Path
root,function_manifest,physical_manifest,out,image=sys.argv[1:];out=Path(out);out.mkdir(parents=True,exist_ok=False)
assert os.environ.get('SLURM_JOB_ID') and int(os.environ['SLURM_CPUS_PER_TASK'])==96
mem={k:int(v.split()[0])*1024 for k,v in (s.split(':',1) for s in Path('/proc/meminfo').read_text().splitlines())}
budget=dict(available_bytes=mem['MemAvailable'],slots=6,cpus_per_slot=16,compile_forecast_gib=128,inspection_forecast_gib=8,headroom=1.2,guard_gib=16)
assert mem['MemAvailable']>((128+5*8)*1.2+16)*1024**3
(out/'memory-admission.json').write_text(json.dumps(budget,indent=2)+'\n')
pending=[('composition',['final_composition.py','--manifest',function_manifest,'--out',str(out/'composition')])]
for leaf in json.loads(Path(physical_manifest).read_text())['leaves']:
    pending.append(('pg-'+leaf,['pg_access.py','--manifest',physical_manifest,'--leaf',leaf,'--out',str(out/('pg-'+leaf))]))
active={};finished={};logs={}
while pending or active:
    for name,p in list(active.items()):
        rc=p.poll()
        if rc is not None:finished[name]=rc;logs[name].close();del active[name]
    while pending and len(active)<6:
        name,args=pending.pop(0);logs[name]=(out/(name+'.log')).open('w')
        script=Path(root)/'project/experiments/control_v1'/args[0]
        command=['srun','--exclusive','-n1','-c16','--cpu-bind=cores','singularity','exec','--cleanenv','--bind','/public/home/yuzelu',
                 '--env','OMP_NUM_THREADS=16','--env','OPENBLAS_NUM_THREADS=1','--env','SLURM_JOB_ID='+os.environ['SLURM_JOB_ID'],image,
                 'bash','-c','set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 "$@"','bash',str(script),*args[1:]]
        active[name]=subprocess.Popen(command,stdout=logs[name],stderr=subprocess.STDOUT)
    (out/'queue-state.json').write_text(json.dumps(dict(active=list(active),pending=[n for n,_ in pending],exit_codes=finished,slots=6,cpus_per_slot=16,time=time.time()),indent=2)+'\n')
    if active:time.sleep(2)
assert all(v==0 for v in finished.values()),finished
