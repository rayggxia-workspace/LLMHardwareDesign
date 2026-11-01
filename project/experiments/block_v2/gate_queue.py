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
    p.add_argument('--models',nargs='+',choices=['e','g','n','m','r'],default=['e','g'])
    p.add_argument('--memory-gib-per-worker',type=int)
    p.add_argument('--memory-basis')
    p.add_argument('--r-native-computation',type=Path)
    p.add_argument('--r-gds-computation',type=Path)
    p.add_argument('--r-formal-memory-gib',type=int)
    p.add_argument('--r-function-computation',type=Path)
    p.add_argument('--r-formal-computation',type=Path)
    a=p.parse_args()
    assert bool(a.r_native_computation)==bool(a.r_gds_computation)
    if a.r_native_computation:
        assert a.models==['r']
        assert a.r_formal_memory_gib is not None and 192<=a.r_formal_memory_gib<=448
        for path in (a.r_native_computation,a.r_gds_computation):
            assert path.is_absolute() and 'issue143-seven-block-v2-20261030' in path.parts and '..' not in path.parts
        # A valid finished native check admits sealing, while the independent
        # GDS computation can still run. Never reinterpret a partial report.
        assert (a.r_native_computation/'diagnostic.json').is_file()
    if a.memory_gib_per_worker is not None:
        assert 32<=a.memory_gib_per_worker<=192 and a.memory_basis
    cpus=int(os.environ['SLURM_CPUS_PER_TASK'])
    assert os.environ.get('SLURM_JOB_ID') and 16<=cpus<=96 and cpus%16==0
    cpu_slots=cpus//16
    for path in (a.root,a.raw,a.out):
        assert path.is_absolute() and '..' not in path.parts
        assert 'issue143-seven-block-v2-20261030' in path.parts
    a.out.mkdir(parents=True,exist_ok=False)
    available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
    # Defaults remain conservative; a measured estimate needs an explicit basis.
    forecast=a.memory_gib_per_worker or (192 if 'r' in a.models else 64)
    per_worker=forecast*1024**3;guard=16*1024**3
    slots=min(cpu_slots,int((available-guard)/(per_worker*1.2)))
    assert slots>0
    report=dict(passed=False,job=os.environ['SLURM_JOB_ID'],slots=slots,cpu_slots=cpu_slots,cpus_per_worker=16,
        memory=dict(available_bytes=available,per_worker_initial_forecast_bytes=per_worker,headroom=1.2,guard_bytes=guard,
                    forecast_basis=a.memory_basis or 'Initial conservative size-class estimate; not measured demand'),
        started_unix=time.time(),tasks={})
    if a.r_native_computation:
        report['memory']['r_formal_forecast_gib']=a.r_formal_memory_gib
        report['memory']['weighted_admission']=True
    tasks={}
    for model in a.models:
        for op,dep in [('seal',[]),('physical',['seal']),('drc',['seal']),('function',['seal']),
                       ('formal',['function']),('deliver',['physical','drc','function','formal']),('geometry',['deliver'])]:
            if model=='r' and a.r_native_computation and op=='formal':dep=['seal']
            tasks[(model,op)]=[(model,x)for x in dep]
    def save():(a.out/'queue.json').write_text(json.dumps(report,indent=2)+'\n')
    def worker(key):
        model,op=key;source=a.raw/'pnr'/model if op=='seal' else a.out/('seal-'+model)
        if op=='geometry':source=a.out/('deliver-'+model)
        dest=a.out/(op+'-'+model)
        command=['python3',str(a.root/'project/experiments/block_v2/qualify.py'),op,'--source',str(source),'--out',str(dest)]
        if model=='r' and a.r_native_computation:
            if op=='seal':command+=['--computation',str(a.r_native_computation)]
            if op=='drc':
                command[2]='drc-join'
                command+=['--computation',str(a.r_native_computation),'--peer',str(a.r_gds_computation)]
            if op=='function' and a.r_function_computation:
                command[2]='function-join';command+=['--computation',str(a.r_function_computation)]
            if op=='formal' and a.r_formal_computation:
                command[2]='formal-join';command+=['--computation',str(a.r_formal_computation)]
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
    def memory_weight(key):
        return (a.r_formal_memory_gib if key==('r','formal') and a.r_native_computation and not a.r_formal_computation else forecast)*1024**3
    def memory_ready(key):
        if not a.r_native_computation:return True
        projected=sum(memory_weight(v) for v in running.values())+memory_weight(key)
        return projected*1.2+guard<=available
    external_wait_start=time.monotonic()
    def finished(path):
        if not path.is_file():return False
        try:
            # A false finished receipt must also reach its worker and fail;
            # incomplete JSON is just a writer that has not finished yet.
            row=json.loads(path.read_text())
            return 'passed' in row or 'diagnostic_completed' in row
        except json.JSONDecodeError:return False
    def ready(key):
        model,op=key
        if model!='r' or not a.r_native_computation:return True
        if op=='drc':return finished(a.r_gds_computation/'diagnostic.json')
        if op=='function' and a.r_function_computation:return finished(a.r_function_computation/'receipt.json')
        if op=='formal':
            if a.r_formal_computation:
                return ('r','function') in complete and finished(a.r_formal_computation/'receipt.json')
            if ('r','function') in failed:return True  # Propagate the actual failure below.
            p=a.out/'function-r/physical-functional-proof.json'
            if not p.is_file():return False
            try:return json.loads(p.read_text()).get('passed') is True
            except json.JSONDecodeError:return False
        return True
    with concurrent.futures.ThreadPoolExecutor(max_workers=slots)as pool:
        while remaining or running:
            for key in sorted(remaining):
                if any(x in failed for x in tasks[key]) or (key==('r','formal') and ('r','function') in failed):
                    failed.add(key);remaining.remove(key);report['tasks']['/'.join(key)]=dict(passed=False,blocked_by_failed_dependency=True);save()
                elif len(running)<slots and memory_ready(key) and all(x in complete for x in tasks[key]) and ready(key):
                    remaining.remove(key);running[pool.submit(worker,key)]=key
                    report['tasks']['/'.join(key)]=dict(state='running',started_unix=time.time(),memory_forecast_bytes=memory_weight(key));save()
            if not running:
                if remaining and a.r_native_computation and any(key in remaining for key in [('r','drc'),('r','function'),('r','formal')]):
                    assert time.monotonic()-external_wait_start<23*3600,'GDS computation has not produced a final receipt within23h'
                    time.sleep(20);continue
                assert not remaining,'DAG deadlock';break
            # Observe newly available immutable function views and external
            # GDS results even when a long worker has not finished yet.
            done,_=concurrent.futures.wait(running,timeout=20,return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                key=running.pop(future)
                try:row=future.result()
                except Exception as error:row=dict(passed=False,error=str(error))
                report['tasks']['/'.join(key)]=row
                (complete if row['passed'] else failed).add(key);save()
    report.update(passed=not failed,ended_unix=time.time());save()
    return int(bool(failed))

if __name__=='__main__':raise SystemExit(main())
