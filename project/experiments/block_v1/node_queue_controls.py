"""Isolated scheduler controls; declared CPU slots are not a speedup benchmark.

Run on Linux (fcntl), without EDA or Slurm: python3 node_queue_controls.py.
Uses the production scheduler and real overlapping timed worker stand-ins.
"""
import concurrent.futures
import copy
import json
from pathlib import Path
import tempfile
import threading
import time
from native_node_queue import Store,dependency,schedule,validate


def main():
    with tempfile.TemporaryDirectory(prefix='bv1-queue-controls-')as temporary:
        base=Path(temporary);run=base/'run';out=run/'tasks/native-node-queue';out.mkdir(parents=True)
        def task(i):
            return dict(id=str(i),mode='task-'+str(i),cwd=str(run/'tasks'/('task-'+str(i))),
                source=str(run/'src'),cpus=16,memory_gib=1,memory_basis='Synthetic admission-control fixture',
                report='proof.json',after=[],receipts=[])
        tasks=[task(i)for i in range(9)]
        spec=dict(schema='block-v1-node-queue/1',node_cpus=96,default_task_cpus=16,memory_guard_gib=1,
            state_path=str(run/'node-queue-state.json'),tasks=tasks)
        validate(spec,base)
        timeline={};lock=threading.Lock();active=0;maximum=0
        def execute(t,unused):
            nonlocal active,maximum
            with lock:
                timeline[t['id']]=dict(start=time.time());active+=1;maximum=max(maximum,active)
            time.sleep(1.5 if t['id']=='0'else .15)
            with lock:timeline[t['id']]['finish']=time.time();active-=1
            return dict(passed=t['id']!='1')
        # The failed task does not cancel its independent peers. Its dependent
        # task is blocked; task 7 must refill before the slow first task ends.
        tasks[-1]['after']=['1']
        result=schedule(spec,'fixture',out,dict(job_id='control',node='local',worker=str(out),pid=0),
            lambda:dict(MemTotal=128*1024**3,MemAvailable=128*1024**3),execute)
        state=Store(spec['state_path'],'fixture').read()
        assert maximum==6 and result['maximum_concurrent_tasks']==6
        assert result['maximum_concurrent_task_cpu_ceilings']==96
        assert timeline['7']['start']<timeline['0']['finish'],'Refill waited for slowest task'
        assert state['tasks']['1']['status']=='FAILED'and state['tasks']['8']['status']=='BLOCKED'
        assert all(state['tasks'][str(i)]['status']=='PASSED'for i in [0,2,3,4,5,6,7])
        assert not result['passed']

        # Multiple allocation owners race for the same shared file lock.
        other=run/'race';other.mkdir();store=Store(other/'node-queue-state.json','race')
        def claim(i):return store.claim(tasks,dict(worker=i),96,128*1024**3)[0]
        with concurrent.futures.ThreadPoolExecutor(max_workers=12)as pool:claims=list(pool.map(claim,range(12)))
        ids=[t['id']for t in claims if t]
        assert len(ids)==len(set(ids))==8
        assert len(store.read()['tasks'])==8

        # Actual available memory is recorded alongside the admission budget.
        memory=Store(other/'memory.json','memory')
        item,done,reasons=memory.claim([task(0)],dict(worker=0),96,1024**3)
        assert item is None and not done and reasons['0']['reason']=='resource'
        assert reasons['0']['required_memory_with_margin_bytes']>reasons['0']['free_memory_bytes']
        assert reasons['0']['basis']=='Synthetic admission-control fixture'
        assert not memory.read()['tasks']

        d=task(0);p=run/'tasks/upstream/receipt.json';p.parent.mkdir()
        d['receipts']=[dict(path=str(p),mode='upstream')]
        assert dependency(d,{})[0]=='waiting'
        p.write_text(json.dumps(dict(mode='upstream',passed=False)))
        assert dependency(d,{})[0]=='failed'
        p.write_text(json.dumps(dict(mode='upstream',passed=True)))
        assert dependency(d,{})[0]=='ready'
        p.unlink();producer=run/'dispatch-state.json'
        producer.write_text(json.dumps(dict(tasks={'upstream':dict(state='RUNNING')})))
        d['receipts'][0].update(producer_state=str(producer),producer_task='upstream')
        assert dependency(d,{})[0]=='waiting'
        producer.write_text(json.dumps(dict(tasks={'upstream':dict(state='OUT_OF_MEMORY',exit_code='0:125')})))
        assert dependency(d,{})[0]=='failed'
        parked_run=base/'parked';parked_out=parked_run/'tasks/native-node-queue';parked_out.mkdir(parents=True)
        parked_spec=copy.deepcopy(spec);parked_spec['tasks']=[d]
        parked_spec['state_path']=str(parked_run/'node-queue-state.json')
        # A still-running producer gives a real dependency wait. No empty
        # allocation is held while waiting, and the task remains unclaimed.
        producer.write_text(json.dumps(dict(tasks={'upstream':dict(state='RUNNING')})))
        parked=schedule(parked_spec,'parked',parked_out,dict(worker='parked'),
            lambda:dict(MemTotal=128*1024**3,MemAvailable=128*1024**3),execute)
        assert parked['passed']and parked['parked_for_external_dependencies']and not parked['queue_all_tasks_passed']
        assert not Store(parked_spec['state_path'],'parked').read()['tasks']
        cyclic=copy.deepcopy(spec);cyclic['tasks'][0]['after']=['2'];cyclic['tasks'][2]['after']=['0']
        try:validate(cyclic,base)
        except AssertionError:pass
        else:raise AssertionError('Dependency cycle accepted')
        proof=dict(passed=True,scope='Production scheduler with timed stand-ins; not EDA/CPU scaling evidence',
            first_wave='6 x 16 declared CPU slots',maximum_concurrent_tasks=maximum,
            immediate_refill_before_slowest=True,independent_peers_complete_after_failure=True,
            dependency_failure_blocked=True,multi_owner_unique_claims=len(ids),memory_evidence_recorded=True,
            missing_receipt_is_waiting=True,authoritative_terminal_failure_rejected=True,cycle_rejected=True,
            empty_node_released_for_external_dependency=True,
            timeline=timeline)
        print(json.dumps(proof,indent=2))


if __name__=='__main__':main()
