"""Dynamic16CPU final-gate DAG, two independent workers when actual RAM fits.

Failed checks remain failures, while independent checks continue for diagnosis.
Nothing in this runner calls an accepted/done status or relaxes a gate.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import json
import os
from pathlib import Path
from queue import Queue
import subprocess
import sys
import time

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
p.add_argument('--native',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
cpus=sorted(os.sched_getaffinity(0));assert len(cpus)>=32
m=dict(s.split(':',1) for s in Path('/proc/meminfo').read_text().splitlines());available=int(m['MemAvailable'].split()[0])*1024
# Actual old C8 run080 MaxRSS180451804KiB, inherited only as scheduling evidence.
# It is not a claim of acceptance or measured memory for these new macros.
prior=180451804*1024;guard=16*1024**3
n=2 if available>=2*prior*1.2+guard else 1 if available>=prior*1.2+guard else 0
assert n>0,'Actual node memory cannot admit one guarded receiver'
(a.out/'memory-admission.json').write_text(json.dumps(dict(available_bytes=available,parallel=n,
    reference_maxrss_bytes=prior,headroom=1.2,node_guard_bytes=guard,reference='old C8 run080, scheduling bound only'),indent=2)+'\n')
free=Queue()
for i in range(n):free.put(cpus[16*i:16*(i+1)])
tasks={}
for macro in ['m','s']:
    top='block_feed_m' if macro=='m' else 'block_feed_s_macro'
    seal=a.out/('source-'+macro)
    tasks['seal-'+macro]=dict(args=['seal','--source',str(a.native/top),'--out',str(seal)],deps=[])
    for op in ['physical','drc','function','formal']:
        args=[op,'--source',str(seal),'--out',str(a.out/(op+'-'+macro))]
        deps=['seal-'+macro]
        if op=='function' and macro=='s':args+=['--peer',str(a.out/'source-m')];deps+=['seal-m']
        if op=='formal':args+=['--function',str(a.out/('function-'+macro))];deps+=['function-'+macro]
        tasks[op+'-'+macro]=dict(args=args,deps=deps)
def one(name):
    selected=free.get();started=time.time()
    try:
        cmd=['taskset','-c',','.join(map(str,selected)),sys.executable,str(a.root/'project/experiments/block_feed_v1/qualify.py'),*tasks[name]['args']]
        with (a.out/(name+'.log')).open('w') as stream:q=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT)
        return dict(returncode=q.returncode,passed=q.returncode==0,cpus=selected,seconds=time.time()-started)
    finally:free.put(selected)
done={};running={};pending=set(tasks)
def save():(a.out/'queue-result.json').write_text(json.dumps(dict(passed=len(done)==len(tasks) and all(x['passed'] for x in done.values()),tasks=done),indent=2)+'\n')
with ThreadPoolExecutor(max_workers=n) as pool:
    while pending or running:
        for name in sorted(pending):
            if name.startswith('seal-'):
                top='block_feed_m' if name=='seal-m' else 'block_feed_s_macro'
                candidate=a.native/top
                if not (candidate/'receipt.json').exists():
                    if not (a.native/'queue-result.json').exists():continue
                    pending.remove(name);done[name]=dict(passed=False,missing_completed_native_receipt=True);save();continue
            if not all(d in done for d in tasks[name]['deps']):continue
            pending.remove(name)
            if not all(done[d]['passed'] for d in tasks[name]['deps']):done[name]=dict(passed=False,blocked_by_failed_dependencies=True);save();continue
            running[pool.submit(one,name)]=name
        if running:
            finished,_=wait(running,return_when=FIRST_COMPLETED)
            for f in finished:
                name=running.pop(f);done[name]=f.result();print(name,json.dumps(done[name]),flush=True);save()
        elif pending:
            assert any(name.startswith('seal-') for name in pending),'Unresolvable dependency DAG'
            time.sleep(30)
save();sys.exit(not all(x['passed'] for x in done.values()))
