import subprocess,shlex
q=r'''from pathlib import Path
import json,subprocess,hashlib,re,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');base=b/'s-ready-composition-01/1391';root=b/'route-selection-102/sready141-proven-cap1421-retired';assert not root.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();receipt=base/'native-pin-load-01/receipt.json';proof=json.loads(receipt.read_text());assert proof['passed']and not proof['whole_system_qualified']and proof['outputs']['native-pin-load.json']==sha(base/'native-pin-load-01/native-pin-load.json')
report=json.loads((base/'native-pin-load-01/native-pin-load.json').read_text());bad=[r for r in report['placements']if Path(r['placement']).name=='1421'];assert len(bad)==1 and bad[0]['violations']['high']>0
rows=[]
for node,job,fam,seed in [(4,95391,5,1431),(2,95341,5,1441),(4,95391,5,1443),(26,95119,2,1447)]:
 queue=b/('dynamic-%02d'%fam)/('node'+str(node));state=json.loads((queue/'queue-state.json').read_text());name='00-k-sready140-route-'+str(seed)
 if name not in state['active']:rows.append(dict(node=node,seed=seed,action='already_finished_no_stop'));continue
 specfile=queue/'pending'/(name+'.json');spec=json.loads(specfile.read_text());assert spec['script']=='system_upper.py'and spec['source_root']==str(b/'source-140')and spec['forecast_gib']==32
 args=spec['args'];out=args[args.index('--out')+1];assert out==str(base/'upper-candidates'/str(seed)/'route')and args[args.index('--reuse-placement')+1]==str(base/'cap-capacity-candidates/1421')
 details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node'+str(node)+' 'in details
 steps=subprocess.check_output(['scontrol','show','step',str(job),'-o'],universal_newlines=True);found=[m.groups()for m in re.finditer(r'StepId=('+str(job)+r'\.\d+).*?SrunHost:Pid=(node\d+):(\d+)',steps)]
 code="import os,json;d={}"+chr(10)+"for p in "+repr([r[2]for r in found])+":"+chr(10)+" try:"+chr(10)+"  assert os.stat('/proc/'+p).st_uid==10011;d[p]=open('/proc/'+p+'/cmdline','rb').read().decode().split(chr(0))"+chr(10)+" except OSError:pass"+chr(10)+"print(json.dumps(d))"
 procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));targets=[]
 for step,host,pid in found:
  actual=procs.get(pid,[])
  if '--out'in actual and actual[actual.index('--out')+1]==out and str(b/'source-140/project/experiments/control_v1/system_upper.py')in actual:targets.append(dict(step=step,host=host,pid=pid,command=actual))
 assert len(targets)==1 and targets[0]['host']=='node'+str(node)
 rows.append(dict(node=node,seed=seed,action='stop_exact_proven_infeasible_placement_search',spec_path=str(specfile),spec_sha256=sha(specfile),job_details=details,target=targets[0],queue_state=state))
root.mkdir();(root/'verified-before.json').write_text(json.dumps(dict(time=time.time(),rows=rows,pin_load_receipt=str(receipt),pin_load_receipt_sha256=sha(receipt),necessary_failure=bad[0],scope='Actual final ODB minimum Liberty pin capacitance proves placement1421 high-RC necessary condition fails even before vias/detours/coupling. Retire only four exact own searches for this placement; preserve original specs/results/parents, all other work and all physical thresholds.'),indent=2))
stopped=[]
for row in rows:
 if row['action']=='stop_exact_proven_infeasible_placement_search':
  subprocess.run(['scancel',row['target']['step']],check=True);stopped.append(row['target']['step']);(root/'cancelled.json').write_text(json.dumps(dict(time=time.time(),steps=stopped),indent=2))
print('Retired exact own infeasible placement searches',stopped)
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
