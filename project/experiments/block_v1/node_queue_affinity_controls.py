"""Real taskset/threads/grandchild controls for the production queue, no EDA."""
import hashlib
import json
import os
from pathlib import Path
import sys
from native_node_queue import schedule,validate


def main():
    out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
    assert len(os.sched_getaffinity(0))>=96
    base=out/'sandbox';run=base/'run';source=run/'src'
    worker=source/'project/experiments/block_v1/worker.py';worker.parent.mkdir(parents=True)
    worker.write_text('''import concurrent.futures,hashlib,json,os,subprocess,sys,time
from pathlib import Path
started=time.time();mode=sys.argv[2];cpus=int(sys.argv[3])
mask=sorted(os.sched_getaffinity(0));assert len(mask)==cpus==16
def thread(i):
 time.sleep(.02);return sorted(os.sched_getaffinity(0))
with concurrent.futures.ThreadPoolExecutor(max_workers=32)as pool:masks=list(pool.map(thread,range(32)))
grandchild=json.loads(subprocess.check_output([sys.executable,'-c','import json,os;print(json.dumps(sorted(os.sched_getaffinity(0))))']))
assert all(v==mask for v in masks)and grandchild==mask
time.sleep(2 if mode=='task-0'else .2)
p=Path('proof.json');p.write_text(json.dumps(dict(passed=True,started=started,finished=time.time(),mask=mask,thread_masks=masks,grandchild_mask=grandchild)))
Path('receipt.json').write_text(json.dumps(dict(passed=True,cpus=cpus,mode=mode,outputs={'proof.json':hashlib.sha256(p.read_bytes()).hexdigest()})))
''')
    tasks=[dict(id=str(i),mode='task-'+str(i),cwd=str(run/'tasks'/('task-'+str(i))),
                source=str(source),cpus=16,memory_gib=1,memory_basis='Tiny real affinity control, no EDA',
                report='proof.json',after=[],receipts=[])for i in range(8)]
    spec=dict(schema='block-v1-node-queue/1',node_cpus=96,default_task_cpus=16,memory_guard_gib=1,
              state_path=str(run/'node-queue-state.json'),tasks=tasks)
    validate(spec,base)
    worker_out=run/'tasks/native-node-queue';worker_out.mkdir(parents=True)
    result=schedule(spec,'affinity-control',worker_out,dict(worker='control',pid=os.getpid()),
                    lambda:dict(MemTotal=128*1024**3,MemAvailable=128*1024**3))
    assert result['passed']and result['queue_all_tasks_passed']and result['maximum_concurrent_tasks']==6
    proofs={t['id']:json.loads((Path(t['cwd'])/'proof.json').read_text())for t in tasks}
    overlap=0
    for k,a in proofs.items():
        for other,b in proofs.items():
            if k>=other:continue
            if max(a['started'],b['started'])<min(a['finished'],b['finished']):
                overlap+=1;assert not(set(a['mask'])&set(b['mask']))
    assert overlap>=15
    assert proofs['6']['started']<proofs['0']['finished']
    result=dict(passed=True,scheduler_sha256=hashlib.sha256((Path(__file__).parent/'native_node_queue.py').read_bytes()).hexdigest(),
                six_concurrent_16_cpu_masks=True,all_overlapping_masks_disjoint=True,
                overlap_pairs=overlap,threads_and_grandchildren_inherit_masks=True,
                immediate_refill_before_slowest=True,queue=result,
                scope='Actual production taskset launcher and queue with tiny real 32-thread/grandchild fixtures. No EDA, throughput, physical or logic acceptance.')
    (out/'affinity-controls.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
