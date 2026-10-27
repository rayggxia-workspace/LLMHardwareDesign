"""Shared candidate queue with immediate refill inside full-node allocations.

One Slurm allocation supplies 96 CPUs. Independent candidates claim work under
a common issue-local lock. No wave barrier, duplicate claim or peer cancellation.
"""
import concurrent.futures
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


TERMINAL={'PASSED','FAILED','BLOCKED'}


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for b in iter(lambda:stream.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def save(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)


def validate(spec,base):
    assert spec['schema']=='block-v1-node-queue/1' and spec['node_cpus']==96 and spec['default_task_cpus']==16
    ids={t['id']for t in spec['tasks']};assert len(ids)==len(spec['tasks']) and ids
    for t in spec['tasks']:
        assert t['cpus']in (1,2,4,8,12,16) and t['memory_gib']>0 and t['memory_basis']
        assert set(t.get('after',[]))<=ids-{t['id']}
        cwd=Path(t['cwd']);source=Path(t['source'])
        assert cwd.parent.name=='tasks' and cwd.parents[2]==base and source.name=='src' and source.parent.parent==base
        assert t['mode']==cwd.name and t['report'].endswith('.json')
        for d in t.get('receipts',[]):
            assert Path(d['path']).name=='receipt.json' and base in Path(d['path']).parents
            assert isinstance(d['mode'],str) and d['mode'],'Missing prerequisite receipt mode'
            assert isinstance(d.get('reports',[]),list)
            if d.get('producer_state'):
                assert base in Path(d['producer_state']).parents and d['producer_task']
    state=Path(spec['state_path']);assert state.parent.parent==base and state.name=='node-queue-state.json'
    remaining=list(spec['tasks']);done=set()
    while remaining:
        ready=[t for t in remaining if set(t.get('after',[]))<=done]
        assert ready,'Queue dependency cycle'
        done.update(t['id']for t in ready);remaining=[t for t in remaining if t not in ready]


def dependency(t,states):
    waiting=[]
    for key in t.get('after',[]):
        state=states.get(key,{})
        if state.get('status')in ('FAILED','BLOCKED'):return 'failed',[key]
        if state.get('status')!='PASSED':waiting.append(key)
    for d in t.get('receipts',[]):
        p=Path(d['path'])
        if not p.is_file():
            # Only authoritative producer terminal state permits failure. A
            # missing receipt, accounting lag or observation timeout does not.
            state_path=Path(d['producer_state'])if d.get('producer_state')else None
            if state_path and state_path.is_file():
                producer=json.loads(state_path.read_text())['tasks'].get(d['producer_task'],{})
                terminal={'COMPLETED','FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL','PREEMPTED','BOOT_FAIL','DEADLINE','REVOKED'}
                if producer.get('state')in terminal:return 'failed',[dict(receipt=str(p),producer=producer)]
            waiting.append(str(p));continue
        r=json.loads(p.read_text())
        assert r['mode']==d['mode'],'Wrong prerequisite receipt mode'
        if r.get('passed')is not True:return 'failed',[str(p)]
        for name in d.get('reports',[]):assert sha(p.parent/name)==r['outputs'][name]
    return ('waiting',waiting)if waiting else('ready',[])


class Store:
    def __init__(self,path,digest):self.path=Path(path);self.digest=digest
    @contextmanager
    def locked(self):
        import fcntl
        with self.path.with_suffix('.lock').open('a')as stream:
            fcntl.flock(stream,fcntl.LOCK_EX)
            state=json.loads(self.path.read_text())if self.path.exists()else dict(manifest_sha256=self.digest,tasks={},events=[])
            assert state['manifest_sha256']==self.digest,'Queue manifest changed; use a new queue'
            yield state
            save(self.path,state)
    def claim(self,tasks,owner,free_cpus,free_memory):
        with self.locked()as state:
            blocked={}
            for t in tasks:
                if t['id']in state['tasks']:continue
                status,reasons=dependency(t,state['tasks'])
                if status=='failed':
                    state['tasks'][t['id']]=dict(status='BLOCKED',reasons=reasons,finished=time.time());continue
                if status!='ready':blocked[t['id']]=dict(reason='dependency',prerequisites=reasons);continue
                required=int(t['memory_gib']*1024**3*1.2)
                if t['cpus']>free_cpus or required>free_memory:
                    blocked[t['id']]=dict(reason='resource',required_cpus=t['cpus'],free_cpus=free_cpus,
                        required_memory_with_margin_bytes=required,free_memory_bytes=free_memory,basis=t['memory_basis']);continue
                state['tasks'][t['id']]=dict(status='RUNNING',owner=owner,started=time.time(),cpus=t['cpus'],reserved_memory_bytes=required)
                state['events'].append(dict(event='claim',id=t['id'],owner=owner,time=time.time()))
                return t,False,blocked
            done=all(state['tasks'].get(t['id'],{}).get('status')in TERMINAL for t in tasks)
            return None,done,blocked
    def finish(self,t,result,owner):
        with self.locked()as state:
            entry=state['tasks'][t['id']];assert entry['status']=='RUNNING' and entry['owner']==owner
            entry.update(result,status='PASSED'if result['passed']else'FAILED',finished=time.time())
            state['events'].append(dict(event='finish',id=t['id'],owner=owner,time=time.time(),passed=result['passed']))
    def read(self):
        with self.locked()as state:return json.loads(json.dumps(state))


def execute(t,base):
    folder=Path(t['cwd']);folder.parent.mkdir(parents=True,exist_ok=True);folder.mkdir(exist_ok=False)
    source=Path(t['source']);allocated=t['cpus'];started=time.time()
    env=dict(os.environ,OMP_NUM_THREADS=str(allocated),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    command=['python3',str(source/'project/experiments/block_v1/worker.py'),str(source),t['mode'],str(allocated)]
    with(folder/'node-queue-child.log').open('w')as stream:
        process=subprocess.Popen(command,cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT)
        peaks={};peak_tree=0;samples=0
        while process.poll()is None:
            todo=[process.pid];seen=set();rss=0
            while todo:
                pid=todo.pop()
                if pid in seen:continue
                seen.add(pid);p=Path('/proc')/str(pid)
                try:
                    status=dict(line.split(':',1)for line in(p/'status').read_text().splitlines()if ':'in line)
                    current=int(status.get('VmRSS','0 kB').split()[0])*1024;rss+=current
                    peaks[pid]=max(peaks.get(pid,0),int(status.get('VmHWM','0 kB').split()[0])*1024)
                    for thread in(p/'task').iterdir():todo.extend(map(int,(thread/'children').read_text().split()))
                except (OSError,ValueError):pass
            peak_tree=max(peak_tree,rss);samples+=1;time.sleep(.5)
        code=process.returncode
    receipt=folder/'receipt.json';report=folder/t['report'];r=json.loads(receipt.read_text())if receipt.exists()else{}
    passed=bool(code==0 and r.get('passed')is True and r.get('cpus')==allocated and r.get('mode')==t['mode']and report.is_file())
    if passed:passed=sha(report)==r['outputs'][t['report']]and json.loads(report.read_text())['passed']is True
    return dict(passed=passed,returncode=code,started=started,finished=time.time(),argv=command,
        receipt_sha256=sha(receipt)if receipt.exists()else None,report_sha256=sha(report)if report.exists()else None,
        sampled_peak_tree_rss_bytes=peak_tree,sampled_process_vm_hwm_bytes=peaks,memory_samples=samples,
        memory_measurement_scope='500ms process-tree RSS sum and per-process VmHWM; samples may miss short peaks and shared pages may be counted more than once')


def schedule(spec,digest,out,owner,memory_snapshot,execute_task=execute):
    """Identical admission/refill path for production and isolated controls."""
    cpus=spec['node_cpus'];base=out.parents[2]
    store=Store(spec['state_path'],digest);futures={};completed=[];maximum_cpus=0;maximum_tasks=0;last=0;parked=False
    with concurrent.futures.ThreadPoolExecutor(max_workers=96)as pool:
        while True:
            for f in list(futures):
                if not f.done():continue
                t=futures.pop(f)
                try:result=f.result()
                except BaseException as error:result=dict(passed=False,error=repr(error))
                store.finish(t,result,owner);completed.append(dict(id=t['id'],**result))
            memory=memory_snapshot();active_cpus=sum(t['cpus']for t in futures.values())
            reserved=sum(int(t['memory_gib']*1024**3*1.2)for t in futures.values())
            free_memory=min(memory['MemAvailable']-spec['memory_guard_gib']*1024**3,memory['MemTotal']-spec['memory_guard_gib']*1024**3-reserved)
            t,done,blocked=store.claim(spec['tasks'],owner,cpus-active_cpus,max(0,free_memory))
            if t is not None:
                futures[pool.submit(execute_task,t,base)]=t
                maximum_cpus=max(maximum_cpus,active_cpus+t['cpus']);maximum_tasks=max(maximum_tasks,len(futures))
                continue
            if time.time()-last>=30:
                save(out/'queue-live.json',dict(time=time.time(),owner=owner,active=list(t['id']for t in futures.values()),
                    active_cpu_ceilings=active_cpus,maximum_tasks=maximum_tasks,memory=memory,reserved_memory_with_margin_bytes=reserved,
                    admission_blocked=blocked,manifest_sha256=digest));last=time.time()
            if done and not futures:break
            if not futures:
                # No runnable independent work remains on this allocation.
                # Persist the unclaimed dependency backlog, then release the
                # node. A new allocation may resume this same immutable queue.
                parked=True;break
            # FIRST_COMPLETED makes completed work free its resources at once;
            # no slow candidate holds the remainder of an otherwise empty wave.
            if futures:concurrent.futures.wait(futures,timeout=1,return_when=concurrent.futures.FIRST_COMPLETED)
    state=store.read();all_passed=all(state['tasks'].get(t['id'],{}).get('status')=='PASSED'for t in spec['tasks'])
    no_failures=all(v['status']not in ('FAILED','BLOCKED')for v in state['tasks'].values())
    result=dict(schema='block-v1-node-queue-result/1',passed=no_failures and (parked or all_passed),
        owner=owner,manifest_sha256=digest,state_path=spec['state_path'],state_sha256=sha(spec['state_path']),completed_here=completed,
        allocated_cpus=cpus,default_task_cpus=16,maximum_concurrent_task_cpu_ceilings=maximum_cpus,
        maximum_concurrent_tasks=maximum_tasks,allocation_parked=parked,
        parked_for_external_dependencies=parked and any(v['reason']=='dependency'for v in blocked.values()),
        parked_for_memory_or_cpu=parked and any(v['reason']=='resource'for v in blocked.values()),queue_all_tasks_passed=all_passed,
        admission_blocked=blocked,qualified_hard_macro=False,
        scope='Allocation scheduling only; successful parking does not qualify pending EDA tasks or any hard macro')
    (out/'native-node-queue.json').write_text(json.dumps(result,indent=2)+'\n');return result


def serve(root,out,cpus):
    from native_allocation_group import memory_snapshot
    assert cpus==96 and int(os.environ['SLURM_CPUS_PER_TASK'])==96
    base=out.parents[2];manifest=root.parent/'node-queue.json';digest=sha(manifest)
    spec=json.loads(manifest.read_text());validate(spec,base)
    # Queues are immutable once any allocation can claim work.
    def measured_memory():
        assert sha(manifest)==digest
        return memory_snapshot()
    owner=dict(job_id=os.environ['SLURM_JOB_ID'],node=os.uname().nodename,worker=str(out),pid=os.getpid())
    result=schedule(spec,digest,out,owner,measured_memory)
    assert result['passed'],'Queue contains failed/blocked tasks; no peer was cancelled'
