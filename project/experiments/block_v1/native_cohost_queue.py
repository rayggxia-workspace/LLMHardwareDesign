"""Run ready independent work in an existing allocation's disjoint spare CPUs.

The original node queue and source remain immutable. The ordinary queue
scheduler/claim/worker/receipt path is reused with an explicit CPU partition.
No sbatch, peer cancellation, RTL change or physical qualification is implied.
"""
import json
import os
from pathlib import Path


def partition(allocated, foreign, available):
    allocated, foreign, available = map(list, (allocated, foreign, available))
    assert all(len(v)==len(set(v)) for v in (allocated,foreign,available))
    allocated, foreign, available = map(set, (allocated, foreign, available))
    assert len(allocated) == 96 and len(foreign) == 16 and len(available) == 80
    assert not foreign & available and foreign | available == allocated
    return sorted(available)


def reserve_memory(memory, forecast_gib, measured_bytes):
    assert forecast_gib > 0 and measured_bytes >= 0
    reservation = max(int(forecast_gib * 1024**3 * 1.2), measured_bytes)
    total = memory['MemTotal'] - reservation
    assert total > 16 * 1024**3, 'Parent reservation leaves no guarded memory'
    return dict(MemTotal=total, MemAvailable=min(total, memory['MemAvailable'])), reservation


def foreign_tree(pid, cpus, job):
    assert 'job_' + job in (Path('/proc') / str(pid) / 'cgroup').read_text()
    todo, seen, rss, threads = [pid], set(), 0, 0
    while todo:
        current = todo.pop()
        if current in seen:
            continue
        seen.add(current)
        p = Path('/proc') / str(current)
        try:
            data = dict(l.split(':', 1) for l in (p / 'status').read_text().splitlines() if ':' in l)
            assert int(data['Uid'].split()[0]) == os.getuid()
            rss += int(data.get('VmRSS', '0 kB').split()[0]) * 1024
            for t in (p / 'task').iterdir():
                # The parent queue coordinator is allowed all96 CPUs; every
                # compute descendant must retain its hard16-CPU mask.
                if current != pid:
                    assert os.sched_getaffinity(int(t.name)) <= set(cpus), 'Peer compute CPU overlap'
                    threads += 1
                todo.extend(map(int, (t / 'children').read_text().split()))
        except (FileNotFoundError, ProcessLookupError):
            if current == pid:
                raise AssertionError('Parent allocation worker disappeared')
    assert len(seen) > 1 and threads > 0, 'No live peer compute process verified'
    return dict(rss_bytes=rss, processes=len(seen), compute_threads=threads)


def serve(root, out, cpus):
    from native_allocation_group import memory_snapshot
    from native_node_queue import schedule, sha, validate
    assert cpus == 80 and int(os.environ['SLURM_CPUS_PER_TASK']) == 80
    base = out.parents[2]
    queue_path, cohost_path = root.parent / 'node-queue.json', root.parent / 'cohost.json'
    queue_sha, cohost_sha = sha(queue_path), sha(cohost_path)
    spec, binding = json.loads(queue_path.read_text()), json.loads(cohost_path.read_text())
    validate(spec, base)
    assert binding['schema'] == 'block-v1-cohost/1' and binding['new_allocation'] is False
    assert os.environ['SLURM_JOB_ID'] == binding['job_id'] and os.uname().nodename == binding['node']
    available = partition(binding['allocated_cpus'], binding['foreign_cpus'], os.sched_getaffinity(0))
    assert available == binding['cohost_cpus']
    parent = Path(binding['parent_queue'])
    assert base in parent.parents and parent.name == 'node-queue.json'
    assert sha(parent) == binding['parent_queue_sha256']
    parent_spec = json.loads(parent.read_text())
    assert parent_spec['node_cpus'] == 96 and len(parent_spec['tasks']) == 1
    task = parent_spec['tasks'][0]
    assert task['id'] == binding['parent_task'] and task['cpus'] == 16
    assert task['memory_gib'] == binding['foreign_memory_gib']
    live_path = parent.parent / 'tasks/native-node-queue/queue-live.json'
    initial = json.loads(live_path.read_text())
    owner = initial['owner']
    assert owner['job_id'] == binding['job_id'] and owner['node'] == binding['node']
    observations = dict(max_foreign_rss_bytes=0, samples=0)

    def measured_memory():
        assert sha(queue_path) == queue_sha and sha(cohost_path) == cohost_sha
        assert sha(parent) == binding['parent_queue_sha256']
        live = json.loads(live_path.read_text())
        assert live['owner'] == owner and live['active'] == [binding['parent_task']]
        assert live['cpu_affinities'][binding['parent_task']] == binding['foreign_cpus']
        actual = foreign_tree(owner['pid'], binding['foreign_cpus'], binding['job_id'])
        observations['samples'] += 1
        observations['max_foreign_rss_bytes'] = max(observations['max_foreign_rss_bytes'], actual['rss_bytes'])
        memory, reserved = reserve_memory(memory_snapshot(), binding['foreign_memory_gib'], actual['rss_bytes'])
        observations['last'] = dict(peer=actual, adjusted_memory=memory, foreign_reservation_with_margin_bytes=reserved)
        return memory

    # The96-CPU declaration is retained and hashed. Only this worker's runtime
    # budget is80;16 CPUs remain exclusively with the already-running peer.
    runtime = dict(spec, node_cpus=80)
    cohost_owner = dict(job_id=binding['job_id'], node=os.uname().nodename, worker=str(out), pid=os.getpid())
    result = schedule(runtime, queue_sha, out, cohost_owner, measured_memory)
    record = dict(passed=result['passed'], original_queue_sha256=queue_sha, cohost_binding_sha256=cohost_sha,
                  new_allocation=False, parent_owner=owner, foreign_cpus=binding['foreign_cpus'],
                  cohost_cpus=available, combined_cpu_ceiling=96, observations=observations,
                  runtime_queue_allocated_cpus=80, original_queue_node_cpus=96,
                  maximum_combined_concurrent_tasks=1 + result['maximum_concurrent_tasks'],
                  scope='Existing Slurm job; peer16 plus at most five disjoint16CPU tasks, immediate refill. '
                        'Foreign forecast1.2 reservation and liveRSS retained in addition to normal task1.2/16GiB guard. '
                        'Scheduling evidence only, not macro qualification.')
    (out / 'native-cohost-queue.json').write_text(json.dumps(record, indent=2) + '\n')
    assert result['passed'] and result['queue_all_tasks_passed'], 'Cohost work did not complete all required tasks'
