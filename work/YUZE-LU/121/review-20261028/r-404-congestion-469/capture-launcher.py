from pathlib import Path
import subprocess,shlex,json
inner=r'''from pathlib import Path
import json,hashlib,re,collections,os,time
assert 'job_93555'in Path('/proc/self/cgroup').read_text()
p=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-404/tasks/revision300-route-r/flow/reports/nangate45/bv1_block_v1_r/base');rows=[]
for n in (5,10,15,20):
 f=p/('congestion-'+str(n)+'.rpt');raw=f.read_bytes();before=hashlib.sha256(raw).hexdigest();text=raw.decode();groups=collections.defaultdict(list)
 for marker in text.split('violation type: ')[1:]:
  direction=marker.splitlines()[0];m=re.search(r'comment: capacity:(\d+) usage:(\d+) congestion:(\d+)',marker);assert m,marker[:200]
  capacity,usage,excess=map(int,m.groups());assert usage-capacity==excess and excess>0
  groups[direction].append((capacity,usage,excess))
 rows.append(dict(iteration=n,path=str(f),bytes=len(raw),sha256=before,unchanged_after=hashlib.sha256(f.read_bytes()).hexdigest()==before,directions={k:dict(congested_edges=len(v),sum_overflow=sum(x[2]for x in v),maximum_overflow=max(x[2]for x in v),sum_congested_edge_capacity=sum(x[0]for x in v),sum_congested_edge_usage=sum(x[1]for x in v))for k,v in groups.items()}))
assert all(x['unchanged_after']for x in rows)
print(json.dumps(dict(captured_unix=time.time(),parent_job='93555',node=os.uname().nodename,actual_affinity=sorted(os.sched_getaffinity(0)),read_only=True,rows=rows,scope='Actual R404 existing GRT iteration reports only. Two-dimensional congestion projection, not per-layer demand or final native DRC. No EDA rerun/source/config changes or failure inference from elapsed time.')))
'''
remote="import subprocess;subprocess.run("+repr(['srun','--jobid=93555','--overlap','--ntasks=1','--cpus-per-task=96','--cpu-bind=none','--time=1','taskset','--cpu-list','16-31','python3','-c',inner])+",check=True)"
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(remote)]));p=Path('.local/issue121/r404-congestion-469.json');assert not p.exists();p.write_bytes((json.dumps(d,indent=2)+'\n').encode())
for r in d['rows']:print(r['iteration'],r['directions'])
