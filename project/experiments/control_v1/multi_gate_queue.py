"""Finite DAG: fill six 16-CPU slots as each leaf/stage becomes ready."""
import json,os,subprocess,sys,time
from pathlib import Path
root,source,producer,out,image,*models=sys.argv[1:];out=Path(out);out.mkdir(parents=True,exist_ok=False)
assert models and os.environ.get('SLURM_JOB_ID') and int(os.environ['SLURM_CPUS_PER_TASK'])>=96
active={};states={};logs={};terminal=set();started=time.time()
def launch(model,op):
    leaf=out/model;leaf.mkdir(exist_ok=True)
    command=['srun','--exclusive','--ntasks=1','--cpus-per-task=16','--cpu-bind=cores',
      'singularity','exec','--cleanenv','--bind','/public/home/yuzelu','--pwd',root,
      '--env','OMP_NUM_THREADS=16','--env','OPENBLAS_NUM_THREADS=1','--env','SLURM_JOB_ID='+os.environ['SLURM_JOB_ID'],
      image,'bash','-c','set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 "$@"','bash',
      str(Path(root)/'project/experiments/control_v1/gates.py'),op,'--source-root',source,
      '--producer',str(Path(producer)/model),'--out',str(leaf/op),'--sealed',str(leaf/'seal'),'--gates',str(leaf)]
    key=(model,op);logs[key]=(leaf/(op+'-worker.log')).open('w')
    active[key]=subprocess.Popen(command,stdout=logs[key],stderr=subprocess.STDOUT)
while len(terminal)<len(models):
    assert time.time()-started<21600,'Producer or gate did not terminate within six hours'
    for key,p in list(active.items()):
        rc=p.poll()
        if rc is not None:states[key]=rc;logs[key].close();del active[key]
    candidates=[]
    for model in models:
        if model in terminal:continue
        r=Path(producer)/model/'receipt.json'
        if not r.exists():continue
        try:receipt=json.loads(r.read_text())
        except json.JSONDecodeError:continue
        if not receipt['passed']:
            terminal.add(model);states[(model,'producer')]=-1;continue
        if any(rc!=0 for (m,op),rc in states.items() if m==model):
            if not any(m==model for m,op in active):terminal.add(model)
            continue
        if states.get((model,'deliver'))==0:terminal.add(model);continue
        if states.get((model,'seal'))!=0:ready=['seal']
        else:
            ready=['physical','drc','function']
            if (out/model/'function/physical-functional-proof.json').exists():ready.append('formal')
            if all(states.get((model,op))==0 for op in ['physical','drc','function','formal']):ready=['deliver']
        for op in ready:
            if (model,op) not in active and (model,op) not in states:candidates.append((model,op))
    for model,op in candidates:
        if len(active)==6:break
        launch(model,op)
    (out/'queue-state.json').write_text(json.dumps(dict(active=[list(k) for k in active],terminal=sorted(terminal),
        exit_codes={m+'/'+op:rc for (m,op),rc in states.items()},slots=6,cpus_per_slot=16,time=time.time()),indent=2)+'\n')
    if len(terminal)<len(models):time.sleep(2)
assert all(states.get((model,'deliver'))==0 for model in models),states
