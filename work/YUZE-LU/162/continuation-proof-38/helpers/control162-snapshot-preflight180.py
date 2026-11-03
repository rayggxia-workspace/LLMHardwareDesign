"""Queue a bound snapshot fixture before retiring one exact own duplicate search."""
import subprocess, shlex

q = r'''from pathlib import Path
import json,hashlib,subprocess,re,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');base=b/'s-ready-composition-01/1391';source=b/'source-180';queue=b/'dynamic-05/node2'
record=b/'route-selection-102/sready180-bounded-snapshot';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert json.loads((source/'source-manifest.json').read_text())['commit']=='3f4ee5dc09e43bb8066e1266fd44227387c29ae9'
name='00-k-sready140-route-1410';old=queue/'pending'/(name+'.json');spec=json.loads(old.read_text());args=spec['args'];out=args[args.index('--out')+1]
assert spec['source_root']==str(b/'source-140')and spec['script']=='system_upper.py'and args[args.index('--route-heuristic-weight')+1]=='1'and out==str(base/'upper-candidates/1410/route')
state=json.loads((queue/'queue-state.json').read_text());assert name in state['active']and len(state['active'])==4
job=95341;details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True)
assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node2 'in details
steps=subprocess.check_output(['scontrol','show','step',str(job),'-o'],universal_newlines=True)
found=[m.groups()for m in re.finditer(r'StepId=('+str(job)+r'\.\d+).*?SrunHost:Pid=(node\d+):(\d+)',steps)]
code="import os,json;d={}"+chr(10)+"for p in "+repr([r[2]for r in found])+":"+chr(10)+" try:"+chr(10)+"  assert os.stat('/proc/'+p).st_uid==10011;d[p]=open('/proc/'+p+'/cmdline','rb').read().decode().split(chr(0))"+chr(10)+" except OSError:pass"+chr(10)+"print(json.dumps(d))"
procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));targets=[]
for step,host,pid in found:
 actual=procs.get(pid,[])
 if '--out'in actual and actual[actual.index('--out')+1]==out and str(b/'source-140/project/experiments/control_v1/system_upper.py')in actual:targets.append(dict(step=step,host=host,pid=pid,command=actual))
assert len(targets)==1 and targets[0]['host']=='node2'
fixture=b/'router-fastroute24phase-preflight-172';r=json.loads((fixture/'receipt.json').read_text());proof=json.loads((fixture/'openroad-probe.json').read_text())
assert r['passed']and proof['passed']and len(proof['cases'])==3
folder=fixture/'case-0';assert not(folder/'drc.rpt').read_text().strip()and json.loads((folder/'grid-proof.json').read_text())['final_conflicts']==0
record.mkdir();config=record/'fixture-inputs.json';cfg=dict(schema='control162-openroad-search-snapshot-v1',iterations=1,nx=48,ny=48,inputs={n:dict(path=str(folder/n),sha256=sha(folder/n))for n in ['before.odb','route.guide','terminals.json','run.tcl']});config.write_text(json.dumps(cfg,indent=2)+'\n')
logs={}
for seed in [1410,1451]:
 path=base/'upper-candidates'/str(seed)/'route/trial-0/router.log';raw=path.read_bytes();lines=raw.decode().splitlines();logs[str(path)]=dict(bytes=len(raw),prefix_sha256=hashlib.sha256(raw).hexdigest(),last_rounds=[x for x in lines if 'excess_occupancy'in x][-4:],tail=lines[-3:])
assert any('"round":15'in x for x in logs[str(base/'upper-candidates/1410/route/trial-0/router.log')]['last_rounds'])
reason='Replace exact own original dense-placement duplicate1410 after16th search round still~972045 excess vertices, retaining1451 and other original controls, all nine mature CUGR and1770 FastRoute. Search retired incomplete, not declared physical failure. Queue bounded snapshot fixture first so full diagnostic can collect actual short nets/locations from original immutable CUGR ODB/guides. No acceptance change, parent/other/R jobs untouched.'
(record/'verified-before.json').write_text(json.dumps(dict(time=time.time(),target=targets[0],old_spec=str(old),old_spec_sha256=sha(old),job_details=details,queue_state=state,active_log_prefix_snapshots=logs,reason=reason),indent=2))
pending=queue/'pending/00-i-sready180-bounded-snapshot-preflight.json';output=b/'router-bounded-snapshot-preflight-180';assert not pending.exists()and not output.exists()
new=dict(script='system_upper.py',source_root=str(source),forecast_gib=32,requires=[str(fixture/'receipt.json')],args=list(map(str,['--manifest',base/'selected/physical.json','--graph',base/'topology/boundary-graph.json','--openroad-snapshot-config',config,'--out',output])))
temp=pending.with_suffix('.tmp');temp.write_text(json.dumps(new));temp.rename(pending)
(record/'queued.json').write_text(json.dumps(dict(time=time.time(),path=str(pending),spec_sha256=sha(pending),source_manifest_sha256=sha(source/'source-manifest.json'),config_sha256=sha(config)),indent=2))
subprocess.run(['scancel',targets[0]['step']],check=True)
(record/'cancelled.json').write_text(json.dumps(dict(time=time.time(),step=targets[0]['step'])))
print('Queued original-geometry diagnostic fixture first; retired only own duplicate child',targets[0]['step'])
'''
compile(q, 'snapshot180_verified_admission', 'exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
