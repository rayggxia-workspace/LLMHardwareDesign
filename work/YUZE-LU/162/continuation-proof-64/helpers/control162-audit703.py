from pathlib import Path
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time,subprocess,traceback
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453/upper-candidates';out=b/'r256-directional-bidirectional-active-pool-audit-703';assert not out.exists();assert all((root/str(seed)/'route'/('trial-'+str(i))/'input.txt').exists()for seed in [6920,6921]for i in range(16));out.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();r=dict(passed=False,whole_system_qualified=False,time=time.time(),comparisons=[],pools=[])
try:
 for seed in [6920,6921]:
  for i in range(16):
   a=root/('5890/route'if seed==6920 else'6720/route')/('trial-'+str(i))/'input.txt';p=root/str(seed)/'route'/('trial-'+str(i))/'input.txt';assert p.read_bytes()==a.read_bytes();r['comparisons'].append(dict(seed=seed,trial=i,baseline=str(a),candidate=str(p),baseline_sha256=sha(a),candidate_sha256=sha(p),sole_input_difference='none_input_bytes_exact_weighted_flag_only'))
 for job,node,folder,seeds in [(95155,5,'dynamic-03/node5',[6920]),(95098,3,'dynamic-02/node3',[6921])]:
  details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node'+str(node)+' 'in details
  binaries={str(root/str(seed)/'route/router'):seed for seed in seeds}
  code="import os,json;rows=[]\nfor n in os.listdir('/proc'):\n if not n.isdigit():continue\n try:\n  p='/proc/'+n;assert os.stat(p).st_uid==10011\n  e=os.readlink(p+'/exe')\n  if e in "+repr(binaries)+":\n   cmd=open(p+'/cmdline','rb').read().decode().split(chr(0));rows.append(dict(pid=n,binary=e,seed="+repr(binaries)+"[e],command=[x for x in cmd if x],cpu_affinity=sorted(os.sched_getaffinity(int(n)))))\n except (OSError,AssertionError):pass\nprint(json.dumps(rows))"
  procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));r['pools'].append(dict(job=job,node=node,actual_processes=procs,job_details=details))
  for seed in seeds:
   found=[x for x in procs if x['seed']==seed];assert len(found)==16,(seed,len(found))
   for row in found:
    cmd=row['command'];assert '--weighted-bidirectional'in cmd;assert '--resource-labels=8000000'in cmd and '--critical-first'in cmd and '--ordinary-zero-pattern'in cmd;assert not any(x.startswith(('--ordinary-search-margin','--ordinary-congestion-scale'))for x in cmd);assert len(row['cpu_affinity'])==16
   queue=b/folder;name=next(n for n in json.loads((queue/'queue-state.json').read_text())['active']if n.endswith('-'+str(seed)));p=queue/'commands'/(name+'.json');command=json.loads(p.read_text());assert command['admission']['admitted']and command['admission']['available_bytes']>command['admission']['required_bytes'];r.setdefault('actual_admissions',[]).append(dict(seed=seed,path=str(p),sha256=sha(p),admission=command['admission']))
 r.update(passed=True,scope='Actual6920/6921 each16 owned weighted router children, actual CPU affinity/command/memory checked;32 actual inputs byte-exact against5890/6720 respectively, only new CLI weighted flag. Actual691 regression and699 invariance bind source690; weight1 exact and higher weights no optimality claim. Outer64GiB/per-router4GiB more conservative, no reduced task width. Same current453/S5380 hardware and all original final gates mandatory. No speed/convergence/physical qualification claim.')
except BaseException as e:r.update(error=str(e),traceback=traceback.format_exc());raise
finally:(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=r['passed'],input_pairs=len(r['comparisons']),actual_children=sum(len(x['actual_processes'])for x in r['pools']))))
'''
compile(q,'actual-remote-audit','exec')
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
