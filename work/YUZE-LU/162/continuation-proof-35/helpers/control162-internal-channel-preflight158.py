"""Queue bounded internal-channel diagnostics; retire two exact own duplicates."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,subprocess,re,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');base=b/'s-ready-composition-01/1391';source=b/'source-157';record=b/'route-selection-102/sready158-internal-channel-preflight';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert json.loads((source/'source-manifest.json').read_text())['commit']=='fbb61e6fb3e1bb7dbff94d3189c33420fe629690'
targets=[];newtasks=[]
for node,job,oldseed in [(3,95098,1432),(6,95101,1433)]:
 queue=b/('dynamic-02/node'+str(node));name='00-k-sready140-route-'+str(oldseed);p=queue/'pending'/(name+'.json');s=json.loads(p.read_text());args=s['args'];out=args[args.index('--out')+1]
 assert s['source_root']==str(b/'source-140')and s['script']=='system_upper.py'and out==str(base/'upper-candidates'/str(oldseed)/'route')
 state=json.loads((queue/'queue-state.json').read_text());assert name in state['active']
 details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and ('NodeList=node'+str(node)+' ')in details
 steps=subprocess.check_output(['scontrol','show','step',str(job),'-o'],universal_newlines=True);found=[m.groups()for m in re.finditer(r'StepId=('+str(job)+r'\.\d+).*?SrunHost:Pid=(node\d+):(\d+)',steps)]
 code="import os,json;d={}"+chr(10)+"for p in "+repr([r[2]for r in found])+":"+chr(10)+" try:"+chr(10)+"  assert os.stat('/proc/'+p).st_uid==10011;d[p]=open('/proc/'+p+'/cmdline','rb').read().decode().split(chr(0))"+chr(10)+" except OSError:pass"+chr(10)+"print(json.dumps(d))"
 procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));matches=[]
 for step,host,pid in found:
  cmd=procs.get(pid,[])
  if '--out'in cmd and cmd[cmd.index('--out')+1]==out and str(b/'source-140/project/experiments/control_v1/system_upper.py')in cmd:matches.append(dict(step=step,host=host,pid=pid,command=cmd))
 assert len(matches)==1 and matches[0]['host']=='node'+str(node)
 log=Path(out)/'trial-0/router.log';data=log.read_bytes()
 targets.append(dict(target=matches[0],old_spec=str(p),old_sha256=sha(p),queue_state=state,job_details=details,log=dict(path=str(log),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),tail=data.decode().splitlines()[-3:])))
 for seed,gap in ([(1580,64),(1582,512)]if node==3 else[(1581,256),(1583,1024)]):
  dest=base/'cap-capacity-candidates'/str(seed);f=queue/'pending'/('00-j-sready158-internal-channel-'+str(seed)+'.json');assert not dest.exists()and not f.exists()
  a=['--manifest',base/'selected/physical.json','--graph',base/'topology/boundary-graph.json','--pg-wrappers',base/'fixed-pg-wrappers','--cap-lower-bound-only','--pin-aware-placement','--electrical-placement-report',base/'cap-initial/wire-cap-lower-bound.json','--placement-capacity-target','.35','--seed',seed,'--channel-gap-um',gap,'--out',dest]
  spec=dict(script='system_upper.py',source_root=str(source),forecast_gib=32,requires=[str(base/'cap-initial/receipt.json')],args=list(map(str,a)))
  newtasks.append((f,spec,seed,gap))
record.mkdir();(record/'verified-before.json').write_text(json.dumps(dict(time=time.time(),targets=targets,reason='Actual large-halo mature routes still hundreds of thousands of shorts; effort50 changes overflow only about3percent. Compare smaller density objective .35 with actual internal gaps64/256/512/1024 while retaining all native masks and209 Link8 rigid offsets. Replace only two verified own duplicate source140 searches; other identical placement controls and all three mature routes continue. No physical gate change, no parent/R/other task changes.'),indent=2))
rows=[]
for f,spec,seed,gap in newtasks:
 tmp=f.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(f);rows.append(dict(path=str(f),sha256=sha(f),seed=seed,gap_um=gap))
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,source_manifest_sha256=sha(source/'source-manifest.json'),whole_system_qualified=False),indent=2))
for row in targets:
 subprocess.run(['scancel',row['target']['step']],check=True)
(record/'cancelled.json').write_text(json.dumps(dict(time=time.time(),steps=[r['target']['step']for r in targets])))
print(json.dumps(dict(queued=rows,retired_exact_steps=[r['target']['step']for r in targets],whole_system_qualified=False)))
'''
compile(q,'internal-channel-preflight158','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
