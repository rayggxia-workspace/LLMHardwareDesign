"""Replace only two exact own obsolete external-S searches with real halo routes."""
import subprocess,shlex
q=r'''from pathlib import Path
import subprocess,json,hashlib,re,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391';root=b/'route-selection-102/sready142-two-obsolete-node5-retired';assert not root.exists();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
function=c/'final-composition/receipt.json';assert json.loads(function.read_text())['passed']
pin=c/'halo-native-pin-load-02/native-pin-load.json';pr=c/'halo-native-pin-load-02/receipt.json';r=json.loads(pr.read_text());assert r['passed']and r['outputs'][pin.name]==sha(pin)
d=json.loads(pin.read_text());assert len(d['placements'])==3 and all(not any(row['violations'].values())for row in d['placements'])
selection=b/'route-selection-102/s-ready-halo-routes-source142.json';new=json.loads(selection.read_text());assert len(new['tasks'])==21 and new['instance_count']==235
old_graph=b/'composition-drive-pg-01/topology/boundary-graph.json';g=json.loads(old_graph.read_text());assert len(g['instances'])==335 and sum(t=='control_link8'for t in g['instances'].values())==309
queue=b/'dynamic-03/node5';state=json.loads((queue/'queue-state.json').read_text());assert str(state['job'])=='95155';details=subprocess.check_output(['scontrol','show','job','95155','-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node5 'in details
steps=subprocess.check_output(['scontrol','show','step','95155','-o'],universal_newlines=True);found=[m.groups()for m in re.finditer(r'StepId=(95155\.\d+).*?SrunHost:Pid=(node\d+):(\d+)',steps)]
code="import os,json;d={}"+chr(10)+"for p in "+repr([r[2]for r in found])+":"+chr(10)+" try:"+chr(10)+"  assert os.stat('/proc/'+p).st_uid==10011;d[p]=open('/proc/'+p+'/cmdline','rb').read().decode().split(chr(0))"+chr(10)+" except OSError:pass"+chr(10)+"print(json.dumps(d))"
procs=json.loads(subprocess.check_output(['srun','--jobid=95155','--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));rows=[]
for seed in [917,918]:
 name='01-c-drive-route-'+str(seed);assert name in state['active'];p=queue/'pending'/(name+'.json');spec=json.loads(p.read_text());args=spec['args'];out=args[args.index('--out')+1]
 assert spec['source_root']==str(b/'source-102')and spec['script']=='system_upper.py'and out==str(b/'drive-route-01'/('seed-'+str(seed)))and args[args.index('--graph')+1]==str(old_graph)
 assert not(Path(out)/'receipt.json').exists()
 targets=[]
 for step,host,pid in found:
  command=procs.get(pid,[])
  if '--out'in command and command[command.index('--out')+1]==out and str(b/'source-102/project/experiments/control_v1/system_upper.py')in command:targets.append(dict(step=step,host=host,pid=pid,command=command))
 assert len(targets)==1 and targets[0]['host']=='node5'
 logs=[]
 for log in Path(out).glob('trial-*/router.log'):
  data=log.read_bytes();logs.append(dict(path=str(log),prefix_bytes=len(data),prefix_sha256=hashlib.sha256(data).hexdigest(),tail=data.decode(errors='replace').splitlines()[-1:]))
 rows.append(dict(seed=seed,spec_path=str(p),spec_sha256=sha(p),target=targets[0],active_log_prefix_snapshots=logs))
root.mkdir();(root/'verified-before.json').write_text(json.dumps(dict(time=time.time(),job_details=details,queue_state=state,targets=rows,actual_function_receipt_sha256=sha(function),pin_receipt_sha256=sha(pr),new_route_selection_sha256=sha(selection),old_graph_sha256=sha(old_graph),scope='Two exact own old335 external-S searches retired only after actual selected235 function and all three halo native/pin necessary bounds passed and21 new route/acceptance tasks appended. Preserve old specs/partial results, all parent allocations, third old933 control, R and all other tasks. Not completed physical failures.'),indent=2))
stopped=[]
for row in rows:
 subprocess.run(['scancel',row['target']['step']],check=True);stopped.append(row['target']['step']);(root/'cancelled.json').write_text(json.dumps(dict(time=time.time(),steps=stopped),indent=2))
print('Released two exact own steps',stopped,'for three independent new halo routes.')
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
