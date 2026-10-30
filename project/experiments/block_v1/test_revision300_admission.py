"""Admission safety checks; pure control-plane data, no Slurm or EDA calls."""
from revision300_admission import classify, own_allocations, recorded_job_ids, RUNS, validate
from pathlib import Path
import hashlib
import tempfile


def check():
    queue = dict(tasks=[dict(id='physical'), dict(id='geometry')])
    def ready(task, states):
        return ('ready', []) if task['id'] == 'physical' else ('waiting', [])
    assert classify(queue, {}, {}, ready) == 'ready'
    # Unknown submission outcome is a reservation, never a free retry slot.
    for old in ({'state':'SUBMITTING'}, {'state':'FAILED','job_id':'123'},
                {'state':'COMPLETED','job_id':'123'}):
        assert classify(queue, {}, dict(tasks={'native-node-queue':old}), ready) == 'already_dispatched'
    assert classify(queue, dict(tasks={'physical':{'status':'FAILED'}}), {}, ready) == 'needs_attention'
    assert classify(queue, dict(tasks={'physical':{'status':'PASSED'},'geometry':{'status':'PASSED'}}), {}, ready) == 'passed'
    assert classify(queue, {}, {}, lambda t,s:('waiting', [])) == 'waiting_dependency'
    assert classify(queue, {}, {}, lambda t,s:('failed', [])) == 'dependency_failed'
    lines = [str(n)+'|yzl-block|'+('PENDING' if n == 0 else 'RUNNING') for n in range(8)]
    issue_ids = set(map(str, range(8)))
    assert len(own_allocations(lines+['20|hpy-block|RUNNING','99|yzl-unrelated|RUNNING'], issue_ids)) == 8
    assert len(own_allocations(lines[:-1], issue_ids)) == 7
    # The actual failed460 wrapper recorded422. Preserve its job in the budget,
    # including PENDING; never rewrite it or silently drop its allocation.
    jobs, mismatches = recorded_job_ids([
        ('block-v1-460', dict(run_id='block-v1-422', tasks={
            'queue': dict(job_id='93606'), 'unknown': dict(state='SUBMITTING')})),
        ('block-v1-464', dict(run_id='block-v1-464', tasks={'queue': dict(job_id='93610')}))])
    assert jobs == {'93606', '93610'}
    assert mismatches == {'block-v1-460': 'block-v1-422'}
    assert len(own_allocations(['93606|yzl-block|PENDING', '93610|yzl-block|RUNNING'], jobs)) == 2
    try:
        recorded_job_ids([('unrelated', dict(run_id='block-v1-422', tasks={}))])
    except AssertionError:
        pass
    else:
        raise AssertionError('Accounting must remain in the issue run namespace')
    try:
        own_allocations(['observation interrupted'], issue_ids)
    except AssertionError:
        pass
    else:
        raise AssertionError('Malformed observation must not become an empty allocation list')
    # Test the exact production queue allowlist before a controller is launched.
    assert RUNS == tuple('block-v1-20261030-'+n for n in
                         ('404','405','406','494','495','505','506','507','508','509'))
    with tempfile.TemporaryDirectory() as directory:
        base=Path(directory).resolve()/'issue-121';base.mkdir()
        config=dict(schema='revision300-admission/1',max_allocations=8,
                    interval_seconds=60,runs=[])
        for run_id in RUNS:
            files={}
            for name in ('manifest.json','node-queue.json',
                         'src/project/experiments/block_v1/dispatch.py',
                         'src/project/experiments/block_v1/native_node_queue.py'):
                path=base/run_id/name;path.parent.mkdir(parents=True,exist_ok=True)
                data=(run_id+name).encode();path.write_bytes(data)
                files[name]=hashlib.sha256(data).hexdigest()
            config['runs'].append(dict(run_id=run_id,files=files))
        validate(config,base)
        config['runs'][-1]['run_id']='block-v1-20261030-478'
        try:
            validate(config,base)
        except AssertionError:
            pass
        else:
            raise AssertionError('Old queue must be rejected before launch')
    print('PASS: reservation/terminal attempts never resubmit; dependency, failure and complete checks')


if __name__ == '__main__':
    check()
