"""Prove a scheduler-only SIGINT drains its existing executor on Linux.

Uses the unchanged production scheduler and a real subprocess stand-in. This
does not qualify EDA, recover queue state, or signal any production process.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def child(module_dir, out):
    sys.path.insert(0, str(module_dir))
    from native_node_queue import schedule, validate
    base = out / 'sandbox'
    run = base / 'run'
    worker_out = run / 'tasks/native-node-queue'
    worker_out.mkdir(parents=True)
    tasks = [dict(id=name, mode=name, cwd=str(run / 'tasks' / name),
                  source=str(run / 'src'), cpus=16, memory_gib=1,
                  memory_basis='Timed subprocess drain control', report='proof.json',
                  after=[] if name == 'active' else ['active'], receipts=[])
             for name in ['active', 'later']]
    spec = dict(schema='block-v1-node-queue/1', node_cpus=96,
                default_task_cpus=16, memory_guard_gib=1,
                state_path=str(run / 'node-queue-state.json'), tasks=tasks)
    validate(spec, base)

    def execute(task, unused):
        assert task['id'] == 'active', 'Drain claimed new work'
        code = ('import json,time;from pathlib import Path;'
                'time.sleep(1.5);Path(__import__("sys").argv[1]).write_text('
                'json.dumps(dict(completed=time.time())))')
        process = subprocess.Popen([sys.executable, '-c', code, str(out / 'finished.json')])
        (out / 'started.json').write_text(json.dumps(dict(pid=process.pid, time=time.time())))
        assert process.wait() == 0
        return dict(passed=True)

    try:
        schedule(spec, 'drain-control', worker_out,
                 dict(pid=os.getpid(), worker='control'),
                 lambda: dict(MemTotal=128 * 1024**3, MemAvailable=128 * 1024**3), execute)
        raise AssertionError('Expected scheduler-only KeyboardInterrupt')
    finally:
        (out / 'scheduler-finally.json').write_text(json.dumps(dict(time=time.time())))


def main():
    module_dir = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve()
    if sys.argv[3:] == ['--child']:
        child(module_dir, out)
        return
    assert not sys.argv[3:]
    out.mkdir(parents=True, exist_ok=False)
    with (out / 'child.log').open('w') as log:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                                    str(module_dir), str(out), '--child'], stdout=log,
                                   stderr=subprocess.STDOUT)
        deadline = time.time() + 10
        while not (out / 'started.json').exists():
            assert process.poll() is None and time.time() < deadline
            time.sleep(.01)
        before = time.time()
        os.kill(process.pid, signal.SIGINT)
        code = process.wait(timeout=10)
    assert code != 0
    finished = json.loads((out / 'finished.json').read_text())['completed']
    final = json.loads((out / 'scheduler-finally.json').read_text())['time']
    assert before < finished <= final, 'Scheduler exited before active subprocess completed'
    state = json.loads((out / 'sandbox/run/node-queue-state.json').read_text())
    assert set(state['tasks']) == {'active'} and state['tasks']['active']['status'] == 'RUNNING'
    assert 'KeyboardInterrupt' in (out / 'child.log').read_text()
    result = dict(passed=True, scheduler_module=str(module_dir / 'native_node_queue.py'),
                  scheduler_sha256=hashlib.sha256((module_dir / 'native_node_queue.py').read_bytes()).hexdigest(),
                  scheduler_returncode=code, signal_time=before,
                  active_subprocess_finished=finished, scheduler_finally=final,
                  no_new_task_claimed=True, existing_subprocess_completed=True,
                  abandoned_running_claim_requires_authoritative_recovery=True,
                  scope='SIGINT sent only to isolated scheduler PID; real subprocess survives and completes. No EDA or production signalling.')
    (out / 'drain-control.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
