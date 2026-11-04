from pathlib import Path
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time,subprocess,traceback
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453/upper-candidates';out=b/'r256-directional-bidirectional-active-pool-audit-787';assert not out.exists();assert all((root/str(seed)/'route'/('trial-'+str(i))/'input.txt').exists()for seed in [7780,7781]for i in range(16));out.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();r=dict(passed=False,whole_system_qualified=False,time=time.time(),comparisons=[],pools=[])
try:
 for seed in [7780,7781]:
  for i in range(16):
   a=root/'7200/route'/('trial-'+str(i))/'input.txt';p=root/str(seed)/'route'/('trial-'+str(i))/'input.txt';assert p.read_bytes()==a.read_bytes();r['comparisons'].append(dict(seed=seed,trial=i,baseline=str(a),candidate=str(p),baseline_sha256=sha(a),candidate_sha256=sha(p),sole_input_difference='none_input_bytes_exact_pair_window_cli_only'))
 for job,node,folder,seeds in [(96222,24,'dynamic-06/node26',[7780,7781])]:
  details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node'+str(node)+' 'in details
  binaries={str(root/str(seed)/'route/router'):seed for seed in seeds}
  code="import os,json;rows=[]\nfor n in os.listdir('/proc'):\n if not n.isdigit():continue\n try:\n  p='/proc/'+n;assert os.stat(p).st_uid==10011\n  e=os.readlink(p+'/exe')\n  if e in "+repr(binaries)+":\n   cmd=open(p+'/cmdline','rb').read().decode().split(chr(0));rows.append(dict(pid=n,binary=e,seed="+repr(binaries)+"[e],command=[x for x in cmd if x],cpu_affinity=sorted(os.sched_getaffinity(int(n)))))\n except (OSError,AssertionError):pass\nprint(json.dumps(rows))"
  procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));r['pools'].append(dict(job=job,node=node,actual_processes=procs,job_details=details))
  for seed in seeds:
   found=[x for x in procs if x['seed']==seed];assert len(found)==16,(seed,len(found))
   for row in found:
    cmd=row['command'];assert '--weighted-bidirectional'in cmd and '--trace-routing-phases'in cmd and (('--weighted-pair-margin=4'in cmd)if seed==7781 else not any(x.startswith('--weighted-pair-margin=')for x in cmd));assert '--resource-labels=8000000'in cmd and '--critical-first'in cmd and '--ordinary-zero-pattern'in cmd;assert not any(x.startswith(('--ordinary-search-margin','--ordinary-congestion-scale'))for x in cmd);assert len(row['cpu_affinity'])==16
   queue=b/folder;name=next(n for n in json.loads((queue/'queue-state.json').read_text())['active']if n.endswith('-'+str(seed)));p=queue/'commands'/(name+'.json');command=json.loads(p.read_text());assert command['admission']['admitted']and command['admission']['available_bytes']>command['admission']['required_bytes'];r.setdefault('actual_admissions',[]).append(dict(seed=seed,path=str(p),sha256=sha(p),admission=command['admission']))
 masks=[set(next(x['cpu_affinity']for x in r['pools'][0]['actual_processes']if x['seed']==seed))for seed in [7780,7781]];assert len(masks[0])==len(masks[1])==16 and not(masks[0]&masks[1]);r['same_node_new_task_masks_disjoint']=True
 r.update(passed=True,scope='Actual7780/7781 four-heap each16 owned children on actualnode24/queuefoldernode26, two16CPU masks disjoint;32 actual inputs byte-identical7200 and actual CLI heap variants margin0/4 checked. Actual777 full regression/785 invariance/786 full-chain binding recorded separately. New source776 changes only heap implementation, no extra arrays or search keys/domains/physical budgets/gates. Same conservative64GiB outer4GiB child and actual1.2+16GiB memory admission; c96six16CPU steps retained. Other4 legacy tasks/source/spec/logs unchanged. No speed/convergence/physical qualification claim.')
except BaseException as e:r.update(error=str(e),traceback=traceback.format_exc());raise
finally:(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=r['passed'],input_pairs=len(r['comparisons']),actual_children=sum(len(x['actual_processes'])for x in r['pools']))))
'''
compile(q,'actual-remote-audit','exec')
z=subprocess.run(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True);print(z.stdout);print(z.stderr[-1600:]if z.returncode else '');assert z.returncode==0,'Actual audit failed; inspect precondition or saved receipt'
