"""Python3.6+ standard-library-only parallel replay on an allocated CPU node."""
import argparse
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import platform
import time
from model import build,audit_schedule

def worker(case):
    g=build(case['rows'],case['K'],case['scale_mode'],case['placement'],case['lanes'],
            case['window'],case['consumer_cost'],case['jobs'])
    s=g.schedule(case['policy']);a=audit_schedule(g,s)
    return dict(name=case['name'],cycles=s['cycles'],busy=s['busy'],traffic=dict(g.bytes),audit=a)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--workers',type=int,required=True)
    a=p.parse_args();root=a.root.resolve()
    if not str(root).startswith('/public/home/yuzelu/RuizhiLiang/issue51-rq-ports-20261023/'):raise ValueError('owner workspace required')
    allocated=int(os.environ.get('SLURM_CPUS_PER_TASK','0'))
    if not 1<=a.workers<=allocated:raise ValueError('worker allocation')
    manifest=json.loads((root/'bundle-manifest.json').read_text())
    for name,expected in manifest['files'].items():
        raw=(root/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected['sha256'] or len(raw)!=expected['bytes']:raise ValueError('source/input SHA '+name)
    output=root/'server-results'
    if output.exists():raise ValueError('refuse overwrite')
    output.mkdir();cases=json.loads((root/'cases.json').read_text())
    environment={'host':platform.node(),'python':platform.python_version(),'job_id':os.environ.get('SLURM_JOB_ID'),
        'allocated_cpus':allocated,'workers':a.workers,'source_commit':manifest['source_commit'],
        'modules':{n:importlib.util.find_spec(n) is not None for n in ('numpy','torch','transformers')},
        'cpuinfo':Path('/proc/cpuinfo').read_text(),'meminfo':Path('/proc/meminfo').read_text()}
    (output/'environment.json').write_text(json.dumps(environment,indent=2)+'\n')
    started=time.time();results=[]
    with multiprocessing.Pool(a.workers) as pool:
        for result in pool.imap_unordered(worker,cases,chunksize=1):
            results.append(result)
            # Individual completed cases survive a later failure or scheduler limit.
            (output/('case-%03d.json'%cases.index(next(c for c in cases if c['name']==result['name'])))).write_text(json.dumps(result,sort_keys=True)+'\n')
    results.sort(key=lambda x:x['name'])
    (output/'runs.json').write_text(json.dumps(results,indent=2,sort_keys=True)+'\n')
    summary={'status':'PASS','runs':len(results),'elapsed_seconds':time.time()-started,'source_commit':manifest['source_commit']}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    files={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in output.iterdir() if p.is_file()}
    (output/'manifest.json').write_text(json.dumps({'files':files,'summary':summary},indent=2,sort_keys=True)+'\n')
    print(json.dumps(summary))

if __name__=='__main__':main()
