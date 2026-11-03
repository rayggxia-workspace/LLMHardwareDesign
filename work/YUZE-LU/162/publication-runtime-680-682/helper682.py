from pathlib import Path
import subprocess,shlex
q=r'''from pathlib import Path
import json,subprocess,time,hashlib,concurrent.futures
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-current-pool-cpu-observation-682';assert not out.exists();audit=b/'r256-directional-bidirectional-active-pool-audit-674/receipt.json';a=json.loads(audit.read_text());assert a['passed'];rows=[]
for p in a['pools']:
 details=subprocess.check_output(['scontrol','show','job',str(p['job']),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node'+str(p['node'])+' 'in details
def one(pool):
 expected={str(x['pid']):x['binary']for x in pool['actual_processes']}
 code="import os,time,json\nexpected="+repr(expected)+"\ndef snap():\n d={}\n for pid,exe in expected.items():\n  try:\n   base='/proc/'+pid;assert os.stat(base).st_uid==10011 and os.readlink(base+'/exe')==exe\n   z=open(base+'/stat').read().rsplit(') ',1)[1].split();d[pid]=dict(ticks=int(z[11])+int(z[12]),state=z[0],affinity=sorted(os.sched_getaffinity(int(pid))))\n  except(OSError,AssertionError):pass\n return d\na=snap();t=time.monotonic();time.sleep(2);c=snap();elapsed=time.monotonic()-t;hz=os.sysconf('SC_CLK_TCK');print(json.dumps(dict(elapsed=elapsed,hz=hz,rows=[dict(pid=pid,binary=expected[pid],cpu_cores=(c[pid]['ticks']-a[pid]['ticks'])/hz/elapsed,state=c[pid]['state'],affinity=c[pid]['affinity'])for pid in a if pid in c])))"
 data=json.loads(subprocess.check_output(['srun','--jobid='+str(pool['job']),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));assert len(data['rows'])==16 and all(len(x['affinity'])==16 for x in data['rows']);return dict(job=pool['job'],node=pool['node'],observation=data)
with concurrent.futures.ThreadPoolExecutor(max_workers=5)as ex:rows=list(ex.map(one,a['pools']))
out.mkdir();r=dict(passed=True,time=time.time(),whole_system_qualified=False,actual_processes=sum(len(x['observation']['rows'])for x in rows),pools=rows,input_audit=dict(path=str(audit),sha256=hashlib.sha256(audit.read_bytes()).hexdigest()),scope='Read-only2second CPU tick observations of exactly80 same UID/executable PIDs from actual674; no claim about all576cores or long-term utilization, no task/pin/affinity modification and no physical acceptance.')
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(passed=True,processes=r['actual_processes'],summed_observed_cores=sum(z['cpu_cores']for x in rows for z in x['observation']['rows']),per_pool=[dict(node=x['node'],cores=sum(z['cpu_cores']for z in x['observation']['rows']),states=sorted(set(z['state']for z in x['observation']['rows'])))for x in rows])))
'''
compile(q,'remote682','exec')
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
