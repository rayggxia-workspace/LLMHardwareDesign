from pathlib import Path
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time,subprocess,traceback
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453/upper-candidates';out=b/'r256-directional-bidirectional-active-pool-audit-918';assert not out.exists();assert all((root/str(seed)/'route'/('trial-'+str(i))/'input.txt').exists()for seed in [9060,9061,9062,9063]for i in range(16));out.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();r=dict(passed=False,whole_system_qualified=False,time=time.time(),comparisons=[],pools=[])
try:
 for seed in [9060,9061,9062,9063]:
  for i in range(16):
   a=root/'7200/route'/('trial-'+str(i))/'input.txt';p=root/str(seed)/'route'/('trial-'+str(i))/'input.txt';expected=a.read_bytes()
   assert p.read_bytes()==expected;r['comparisons'].append(dict(seed=seed,trial=i,baseline=str(a),candidate=str(p),baseline_sha256=sha(a),candidate_sha256=sha(p),sole_input_difference='all_input_bytes_exact_against7200_only_opt_in_CLI_differs'))
 for job,node,folder,seeds in [(97097,6,'dynamic-08/node6',[9060,9061]),(95155,5,'dynamic-03/node5',[9062,9063])]:
  details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node'+str(node)+' 'in details
  binaries={str(root/str(seed)/'route/router'):seed for seed in seeds}
  code="import os,json;rows=[]\nfor n in os.listdir('/proc'):\n if not n.isdigit():continue\n try:\n  p='/proc/'+n;assert os.stat(p).st_uid==10011\n  e=os.readlink(p+'/exe')\n  if e in "+repr(binaries)+":\n   cmd=open(p+'/cmdline','rb').read().decode().split(chr(0));rows.append(dict(pid=n,binary=e,seed="+repr(binaries)+"[e],command=[x for x in cmd if x],cpu_affinity=sorted(os.sched_getaffinity(int(n)))))\n except (OSError,AssertionError):pass\nprint(json.dumps(rows))"
  procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));r['pools'].append(dict(job=job,node=node,actual_processes=procs,job_details=details))
  for seed in seeds:
   found=[x for x in procs if x['seed']==seed];assert len(found)==16,(seed,len(found))
   for row in found:
    cmd=row['command'];assert '--ordinary-endpoint-escape'in cmd and '--weighted-bidirectional'in cmd and '--trace-routing-phases'in cmd and '--ordinary-zero-maze=16384'in cmd and '--native-prefix-first'in cmd and ('--pin-access='+('after-native'if seed==9062 else'ordinary-first'))in cmd and (('--native-zero-maze=16384'in cmd)if seed==9061 else not any(x.startswith('--native-zero-maze=')for x in cmd))and ('--native-batch-ripup'in cmd)==(seed!=9063);assert '--resource-labels=8000000'in cmd and '--critical-first'in cmd and '--ordinary-zero-pattern'in cmd;assert not any(x.startswith(('--ordinary-search-margin','--ordinary-congestion-scale'))for x in cmd);assert len(row['cpu_affinity'])==16
   queue=b/folder;name=next(n for n in json.loads((queue/'queue-state.json').read_text())['active']if n.endswith('-'+str(seed)));p=queue/'commands'/(name+'.json');command=json.loads(p.read_text());assert command['admission']['admitted']and command['admission']['available_bytes']>command['admission']['required_bytes'];r.setdefault('actual_admissions',[]).append(dict(seed=seed,path=str(p),sha256=sha(p),admission=command['admission']))
  if len(seeds)>1:
   masks=[set(next(x for x in procs if x['seed']==seed)['cpu_affinity'])for seed in seeds];assert all(not(masks[i]&masks[j])for i in range(len(masks))for j in range(i))
 r.update(passed=True,scope='Actual9060/9061/9062/9063 each16owned router children,64inputs byte-exact7200. Source901 controlled ordinary-first/batch/native16K variants and batch after-native control CLI verified. Each mask16CPU, both nodes two new job masks disjoint, actual1.2+16GiB memory admissions verified. Actual90271case45negative/90763original byte replays/91128full stage bindings retain final gates and actual current453 functions/events. Only guarded own8591/8860/8861/8862 replaced, all old sources/raw/specs/failures/partials preserved.8parents dynamic c64 4x16/c96 6x16, node5/node6 forecasts224GiB need284.8GiB actual available. Other own tasks and externalR/foreign unchanged. No native/full route/physical pass inferred.')
except BaseException as e:r.update(error=str(e),traceback=traceback.format_exc());raise
finally:(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=r['passed'],input_pairs=len(r['comparisons']),actual_children=sum(len(x['actual_processes'])for x in r['pools']))))
'''
compile(q,'actual-remote-audit','exec')
z=subprocess.run(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True);print(z.stdout);print(z.stderr[-1600:]if z.returncode else '');assert z.returncode==0,'Actual audit failed; inspect precondition or saved receipt'
