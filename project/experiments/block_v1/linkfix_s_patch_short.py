"""Finite patch probe in a measured spare16CPU slot; no parent lifetime claim."""
import json
import os
import subprocess
import sys
from pathlib import Path
from native_node_queue import sha


def serve(root):
    from native_cohost_queue import foreign_tree, reserve_memory
    from native_allocation_group import memory_snapshot
    binding = json.loads((root.parent/'opportunistic.json').read_text())
    assert os.environ['SLURM_JOB_ID'] == binding['job_id'] == '93425'
    allocated = sorted(os.sched_getaffinity(0)); assert len(allocated) == 48
    parent = Path(binding['parent_queue']); assert sha(parent) == binding['parent_queue_sha256']
    live = json.loads((parent.parent/'tasks/native-node-queue/queue-live.json').read_text())
    assert live['owner']['job_id'] == '93425' and live['active'] == ['linkfix-function-s']
    foreign = allocated[32:48]; spare = allocated[:16]
    assert live['cpu_affinities']['linkfix-function-s'] == foreign
    actual = foreign_tree(live['owner']['pid'], foreign, '93425')
    memory, reserved = reserve_memory(memory_snapshot(), 128, actual['rss_bytes'])
    assert min(memory['MemAvailable'], memory['MemTotal']) > (16*1.2+16)*1024**3
    os.sched_setaffinity(0, spare)
    task = root.parent/'tasks/linkfix-s-patch'; task.mkdir(parents=True)
    with (task/'short-step.log').open('w') as log:
        code = subprocess.call(['taskset','--cpu-list',','.join(map(str,spare)), 'bash',str(root/'project/experiments/block_v1/worker.sh'),str(root),'linkfix-s-patch'],
            cwd=task, env=dict(os.environ, SLURM_CPUS_PER_TASK='16', OMP_NUM_THREADS='16'), stdout=log, stderr=subprocess.STDOUT)
    receipt = json.loads((task/'receipt.json').read_text()); assert code == 0 and receipt['passed']
    assert sha(task/'linkfix-s-patch.json') == receipt['outputs']['linkfix-s-patch.json']
    (root.parent/'opportunistic-short-step.json').write_text(json.dumps(dict(passed=True,new_allocation=False,
        job_id='93425',allocated_cpus=allocated,parent_cpus=foreign,probe_cpus=spare,parent_rss=actual['rss_bytes'],
        parent_reserved_bytes=reserved,receipt_sha256=sha(task/'receipt.json'),
        scope='Closed finite patch-probe receipt only; parent lifetime not extended. Interrupted work grants no qualification.'),indent=2)+'\n')


if __name__ == '__main__':
    serve(Path(sys.argv[1]))
