"""Admit only six pinned revision300 queues; no EDA or job cancellation here.

Run on the login host. The existing dispatcher remains the sole submission
authority and retains its issue-wide lock, reservation and eight-allocation cap.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time


RUNS = ('344', '345', '346', '363', '364', '365')
SLURM_TERMINAL = {'COMPLETED', 'FAILED', 'CANCELLED', 'TIMEOUT', 'OUT_OF_MEMORY',
                  'NODE_FAIL', 'PREEMPTED', 'BOOT_FAIL', 'DEADLINE', 'REVOKED'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(config, base):
    assert config['schema'] == 'revision300-admission/1'
    assert config['max_allocations'] == 8 and config['interval_seconds'] == 60
    assert base.is_absolute() and base.name == 'issue-121'
    assert [x['run_id'] for x in config['runs']] == ['block-v1-20261029-' + n for n in RUNS]
    for row in config['runs']:
        root = base / row['run_id']
        assert root.resolve().parent == base.resolve()
        for name, digest in row['files'].items():
            assert name in ('manifest.json', 'node-queue.json',
                            'src/project/experiments/block_v1/dispatch.py',
                            'src/project/experiments/block_v1/native_node_queue.py')
            assert len(digest) == 64 and sha(root / name) == digest
        assert len(row['files']) == 4


def classify(queue, node_state, dispatch_state, dependency):
    states = node_state.get('tasks', {})
    if queue['tasks'] and all(states.get(t['id'], {}).get('status') == 'PASSED' for t in queue['tasks']):
        return 'passed'
    if any(v.get('status') in ('FAILED', 'BLOCKED') for v in states.values()):
        return 'needs_attention'
    # Any reservation, job ID or previous terminal attempt forbids resubmission.
    if dispatch_state.get('tasks'):
        return 'already_dispatched'
    checks = [dependency(t, states)[0] for t in queue['tasks']]
    if 'ready' in checks:
        return 'ready'
    return 'dependency_failed' if 'failed' in checks else 'waiting_dependency'


def read(path):
    return json.loads(path.read_text()) if path.exists() else {}


def own_allocations(lines, issue_job_ids):
    result = []
    for line in lines:
        fields = line.split('|')
        assert len(fields) == 3 and all(fields), 'Malformed Slurm observation'
        if fields[1].startswith('yzl-') and fields[0] in issue_job_ids:
            result.append(line)
    return result


def allocation_observation(items):
    observations = {}
    for key, item in items.items():
        job = item.get('job_id')
        if not job:
            observations[key] = 'uncertain_submission'
            continue
        try:
            lines = output(['squeue', '-h', '-j', job, '-o', '%i|%T']).splitlines()
        except subprocess.CalledProcessError:
            lines = []  # Resolve purged jobs through accounting, never by absence.
        exact = [line.split('|')[1] for line in lines if line.split('|')[0] == job]
        if not exact:
            lines = output(['sacct', '-n', '-P', '-j', job, '--format=JobIDRaw,State']).splitlines()
            exact = [line.split('|')[1].split()[0].rstrip('+') for line in lines if line.split('|')[0] == job]
        observations[key] = exact[0] if exact else 'accounting_unresolved'
    return observations


def save(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    tmp.replace(str(path))


def output(argv):
    return subprocess.check_output(argv, universal_newlines=True, timeout=60)


def main():
    import fcntl
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('config', type=Path)
    p.add_argument('out', type=Path)
    args = p.parse_args()
    assert args.out.is_dir()
    config = read(args.config)
    base = Path(config['base'])
    validate(config, base)
    assert args.out.resolve().parent == base.resolve()
    lock = (args.out / 'controller.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    config_sha, code_sha = sha(args.config), sha(Path(__file__))
    previous = None
    while True:
        stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        status = dict(observed_utc=stamp, controller_source_sha256=code_sha,
                      config_sha256=config_sha, runs={}, new_allocations=[],
                      scope='Admission only; existing dispatcher enforces global reservations. No retry, cancellation, EDA or qualification.')
        try:
            assert sha(args.config) == config_sha and sha(Path(__file__)) == code_sha
            validate(config, base)
            for row in config['runs']:
                root = base / row['run_id']
                assert not (root / 'retired.json').exists()
                module_path = root / 'src/project/experiments/block_v1/native_node_queue.py'
                module_spec = importlib.util.spec_from_file_location('admission_dependency', str(module_path))
                module = importlib.util.module_from_spec(module_spec)
                module_spec.loader.exec_module(module)
                dispatch = read(root / 'dispatch-state.json')
                state = classify(read(root / 'node-queue.json'), read(root / 'node-queue-state.json'),
                                 dispatch, module.dependency)
                if state == 'already_dispatched':
                    observed = allocation_observation(dispatch['tasks'])
                    status.setdefault('allocations', {})[row['run_id']] = observed
                    if any(v == 'uncertain_submission' or v in SLURM_TERMINAL for v in observed.values()):
                        state = 'needs_attention'
                status['runs'][row['run_id']] = state
                if state != 'ready':
                    continue
                # Requery before every possible mutation. Other members' jobs
                # are untouched; pending own jobs count equally with running.
                lines = output(['squeue', '-h', '-u', 'yuzelu', '-o', '%i|%j|%T']).splitlines()
                issue_job_ids = set()
                for path in base.glob('block-v1-*/dispatch-state.json'):
                    assert path.resolve().parent.parent == base.resolve()
                    recorded = read(path)
                    assert recorded['run_id'] == path.parent.name
                    issue_job_ids.update(str(x['job_id']) for x in recorded['tasks'].values() if x.get('job_id'))
                # This is an issue budget, not a whole-account budget. Unknown
                # reservations remain fail-closed in the original dispatcher.
                own = own_allocations(lines, issue_job_ids)
                status['own_live_allocations'] = own
                if len(own) >= config['max_allocations']:
                    status['runs'][row['run_id']] = 'ready_at_allocation_cap'
                    continue
                raw = output(['python3', str(root / 'src/project/experiments/block_v1/dispatch.py'),
                              str(root / 'manifest.json'), '--submit'])
                submitted = json.loads(raw)
                status['new_allocations'].append(dict(run_id=row['run_id'], state=submitted))
                status['runs'][row['run_id']] = 'dispatched' if submitted['tasks'] else 'dispatcher_deferred'
            terminal = {'passed', 'needs_attention', 'dependency_failed'}
            status['state'] = 'finished' if all(v in terminal for v in status['runs'].values()) else 'watching'
        except Exception as exc:
            # A timeout is an observation error, never an empty allocation or
            # permission to retry sbatch. Persisted reservations are untouched.
            status['state'] = 'observation_error'
            status['error'] = type(exc).__name__ + ': ' + str(exc)
        save(args.out / 'status.json', status)
        signature = json.dumps({k:v for k,v in status.items() if k not in ('observed_utc', 'new_allocations')}, sort_keys=True)
        if signature != previous or status['new_allocations']:
            with (args.out / 'events.jsonl').open('a') as stream:
                stream.write(json.dumps(status, sort_keys=True) + '\n')
            previous = signature
        if status['state'] == 'finished':
            return
        time.sleep(config['interval_seconds'])


if __name__ == '__main__':
    main()
