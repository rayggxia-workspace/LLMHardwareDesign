"""Free exactly three own obsolete external-S route attempts; preserve parents/evidence."""
import subprocess,shlex
q=r"""from pathlib import Path
import json,subprocess,hashlib,re,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'route-selection-102/sready140-three-obsolete-routes-retired'
if root.exists():print('Already recorded:',root);raise SystemExit(0)
needed=[b/'s-ready-qualified-01'/str(n)/'pg-delivery/receipt.json'for n in [1390,1391]]
if not all(p.exists()and json.loads(p.read_text()).get('passed')for p in needed):print('ready=false; actual new adapters PG qualification pending');raise SystemExit(0)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
for node,job,fam,name in [(5,95155,3,'01-c-drive-route-916'),(6,95101,2,'01-c-drive-route-912'),(7,95102,2,'01-c-drive-route-919')]:
 queue=b/('dynamic-%02d'%fam)/('node'+str(node));state=json.loads((queue/'queue-state.json').read_text())
 if name not in state['active']:rows.append(dict(node=node,name=name,action='already_finished_no_stop'));continue
 assert len(state['active'])==4
 specfile=queue/'pending'/(name+'.json');spec=json.loads(specfile.read_text());assert spec['script']=='system_upper.py'and spec['source_root']==str(b/'source-102')and spec['forecast_gib']==32
 args=spec['args'];out=args[args.index('--out')+1];graph=Path(args[args.index('--graph')+1]);g=json.loads(graph.read_text());assert len(g['instances'])==335 and not g.get('S_internal_drive')and sum(r['source_instance']=='macro_s'for r in g['boundary_links']['links'])==100
 assert out==str(b/'drive-route-01'/('seed-'+name.rsplit('-',1)[1]))
 details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node'+str(node)+' 'in details
 steps=subprocess.check_output(['scontrol','show','step',str(job),'-o'],universal_newlines=True)
 found=[m.groups()for m in re.finditer(r'StepId=('+str(job)+r'\.\d+).*?SrunHost:Pid=(node\d+):(\d+)',steps)]
 code="import os,json;d={}"+chr(10)+"for p in "+repr([r[2]for r in found])+":"+chr(10)+" try:"+chr(10)+"  assert os.stat('/proc/'+p).st_uid==10011;d[p]=open('/proc/'+p+'/cmdline','rb').read().decode().split(chr(0))"+chr(10)+" except OSError:pass"+chr(10)+"print(json.dumps(d))"
 procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));targets=[]
 for step,host,pid in found:
  actual=procs.get(pid,[])
  if '--out'in actual and actual[actual.index('--out')+1]==out and str(b/'source-102/project/experiments/control_v1/system_upper.py')in actual:targets.append(dict(step=step,host=host,pid=pid,command=actual))
 assert len(targets)==1 and targets[0]['host']=='node'+str(node)
 rows.append(dict(node=node,job=job,name=name,action='stop_exact_obsolete_route',spec_path=str(specfile),spec_sha256=sha(specfile),old_graph=str(graph),old_graph_sha256=sha(graph),old_external_S_Link8_instances=100,job_details=details,queue_state=state,target=targets[0]))
root.mkdir();(root/'verified-before.json').write_text(json.dumps(dict(time=time.time(),rows=rows,prerequisites={str(p):sha(p)for p in needed},reason='Only three own Issue162 old335-instance external-S searches, one per fully occupied node, retired to admit exact new qualified internal-S/S-ready combinations. User selected internal-S drive; obsolete masks/searches cannot be final solution. Preserve all specs/partial outputs and parent allocations. No other task/R job stopped. Not a hardware failure; all CPU/memory gates unchanged.'),indent=2))
completed=[]
for row in rows:
 if row['action']=='stop_exact_obsolete_route':
  subprocess.run(['scancel',row['target']['step']],check=True);completed.append(row['target']['step']);(root/'cancelled.json').write_text(json.dumps(dict(time=time.time(),steps=completed)))
print('Retired exact own obsolete route steps:',completed)
"""
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
