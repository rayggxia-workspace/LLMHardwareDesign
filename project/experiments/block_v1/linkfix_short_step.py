"""Finite opportunistic route or electrical checks in proved-spare CPU slots.

No full native reception is admitted here. The immutable parent
batch does not track this step's lifetime: interruption grants no unfinished
qualification; only each completely closed, hash-verified child receipt counts.
Full native qualification remains on the ordinary shared dispatcher; a diagnostic
electrical pipeline grants no missing native DRC/PG/LEC acceptance.
"""
import json,os,subprocess,sys
from pathlib import Path
from native_node_queue import sha


def width(tasks,states):
    bad={k for k,v in states.items()if v.get('status')in('FAILED','BLOCKED')}
    while True:
        old=len(bad);bad.update(t['id']for t in tasks if set(t.get('after',[]))&bad)
        if len(bad)==old:break
    remaining={t['id']:t for t in tasks if t['id']not in bad and states.get(t['id'],{}).get('status')!='PASSED'}
    ancestors={}
    def before(k):
        if k not in ancestors:
            a=set(remaining[k].get('after',[]))&set(remaining)
            for p in list(a):a.update(before(p))
            ancestors[k]=a
        return ancestors[k]
    matched={}
    def augment(k,seen):
        for p in before(k):
            if p in seen:continue
            seen.add(p)
            if p not in matched or augment(matched[p],seen):matched[p]=k;return True
        return False
    return len(remaining)-sum(augment(k,set())for k in remaining)


def serve(root):
    from native_cohost_queue import foreign_tree,reserve_memory
    from native_allocation_group import memory_snapshot
    binding_path=root.parent/'opportunistic.json';binding=json.loads(binding_path.read_text())
    assert binding['job_id']==os.environ['SLURM_JOB_ID']=='93369'
    parent=Path(binding['parent_queue']);assert sha(parent)==binding['parent_queue_sha256']
    pq=json.loads(parent.read_text());state_path=Path(pq['state_path']);live_path=parent.parent/'tasks/native-node-queue/queue-live.json'
    assert sha(parent.parent/'src/project/experiments/block_v1/native_node_queue.py')==sha(root/'project/experiments/block_v1/native_node_queue.py')
    allocated=sorted(os.sched_getaffinity(0));assert len(allocated)==96
    electrical=binding.get('pipeline')=='electrical'
    foreign,spare=allocated[:64],allocated[64:96 if electrical else 80];records=[];samples=[]
    def check():
        assert sha(parent)==binding['parent_queue_sha256']
        states=json.loads(state_path.read_text())['tasks'];w=width(pq['tasks'],states);assert w<=4
        live=json.loads(live_path.read_text());assert live['owner']['job_id']==binding['job_id']
        assert all(set(v)<=set(foreign)for v in live['cpu_affinities'].values())
        actual=foreign_tree(live['owner']['pid'],foreign,binding['job_id'])
        mem,reserved=reserve_memory(memory_snapshot(),96,actual['rss_bytes'])
        assert min(mem['MemAvailable'],mem['MemTotal'])>(len(spare)*1.2+16)*1024**3
        samples.append(dict(parent_width=w,parent_rss=actual['rss_bytes'],parent_reserved_bytes=reserved))
    check();os.sched_setaffinity(0,spare)
    def execute(mode,report,cpus):
        check();out=root.parent/'tasks'/mode;out.mkdir(parents=True,exist_ok=False)
        env=dict(os.environ,SLURM_CPUS_PER_TASK='16',OMP_NUM_THREADS='16')
        with (out/'short-step.log').open('w')as log:
            result=subprocess.run(['taskset','--cpu-list',','.join(map(str,cpus)),'bash',str(root/'project/experiments/block_v1/worker.sh'),str(root),mode],cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT)
        r=json.loads((out/'receipt.json').read_text());assert result.returncode==0 and r['passed']and r['cpus']==16 and r['mode']==mode
        p=out/report;assert sha(p)==r['outputs'][report]and json.loads(p.read_text())['passed']
        records.append(dict(mode=mode,receipt_sha256=sha(out/'receipt.json'),report_sha256=sha(p),cpu_affinity=cpus))
    sequential=([('linkfix-io-view-t','linkfix-io-view.json'),('linkfix-io-view-s','linkfix-io-view.json'),
                 ('linkclose-route-tq2','linkclose-route.json'),('linkclose-prepare-tq2','linkclose-prepare.json')]if electrical else
                [('linkclose-route-tf9','linkclose-route.json'),('linkfix-geometry-tf9','linkfix-geometry.json')])
    for mode,report in sequential:execute(mode,report,spare[:16])
    if electrical:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
            first=pool.submit(execute,'linkclose-case-tq2-guarded','linkclose-result.json',spare[:16])
            second=pool.submit(execute,'linkclose-case-tq2-opposite','linkclose-result.json',spare[16:])
            done,_=concurrent.futures.wait([first,second],return_when=concurrent.futures.FIRST_COMPLETED)
            finished=next(iter(done));finished.result()
            next_cpus=spare[:16]if finished is first else spare[16:]
            third=pool.submit(execute,'linkclose-case-tq2-grounded','linkclose-result.json',next_cpus)
            first.result();second.result();third.result()
    report_name='opportunistic-electrical-step.json'if electrical else'opportunistic-short-step.json'
    (root.parent/report_name).write_text(json.dumps(dict(passed=True,new_allocation=False,
        allocated_cpus=allocated,parent_cpus=foreign,short_step_cpus=spare,maximum_combined_cpu_ceiling=64+len(spare),
        binding_sha256=sha(binding_path),samples=samples,closed_children=records,
        scope='Finite closed route/geometry or electrical diagnostic receipts only. Native complete acceptance is a separate final gate. Parent lifetime is not extended; any interrupted child grants no qualification and requires a new task directory for retry.'),indent=2)+'\n')

if __name__=='__main__':serve(Path(sys.argv[1]))
