import datetime,json,shlex,subprocess
from pathlib import Path
remote=r"""
from pathlib import Path
import json,subprocess,time
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121');result=dict(time=time.time(),runs={})
inner=r'''
from pathlib import Path
import os,json,time,sys
root=int(sys.argv[1]);job=sys.argv[2]
assert 'job_'+job in(Path('/proc')/str(root)/'cgroup').read_text()
def snapshot():
 todo=[root];seen=set();rows=[]
 while todo:
  pid=todo.pop()
  if pid in seen:continue
  seen.add(pid);p=Path('/proc')/str(pid)
  try:
   s=dict(l.split(':',1)for l in(p/'status').read_text().splitlines()if ':'in l);assert int(s['Uid'].split()[0])==os.getuid()
   fields=(p/'stat').read_text().rsplit(')',1)[1].split();threads=[]
   for t in(p/'task').iterdir():
    threads.append(dict(tid=int(t.name),cpus=sorted(os.sched_getaffinity(int(t.name)))));todo.extend(map(int,(t/'children').read_text().split()))
   rows.append(dict(pid=pid,name=s['Name'].strip(),cpu_ticks=int(fields[11])+int(fields[12]),rss_kib=int(s.get('VmRSS','0 kB').split()[0]),threads=threads))
  except (OSError,ValueError):pass
 return dict(time=time.time(),rows=rows)
a=snapshot();time.sleep(1);print(json.dumps(dict(before=a,after=snapshot())))
'''
for number,job in [(870,'94496')]:
 b=base/('block-v1-20261101-'+str(number));q=json.loads((b/'tasks/native-node-queue/queue-live.json').read_text());o=q['owner'];assert o['job_id']==job
 r=json.loads(subprocess.check_output(['srun','--jobid='+job,'--overlap','--ntasks=1','--cpus-per-task=1','--time=1','python3','-c',inner,str(o['pid']),job],universal_newlines=True,timeout=20))
 result['runs'][str(number)]=dict(owner=o,live=q,samples=r)
print(json.dumps(result))
"""
r=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(remote)],timeout=48))
p=Path('.local/issue121')/('repair-progress-870-'+datetime.datetime.now().strftime('%H%M%S%f'));p.mkdir();(p/'index.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(p)
for n,v in r['runs'].items():
 old={x['pid']:x for x in v['samples']['before']['rows']};print('RUN',n,'active',v['live']['active'],'masks',v['live']['cpu_affinities'])
 groups={}
 for x in v['samples']['after']['rows']:
  if x['name']in('bash','make','python3','time','sh','g++','perl'):continue
  g=groups.setdefault(x['name'],dict(processes=0,cpu_ticks_delta=0,rss_kib=0,masks=set()));g['processes']+=1;g['cpu_ticks_delta']+=x['cpu_ticks']-old.get(x['pid'],x)['cpu_ticks'];g['rss_kib']+=x['rss_kib'];g['masks'].update(tuple(t['cpus'])for t in x['threads'])
 for name,g in groups.items():g['masks']=sorted(g['masks']);print(name,g)
