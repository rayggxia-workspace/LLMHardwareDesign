"""Dynamic issue130 physical queue; hard16CPU child affinity, actual RAM guard."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import sys

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--mapping',type=Path,required=True)
a=p.parse_args();cpus=sorted(os.sched_getaffinity(0));assert len(cpus)>=32
n=json.loads((a.out/'memory-admission.json').read_text())['parallel'];assert n in (1,2)
groups=[cpus[i*16:(i+1)*16] for i in range(n)]
from queue import Queue
free=Queue()
for g in groups:free.put(g)
def task(top):
    g=free.get()
    try:
        cmd=['taskset','-c',','.join(map(str,g)),sys.executable,str(a.root/'project/experiments/block_feed_v1/physical.py'),
             '--top',top,'--out',str(a.out/top),'--mapping',str(a.mapping)]
        with (a.out/(top+'.log')).open('w') as stream:
            q=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT)
        return dict(top=top,returncode=q.returncode,cpus=g)
    finally:free.put(g)
results=[]
with ThreadPoolExecutor(max_workers=n) as pool:
    for f in as_completed([pool.submit(task,t) for t in ('block_feed_m','block_feed_s_macro')]):
        result=f.result();results.append(result);print(json.dumps(result),flush=True)
(a.out/'queue-result.json').write_text(json.dumps(dict(passed=all(r['returncode']==0 for r in results),tasks=results),indent=2)+'\n')
sys.exit(any(r['returncode'] for r in results))
