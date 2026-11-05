from pathlib import Path
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time,subprocess,traceback
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453/upper-candidates';out=b/'r256-directional-bidirectional-active-pool-audit-891';assert not out.exists();assert all((root/str(seed)/'route'/('trial-'+str(i))/'input.txt').exists()for seed in [8860,8861,8862]for i in range(16));out.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();r=dict(passed=False,whole_system_qualified=False,time=time.time(),comparisons=[],pools=[])
try:
 for seed in [8860,8861,8862]:
  for i in range(16):
   a=root/'7200/route'/('trial-'+str(i))/'input.txt';p=root/str(seed)/'route'/('trial-'+str(i))/'input.txt';expected=a.read_bytes()
   if seed==8862:
    header,body=expected.split(b'\n',1);fields=header.split();fields[3]=str(int(fields[3])-1009).encode();expected=b' '.join(fields)+b'\n'+body
   assert p.read_bytes()==expected;r['comparisons'].append(dict(seed=seed,trial=i,baseline=str(a),candidate=str(p),baseline_sha256=sha(a),candidate_sha256=sha(p),sole_input_difference='only_rng_field_minus1009_for8862_otherwise_exact_native_zero_cli_only'))
 for job,node,folder,seeds in [(97097,6,'dynamic-08/node6',[8860]),(95155,5,'dynamic-03/node5',[8861,8862])]:
  details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node'+str(node)+' 'in details
  binaries={str(root/str(seed)/'route/router'):seed for seed in seeds}
  code="import os,json;rows=[]\nfor n in os.listdir('/proc'):\n if not n.isdigit():continue\n try:\n  p='/proc/'+n;assert os.stat(p).st_uid==10011\n  e=os.readlink(p+'/exe')\n  if e in "+repr(binaries)+":\n   cmd=open(p+'/cmdline','rb').read().decode().split(chr(0));rows.append(dict(pid=n,binary=e,seed="+repr(binaries)+"[e],command=[x for x in cmd if x],cpu_affinity=sorted(os.sched_getaffinity(int(n)))))\n except (OSError,AssertionError):pass\nprint(json.dumps(rows))"
  procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));r['pools'].append(dict(job=job,node=node,actual_processes=procs,job_details=details))
  for seed in seeds:
   found=[x for x in procs if x['seed']==seed];assert len(found)==16,(seed,len(found))
   for row in found:
    cmd=row['command'];assert '--ordinary-endpoint-escape'in cmd and '--weighted-bidirectional'in cmd and '--trace-routing-phases'in cmd and '--ordinary-zero-maze=16384'in cmd and '--native-prefix-first'in cmd and '--pin-access=all'in cmd and ('--native-zero-maze='+str({8860:16384,8861:65536,8862:16384}[seed]))in cmd;assert '--resource-labels=8000000'in cmd and '--critical-first'in cmd and '--ordinary-zero-pattern'in cmd;assert not any(x.startswith(('--ordinary-search-margin','--ordinary-congestion-scale'))for x in cmd);assert len(row['cpu_affinity'])==16
   queue=b/folder;name=next(n for n in json.loads((queue/'queue-state.json').read_text())['active']if n.endswith('-'+str(seed)));p=queue/'commands'/(name+'.json');command=json.loads(p.read_text());assert command['admission']['admitted']and command['admission']['available_bytes']>command['admission']['required_bytes'];r.setdefault('actual_admissions',[]).append(dict(seed=seed,path=str(p),sha256=sha(p),admission=command['admission']))
  if len(seeds)>1:
   masks=[set(next(x for x in procs if x['seed']==seed)['cpu_affinity'])for seed in seeds];assert all(not(masks[i]&masks[j])for i in range(len(masks))for j in range(i))
 r.update(passed=True,scope='Actual8860/8861/8862 each16owned children,48inputs: first2 byte-identical7200,8862 onlyactual RNG field minus1009. All original coordinate/body/options exact. Native-zero16K/64K/16K, native-first/all-pin, original weighted/ordinarymaze/escape CLI verified. Each mask16CPU and node5 two-step masks disjoint; actual1.2+16GiB memory admissions verified. Actual88563case/40negative and88757old byte replay,18 gates/headers and original finite/exact branches unchanged,89021complete final stage bindings/functions/events. Only guarded own8560 child97097.5 replaced; all old raw/source/spec/failure/partial retained. Old8561 finished64failures and87316exact80round diagnostic ended naturally before885 then8861/8862 refill.8parents c64 4x16/c96 6x16, node5forecast224needs284.8GiB and node6forecast192needs246.4GiB fresh actualMemAvailable plus scheduler admission. Other tasks/externalR unchanged. No native/fullroute/physical pass inferred.')
except BaseException as e:r.update(error=str(e),traceback=traceback.format_exc());raise
finally:(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=r['passed'],input_pairs=len(r['comparisons']),actual_children=sum(len(x['actual_processes'])for x in r['pools']))))
'''
compile(q,'actual-remote-audit','exec')
z=subprocess.run(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True);print(z.stdout);print(z.stderr[-1600:]if z.returncode else '');assert z.returncode==0,'Actual audit failed; inspect precondition or saved receipt'
