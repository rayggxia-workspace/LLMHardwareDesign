"""Finite owned qualification DAG: six 16-core slots, refill on completion."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import time

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--models',nargs='+',choices=['e','g','n','m'],default=['e','g']);a=p.parse_args()
    cpus=int(os.environ['SLURM_CPUS_PER_TASK'])
    assert os.environ.get('SLURM_JOB_ID') and 16<=cpus<=96 and cpus%16==0
    cpu_slots=cpus//16
    for path in (a.root,a.raw,a.out):
        assert path.is_absolute() and '..' not in path.parts
        assert 'issue143-seven-block-v2-20261030' in path.parts
    a.out.mkdir(parents=True,exist_ok=False)
    available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
    # Small leaves only; this budget is not valid for R/S/T or a large M.
    per_worker=64*1024**3;guard=16*1024**3
    slots=min(cpu_slots,int((available-guard)/(per_worker*1.2)))
    assert slots>0
    report=dict(passed=False,job=os.environ['SLURM_JOB_ID'],slots=slots,cpu_slots=cpu_slots,cpus_per_worker=16,
        memory=dict(available_bytes=available,per_worker_initial_forecast_bytes=per_worker,headroom=1.2,guard_bytes=guard),
        started_unix=time.time(),tasks={})
    tasks={}
    for model in a.models:
        for op,dep in [('seal',[]),('physical',['seal']),('drc',['seal']),('function',['seal']),
                       ('formal',['function']),('deliver',['physical','drc','function','formal']),('geometry',['deliver'])]:
            tasks[(model,op)]=[(model,x)for x in dep]
    def save():(a.out/'queue.json').write_text(json.dumps(report,indent=2)+'\n')
    def worker(key):
        model,op=key;source=a.raw/'pnr'/model if op=='seal' else a.out/('seal-'+model)
        if op=='geometry':source=a.out/('deliver-'+model)
        dest=a.out/(op+'-'+model)
        command=['python3',str(a.root/'project/experiments/block_v2/qualify.py'),op,'--source',str(source),'--out',str(dest)]
        if op=='formal':command+=['--function',str(a.out/('function-'+model))]
        if op=='deliver':command+=['--gates',str(a.out)]
        image='/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif'
        command=['srun','--exclusive','--ntasks=1','--cpus-per-task=16','--cpu-bind=cores',
            '/public/software/singularity-ce-4.3.4/bin/singularity','exec','--cleanenv','--bind','/public/home/yuzelu',
            '--pwd',str(a.root),'--env','OMP_NUM_THREADS=16','--env','OPENBLAS_NUM_THREADS=1',image,
            '/usr/bin/time','-v','bash','-c','set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec "$@"','bash',*command]
        with (a.out/(op+'-'+model+'-worker.log')).open('w') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
        row=dict(returncode=result.returncode,ended_unix=time.time(),output=str(dest),passed=False)
        if (dest/'receipt.json').is_file():row['passed']=result.returncode==0 and json.loads((dest/'receipt.json').read_text())['passed']
        return row
    remaining=set(tasks);running={};complete=set();failed=set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=slots)as pool:
        while remaining or running:
            for key in sorted(remaining):
                if any(x in failed for x in tasks[key]):
                    failed.add(key);remaining.remove(key);report['tasks']['/'.join(key)]=dict(passed=False,blocked_by_failed_dependency=True);save()
                elif len(running)<slots and all(x in complete for x in tasks[key]):
                    remaining.remove(key);running[pool.submit(worker,key)]=key
                    report['tasks']['/'.join(key)]=dict(state='running',started_unix=time.time());save()
            if not running:
                assert not remaining,'DAG deadlock';break
            done,_=concurrent.futures.wait(running,return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                key=running.pop(future)
                try:row=future.result()
                except Exception as error:row=dict(passed=False,error=str(error))
                report['tasks']['/'.join(key)]=row
                (complete if row['passed'] else failed).add(key);save()
    report.update(passed=not failed,ended_unix=time.time());save()
    return int(bool(failed))

if __name__=='__main__':raise SystemExit(main())
