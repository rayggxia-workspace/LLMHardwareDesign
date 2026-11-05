from pathlib import Path
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time,subprocess,traceback
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453/upper-candidates';out=b/'r256-directional-bidirectional-active-pool-audit-818';assert not out.exists();assert all((root/str(seed)/'route'/('trial-'+str(i))/'input.txt').exists()for seed in [8110,8111]for i in range(16));out.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();r=dict(passed=False,whole_system_qualified=False,time=time.time(),comparisons=[],pools=[])
try:
 for seed in [8110,8111]:
  for i in range(16):
   a=root/'7200/route'/('trial-'+str(i))/'input.txt';p=root/str(seed)/'route'/('trial-'+str(i))/'input.txt';assert p.read_bytes()==a.read_bytes();r['comparisons'].append(dict(seed=seed,trial=i,baseline=str(a),candidate=str(p),baseline_sha256=sha(a),candidate_sha256=sha(p),sole_input_difference='none_input_bytes_exact_endpoint_escape_cli_only'))
 for job,node,folder,seeds in [(95341,2,'dynamic-05/node2',[8110]),(95391,4,'dynamic-05/node4',[8111])]:
  details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node'+str(node)+' 'in details
  binaries={str(root/str(seed)/'route/router'):seed for seed in seeds}
  code="import os,json;rows=[]\nfor n in os.listdir('/proc'):\n if not n.isdigit():continue\n try:\n  p='/proc/'+n;assert os.stat(p).st_uid==10011\n  e=os.readlink(p+'/exe')\n  if e in "+repr(binaries)+":\n   cmd=open(p+'/cmdline','rb').read().decode().split(chr(0));rows.append(dict(pid=n,binary=e,seed="+repr(binaries)+"[e],command=[x for x in cmd if x],cpu_affinity=sorted(os.sched_getaffinity(int(n)))))\n except (OSError,AssertionError):pass\nprint(json.dumps(rows))"
  procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));r['pools'].append(dict(job=job,node=node,actual_processes=procs,job_details=details))
  for seed in seeds:
   found=[x for x in procs if x['seed']==seed];assert len(found)==16,(seed,len(found))
   for row in found:
    cmd=row['command'];assert '--ordinary-endpoint-escape'in cmd and '--weighted-bidirectional'in cmd and '--trace-routing-phases'in cmd and (('--ordinary-threshold-pattern-rounds=16'in cmd)if seed==8111 else not any(x.startswith('--ordinary-threshold-pattern-rounds=')for x in cmd));assert '--resource-labels=8000000'in cmd and '--critical-first'in cmd and '--ordinary-zero-pattern'in cmd;assert not any(x.startswith(('--ordinary-search-margin','--ordinary-congestion-scale'))for x in cmd);assert len(row['cpu_affinity'])==16
   queue=b/folder;name=next(n for n in json.loads((queue/'queue-state.json').read_text())['active']if n.endswith('-'+str(seed)));p=queue/'commands'/(name+'.json');command=json.loads(p.read_text());assert command['admission']['admitted']and command['admission']['available_bytes']>command['admission']['required_bytes'];r.setdefault('actual_admissions',[]).append(dict(seed=seed,path=str(p),sha256=sha(p),admission=command['admission']))
 r.update(passed=True,scope='Actual8110/8111 each16 owned children, node2/job95341 and node4/job95391, each16CPU mask and real1.2+16GiB memory admission checked.32 actual input bytes identical7200; new strict-zero escape flag and phase0/16 CLI checked. Actual810 full45case regression and817 all39 default input/output/filtered-log replay,15 source invariants,132 direct candidate checks per binary passed.822 actual real-pin static9730 candidate coverage is static only. Guards813/814 replaced only exact own7371/7370 child steps, all prior raw/source/spec/partial/failure preserved, other tasks/8parents/externalR untouched. Both c64 nodes retain4x16,forecast160GiB need208GiB below815 actual448-plusGiB and fresh actualadmission. Final7stage chains816 retain current453 functions/traces and all original physical gates. No whole-scene convergence, speed or physical pass inferred.')
except BaseException as e:r.update(error=str(e),traceback=traceback.format_exc());raise
finally:(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=r['passed'],input_pairs=len(r['comparisons']),actual_children=sum(len(x['actual_processes'])for x in r['pools']))))
'''
compile(q,'actual-remote-audit','exec')
z=subprocess.run(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True);print(z.stdout);print(z.stderr[-1600:]if z.returncode else '');assert z.returncode==0,'Actual audit failed; inspect precondition or saved receipt'
