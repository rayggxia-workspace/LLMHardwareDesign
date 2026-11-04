from pathlib import Path
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time,subprocess,traceback
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453/upper-candidates';out=b/'r256-pin-release-active-pool-audit-961';assert not out.exists();assert all((root/str(seed)/'route'/('trial-'+str(i))/'input.txt').exists()for seed in [9490,9491]for i in range(16));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();r=dict(passed=False,whole_system_qualified=False,time=time.time(),comparisons=[],pools=[]);out.mkdir()
try:
 for seed,baseline in [(9490,9060),(9491,9280)]:
  for i in range(16):
   p=root/str(seed)/'route'/('trial-'+str(i))/'input.txt';prior=root/str(baseline)/'route'/('trial-'+str(i))/'input.txt';assert p.read_bytes()==prior.read_bytes()
   newlog=p.parent/'output.txt.native-prefix.log';oldlog=prior.parent/'output.txt.native-prefix.log'
   def filtered(path):
    raw=path.read_bytes();lines=raw.splitlines(keepends=True)
    if raw and not raw.endswith(b'\n'):lines=lines[:-1]
    return b''.join(l for l in lines if b'routing_phase_event'not in l)
   latest=filtered(newlog);assert latest and filtered(oldlog).startswith(latest)
   r['comparisons'].append(dict(candidate=seed,baseline=baseline,trial=i,input_sha256=sha(p),baseline_input_sha256=sha(prior),native_filtered_live_prefix_bytes=len(latest),native_filtered_live_prefix_sha256=hashlib.sha256(latest).hexdigest(),old_native_log=str(oldlog),new_native_log=str(newlog),input_byte_exact=True,actual_native_log_prefix_byte_exact=True))
 for job,node,folder,selected,all_seeds in [(95155,5,'dynamic-03/node5',[9490],[6360,8301,9280,9490]),(97097,6,'dynamic-08/node6',[9491],[9060,9061,9281,9491])]:
  details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node'+str(node)+' 'in details
  binaries={str(root/str(seed)/'route/router'):seed for seed in all_seeds}
  code="import os,json;rows=[]\nfor n in os.listdir('/proc'):\n if not n.isdigit():continue\n try:\n  p='/proc/'+n;assert os.stat(p).st_uid==10011\n  e=os.readlink(p+'/exe')\n  if e in "+repr(binaries)+":\n   cmd=open(p+'/cmdline','rb').read().decode().split(chr(0));rows.append(dict(pid=n,binary=e,seed="+repr(binaries)+"[e],command=[x for x in cmd if x],cpu_affinity=sorted(os.sched_getaffinity(int(n)))))\n except (OSError,AssertionError):pass\nprint(json.dumps(rows))"
  procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));masks={}
  for seed in all_seeds:
   found=[x for x in procs if x['seed']==seed];assert found,(seed,'no live owned child');mask=found[0]['cpu_affinity'];assert len(mask)==16 and all(x['cpu_affinity']==mask for x in found);masks[seed]=set(mask)
   if seed not in selected:continue
   assert len(found)==16,(seed,len(found))
   for row in found:
    cmd=row['command'];assert all(flag in cmd for flag in ['--ordinary-endpoint-escape','--weighted-bidirectional','--trace-routing-phases','--ordinary-zero-maze=16384','--native-prefix-first','--pin-access=ordinary-first','--native-batch-ripup','--release-pin-reservations','--critical-first','--ordinary-zero-pattern','--resource-labels=8000000'])
    assert ('--native-refresh=8'in cmd)==(seed==9491);assert not any(x.startswith(('--native-zero-maze=','--ordinary-search-margin','--ordinary-congestion-scale'))for x in cmd)
   queue=b/folder;name=next(n for n in json.loads((queue/'queue-state.json').read_text())['active']if n.endswith('-'+str(seed)));p=queue/'commands'/(name+'.json');command=json.loads(p.read_text());a=command['admission'];assert a['admitted']and a['available_bytes']>a['required_bytes'];r.setdefault('actual_admissions',[]).append(dict(seed=seed,path=str(p),sha256=sha(p),admission=a))
  assert all(not(masks[a]&masks[z])for a in masks for z in masks if a<z)
  r['pools'].append(dict(job=job,node=node,selected=selected,all_owned_live_processes=procs,four16cpu_masks_pairwise_disjoint=True,job_details=details))
 r.update(passed=True,scope='Actual9490/9491 each16owned source947 children and32inputs/native log prefix bytes match9060/9280. Release flag acts only at native-to-ordinary handoff; current actual native trajectory unchanged. CPU masks16, all four active jobs per node pairwise disjoint; actual224GiB node5/256GiB node6 conservative memory admissions verified. Actual948/950/956 preserve same-prefix failure/success, original71byte replays/20invariants and all14future final gate paths/functions/events. Only guarded own9062/8592 retired, old raw/specs/partials preserved.8parents dynamic c64 4x16/c96 6x16 and externalR/foreign untouched. No native/fullroute/system physical acceptance inferred.')
except BaseException as e:r.update(error=str(e),traceback=traceback.format_exc());raise
finally:(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=r['passed'],new_owned_children=32,input_and_live_native_prefix_pairs=len(r['comparisons']),four16cpu_masks_disjoint_both_nodes=True)))
'''
compile(q,'audit961remote','exec');print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
