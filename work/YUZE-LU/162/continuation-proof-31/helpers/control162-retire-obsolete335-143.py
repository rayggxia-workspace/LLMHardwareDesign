"""Retire twelve individually verified searches belonging only to Issue162."""
import subprocess,shlex
q=r'''from pathlib import Path
import subprocess,json,hashlib,re,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391';root=b/'route-selection-102/sready143-twelve-obsolete335-retired';assert not root.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
function=c/'final-composition/receipt.json';assert json.loads(function.read_text())['passed']
comparison=b/'route-selection-102/sready143-exact-cache-comparison.json';comp=json.loads(comparison.read_text());assert comp['passed']and comp['identical_successful_route_count']==132
selection=b/'route-selection-102/s-ready-cache-refill-source143.json';new=json.loads(selection.read_text());assert new['instance_count']==235 and len(new['tasks'])==84
for row in new['tasks']:assert Path(row['path']).exists()and sha(row['path'])==row['sha256']
old_graph=b/'composition-drive-pg-01/topology/boundary-graph.json';g=json.loads(old_graph.read_text());assert len(g['instances'])==335 and sum(v=='control_link8'for v in g['instances'].values())==309
groups=[(2,3,95098,['01-c-capacity-route-1130','01-a-budget-priority-1140']),(2,6,95101,['01-c-drive-route-913','01-c-drive-route-914','01-c-capacity-route-1071']),(2,7,95102,['01-c-drive-route-920','01-c-decaying-weight-route-951','01-c-decaying-weight-route-953']),(4,25,95204,['01-c-drive-route-922','01-c-drive-route-923','01-c-drive-route-932']),(2,26,95119,['01-c-decaying-weight-route-952'])]
rows=[]
for fam,node,job,names in groups:
 queue=b/('dynamic-%02d'%fam)/('node'+str(node));state=json.loads((queue/'queue-state.json').read_text());assert str(state['job'])==str(job)
 details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node'+str(node)+' 'in details
 steps=subprocess.check_output(['scontrol','show','step',str(job),'-o'],universal_newlines=True);found=[m.groups()for m in re.finditer(r'StepId=('+str(job)+r'\.\d+).*?SrunHost:Pid=(node\d+):(\d+)',steps)]
 code="import os,json;d={}"+chr(10)+"for p in "+repr([r[2]for r in found])+":"+chr(10)+" try:"+chr(10)+"  assert os.stat('/proc/'+p).st_uid==10011;d[p]=open('/proc/'+p+'/cmdline','rb').read().decode().split(chr(0))"+chr(10)+" except OSError:pass"+chr(10)+"print(json.dumps(d))"
 procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True))
 for name in names:
  assert name in state['active'];p=queue/'pending'/(name+'.json');spec=json.loads(p.read_text());args=spec['args'];out=Path(args[args.index('--out')+1]);source=Path(spec['source_root'])
  assert spec['script']=='system_upper.py'and spec['forecast_gib']==32 and source.parent==b and source.name in ['source-102','source-105','source-106','source-113','source-114']and args[args.index('--graph')+1]==str(old_graph)
  assert b in out.parents and not(out/'receipt.json').exists();targets=[]
  for step,host,pid in found:
   command=procs.get(pid,[])
   if '--out'in command and command[command.index('--out')+1]==str(out)and str(source/'project/experiments/control_v1/system_upper.py')in command:targets.append(dict(step=step,host=host,pid=pid,command=command))
  assert len(targets)==1 and targets[0]['host']=='node'+str(node)
  logs=[]
  for log in out.glob('trial-*/router.log'):
   data=log.read_bytes();logs.append(dict(path=str(log),prefix_bytes=len(data),prefix_sha256=hashlib.sha256(data).hexdigest(),tail=data.decode(errors='replace').splitlines()[-1:]))
  rows.append(dict(node=node,name=name,job_details=details,spec_path=str(p),spec_sha256=sha(p),target=targets[0],active_log_prefix_snapshots=logs))
assert len(rows)==12 and len({row['target']['step']for row in rows})==12
root.mkdir();(root/'verified-before.json').write_text(json.dumps(dict(time=time.time(),targets=rows,old_graph_sha256=sha(old_graph),actual_current_function_receipt_sha256=sha(function),exact_cache_comparison_sha256=sha(comparison),queued_replacements_sha256=sha(selection),scope='Only individually verified Issue162 obsolete335 external-S searches; user selected S-internal drive, actual235 function/native leaf/bounds qualified. Twelve replacement235 routes plus72 unchanged full gates already queued. Preserve every original spec/output, all eight parent allocations, current235 searches, other tasks and R. Unfinished obsolete searches, not completed physical failures; no threshold relaxed.'),indent=2))
stopped=[]
for row in rows:
 subprocess.run(['scancel',row['target']['step']],check=True);stopped.append(row['target']['step']);(root/'cancelled.json').write_text(json.dumps(dict(time=time.time(),steps=stopped),indent=2))
print(json.dumps(dict(retired_exact_own_steps=stopped,parent_allocations_cancelled=0,other_tasks_touched=False)))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
