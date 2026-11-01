"""Two independent native receivers inside one c96 Slurm allocation.

Children keep the ordinary tasks/<leaf> depth and separate workers/receipts.
No new sbatch or allocation is created. The sum of child thread ceilings is
bounded by the real parent allocation; failed children do not cancel peers.
"""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def file_sha(path):
    digest=hashlib.sha256()
    with path.open('rb')as stream:
        for data in iter(lambda:stream.read(1024*1024),b''):digest.update(data)
    return digest.hexdigest()


def memory_snapshot():
    values={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key,value=line.split(':',1)
        if key in ('MemTotal','MemAvailable'):
            amount,unit=value.split();assert unit=='kB'
            values[key]=int(amount)*1024
    assert set(values)=={'MemTotal','MemAvailable'}
    assert 0<values['MemAvailable']<=values['MemTotal']
    return values


def receive_pair(root,out,cpus):
    assert cpus==64,'Pair requires exactly two independently bounded 32-CPU workers'
    specs=[dict(id='native-receive-shared109-'+policy,
                mode='native-const-protected-receive-shared109-'+policy,cpus=32)
           for policy in ['a','c']]
    assert sum(item['cpus']for item in specs)==cpus
    assert out.parent.name=='tasks'and out.name=='native-const-receiver-group'
    allocation=out/'allocation.txt';assert allocation.is_file()
    memory=memory_snapshot()
    # Conservative scheduling bound from actual complete C8 run080 MaxRSS,
    # not a claim that a receiver has already measured the same peak.
    prior_c8_peak_bytes=180451804*1024
    simultaneous=2 if memory['MemAvailable']>=((2*prior_c8_peak_bytes*6+4)//5)else 1
    slots={}
    for spec in specs:
        child=out.parent/spec['id'];child.mkdir(exist_ok=False)
        slots[spec['id']]=child
    def execute(spec):
        child=slots[spec['id']]
        env=os.environ.copy()
        env.update(OMP_NUM_THREADS=str(spec['cpus']),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        argv=[sys.executable,str(root/'project/experiments/block_v1/worker.py'),str(root),spec['mode'],str(spec['cpus'])]
        started=time.time()
        with(child/'group-child.log').open('w')as stream:
            process=subprocess.run(argv,cwd=child,env=env,stdout=stream,stderr=subprocess.STDOUT)
        receipt_path=child/'receipt.json'
        record=dict(**spec,argv=argv,folder=str(child),returncode=process.returncode,
                    started=started,finished=time.time(),log_sha256=file_sha(child/'group-child.log'))
        if receipt_path.exists():
            receipt=json.loads(receipt_path.read_text())
            record.update(receipt_sha256=file_sha(receipt_path),passed=receipt.get('passed')is True)
            assert receipt['cpus']==spec['cpus']and receipt['mode']==spec['mode']
        else:record['passed']=False
        return record
    # Do not return or terminate a peer when the other worker fails.
    with concurrent.futures.ThreadPoolExecutor(max_workers=simultaneous)as pool:
        children=list(pool.map(execute,specs))
    record=dict(schema='block-v1-native-allocation-group/1',
                passed=all(item['passed']and item['returncode']==0 for item in children),
                allocated_cpus=cpus,simultaneous_workers=simultaneous,sum_child_cpu_ceilings=64,
                maximum_concurrent_cpu_ceilings=32*simultaneous,memory_preflight=memory,
                conservative_prior_c8_peak_bytes=prior_c8_peak_bytes,parallel_memory_safety_factor=1.2,
                allocation_sha256=file_sha(allocation),children=children,
                scope='Two full independent physical receivers in one allocation; no reduced gates or nested sbatch')
    (out/'native-allocation-group.json').write_text(json.dumps(record,indent=2)+'\n')
    assert record['passed'],'A full physical child failed; all completed peer evidence preserved'
