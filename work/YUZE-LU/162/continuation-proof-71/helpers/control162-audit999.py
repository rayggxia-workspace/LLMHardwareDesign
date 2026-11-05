from pathlib import Path
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time,subprocess,traceback
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453/upper-candidates';out=b/'r256-native-warm-active-pool-audit-999';assert not out.exists();assert all((root/str(seed)/'route'/('trial-'+str(i))/'input.txt').exists()for seed in [9490,9491]for i in range(16));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();r=dict(passed=False,whole_system_qualified=False,time=time.time(),comparisons=[],pools=[]);out.mkdir()
try:
 for seed in [9920,9921]:
  manifest=b/'r256-composition-453'/('warm-seed-'+str(seed)+'.json');cfg=json.loads(manifest.read_text());original=Path(cfg['input']);prefix=Path(cfg['prefix']);assert sha(original)==cfg['input_sha256']and sha(prefix)==cfg['prefix_sha256']
  h,body=original.read_bytes().split(b'\n',1)
  for i in range(16):
   p=root/str(seed)/'route'/('trial-'+str(i))/'input.txt';assert p.read_bytes().split(b'\n',1)[1]==body
   snapshot=p.parent/'output.txt.native-prefix-paths.txt';assert sha(snapshot)==cfg['prefix_sha256']
   log=p.parent/'output.txt.native-prefix.log';lines=[json.loads(x)for x in log.read_text().splitlines()if x.startswith('{')];rows=[x for x in lines if'conflict_nodes'in x];assert len(rows)==1 and rows[0]['conflict_nodes']==0 and rows[0]['round']==0
   r['comparisons'].append(dict(candidate=seed,trial=i,input_sha256=sha(p),seed_manifest=str(manifest),seed_manifest_sha256=sha(manifest),seed_native_prefix_sha256=sha(prefix),actual_imported_prefix_sha256=sha(snapshot),native_rounds=rows,original_input_body_byte_exact=True,actual_warm_zero_prefix_byte_exact=True))
 for job,node,folder,selected,all_seeds in [(95341,2,'dynamic-05/node2',[9920],[4660,5550,6560,9920]),(95391,4,'dynamic-05/node4',[9921],[4670,6140,6563,9921])]:
  details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node'+str(node)+' 'in details
  binaries={str(root/str(seed)/'route/router'):seed for seed in all_seeds}
  code="import os,json;rows=[]\nfor n in os.listdir('/proc'):\n if not n.isdigit():continue\n try:\n  p='/proc/'+n;assert os.stat(p).st_uid==10011\n  e=os.readlink(p+'/exe')\n  if e in "+repr(binaries)+":\n   cmd=open(p+'/cmdline','rb').read().decode().split(chr(0));rows.append(dict(pid=n,binary=e,seed="+repr(binaries)+"[e],command=[x for x in cmd if x],cpu_affinity=sorted(os.sched_getaffinity(int(n)))))\n except (OSError,AssertionError):pass\nprint(json.dumps(rows))"
  procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));masks={}
  for seed in all_seeds:
   found=[x for x in procs if x['seed']==seed];assert found,(seed,'no live owned child');mask=found[0]['cpu_affinity'];assert len(mask)==16 and all(x['cpu_affinity']==mask for x in found);masks[seed]=set(mask)
   if seed not in selected:continue
   assert len(found)==16,(seed,len(found))
   for row in found:
    cmd=row['command'];assert all(flag in cmd for flag in ['--ordinary-endpoint-escape','--weighted-bidirectional','--trace-routing-phases','--ordinary-zero-maze=16384','--native-prefix-first','--pin-access=none','--native-prefix-flexible','--critical-first','--ordinary-zero-pattern','--resource-labels=8000000'])
    assert '--native-prefix-input='+json.loads((b/'r256-composition-453'/('warm-seed-'+str(seed)+'.json')).read_text())['prefix']in cmd;assert not any(x.startswith('--native-refresh=')for x in cmd);assert not any(x.startswith(('--native-zero-maze=','--ordinary-search-margin','--ordinary-congestion-scale'))for x in cmd)
   queue=b/folder;name=next(n for n in json.loads((queue/'queue-state.json').read_text())['active']if n.endswith('-'+str(seed)));p=queue/'commands'/(name+'.json');command=json.loads(p.read_text());a=command['admission'];assert a['admitted']and a['available_bytes']>a['required_bytes'];r.setdefault('actual_admissions',[]).append(dict(seed=seed,path=str(p),sha256=sha(p),admission=a))
  assert all(not(masks[a]&masks[z])for a in masks for z in masks if a<z)
  r['pools'].append(dict(job=job,node=node,selected=selected,all_owned_live_processes=procs,four16cpu_masks_pairwise_disjoint=True,job_details=details))
 r.update(passed=True,scope='Actual9810/9811 each16 owned source972 children.32actualinputs bodies match source seeds;32actual zero-native snapshot files byte-identical to validated imported prefixes. Independent16CPU masks and all4active slots pernode disjoint, actual224/256GiB memory admissions checked. Every native M11/M12 wire remains movable under original finite wire budgets; actualM11landings and M1-M10 interiors unchanged. Actual973/980/984 tests/source/14strictfuturefullstage bindings required; originalgeometry/PG/currentfunctions/events/3RC300MHz gates unchanged. No fullroute or physical acceptance inferred')
except BaseException as e:r.update(error=str(e),traceback=traceback.format_exc());raise
finally:(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=r['passed'],new_owned_children=32,input_and_live_native_prefix_pairs=len(r['comparisons']),four16cpu_masks_disjoint_both_nodes=True)))
'''
compile(q,'audit961remote','exec');print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())

