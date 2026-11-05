from pathlib import Path
import json,hashlib,subprocess,re,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');record=b/'route-selection-102/sready957-pin-release-node6';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
replacement=b/'route-selection-102/sready948-pin-release-fullchains/tasks.json';tasks=json.loads(replacement.read_text());assert len(tasks['tasks'])==14
for row in tasks['tasks']:assert sha(row['path'])==row['sha256']
assert json.loads((b/'r256-pin-release-regression-948/receipt.json').read_text())['passed'];assert json.loads((b/'r256-pin-release-source-audit-950/receipt.json').read_text())['passed'];assert json.loads((b/'r256-final-chain-binding-audit-956/receipt.json').read_text())['passed'];record.mkdir();mem=json.loads(subprocess.check_output(['srun','--jobid=97097','--overlap','-n1','-c1','python3','-c',"import json;print(json.dumps({k:int(v.split()[0]) for k,v in [l.split(':',1)for l in open('/proc/meminfo')] if k=='MemAvailable'}))"],universal_newlines=True));assert mem['MemAvailable']/1048576>323.2;(record/'fresh-memory.json').write_text(json.dumps(dict(time=time.time(),mem=mem,maximum_forecasts_gib=256,required_available_gib=323.2,passed=True)))
(record/'replacement.json').write_text(json.dumps(dict(path=str(replacement),sha256=sha(replacement),whole_system_qualified=False)))
for node,job,folder,seed,expected_source,minimum_failed in [(6,97097,'dynamic-08/node6',8592,'source-828',0)]:
 mem=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',"import json;print(json.dumps({k:int(v.split()[0]) for k,v in [l.split(':',1)for l in open('/proc/meminfo')]if k=='MemAvailable'}))"],universal_newlines=True));assert mem['MemAvailable']/1048576>323.2;(record/('fresh-memory-'+str(seed)+'.json')).write_text(json.dumps(dict(time=time.time(),mem=mem,required_available_gib=323.2,passed=True)))
 queue=b/folder;state=json.loads((queue/'queue-state.json').read_text());matches=[]
 for name in state['active']:
  path=queue/'pending'/(name+'.json');spec=json.loads(path.read_text());a=spec['args']
  if '--out'in a and Path(a[a.index('--out')+1]).parent.name==str(seed):matches.append((path,spec))
 assert len(matches)==1;(path,spec)=matches[0];a=spec['args'];out=a[a.index('--out')+1];source=Path(spec['source_root']);assert spec['script']=='system_upper.py'and source.parent==b and re.fullmatch('source-[0-9]+',source.name)and(source/'source-manifest.json').is_file()
 graph=Path(a[a.index('--graph')+1]);g=json.loads(graph.read_text());assert len(g['instances'])==345 and 'macro_r'in g['instances']
 current=b/'r256-composition-453/topology/boundary-graph.json';cg=json.loads(current.read_text());assert len(cg['instances'])==345 and 'macro_r'in cg['instances']
 details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node'+str(node)+' 'in details
 steps=subprocess.check_output(['scontrol','show','step',str(job),'-o'],universal_newlines=True);found=[m.groups()for m in re.finditer(r'StepId=('+str(job)+r'\.\d+).*?SrunHost:Pid=(node\d+):(\d+)',steps)]
 code="import os,json;d={}"+chr(10)+"for p in "+repr([r[2]for r in found])+":"+chr(10)+" try:"+chr(10)+"  assert os.stat('/proc/'+p).st_uid==10011;d[p]=open('/proc/'+p+'/cmdline','rb').read().decode().split(chr(0))"+chr(10)+" except OSError:pass"+chr(10)+"print(json.dumps(d))"
 procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));targets=[]
 for step,host,pid in found:
  cmd=procs.get(pid,[])
  if '--out'in cmd and cmd[cmd.index('--out')+1]==out and str(source/'project/experiments/control_v1/system_upper.py')in cmd:targets.append(dict(step=step,host=host,pid=pid,command=cmd))
 assert len(targets)==1 and targets[0]['host']=='node'+str(node)
 logs=[]
 for f in [Path(out)/'router.log',Path(out)/'trial-0/router.log']:
  if f.exists():logs.append(dict(path=str(f),bytes=f.stat().st_size,sha256=sha(f),tail=f.read_text()[-1200:]))
 assert logs
 assert source.name==expected_source and graph==current ;actual=next(x for x in json.loads((b/'r256-native-batch-admission-953/receipt.json').read_text())['rows']if x['path']==str(path));assert sha(path)==actual['sha256']
 assert json.loads((b/'r256-padding-final-function-audit-472/receipt.json').read_text())['passed']and json.loads((b/'r256-bidirectional-search-regression-500/receipt.json').read_text())['passed']
 attempts=[]
 for f in Path(out).glob('trial-*/router.log'):
  lines=f.read_text().splitlines();last=lines[-1]if lines else '';failed=last.startswith(('Locked-source optimistic wire budget exceeded by this search:','disconnected tree:','disconnected finite-resource tree:'))
  attempts.append(dict(path=str(f),sha256=sha(f),failed_message=last if failed else None))
 assert 16<=len(attempts)<=64;assert all(Path(r['path']).stat().st_size>0 for r in attempts)
 row=dict(time=time.time(),target=targets[0],job_details=details,spec=str(path),spec_sha256=sha(path),old_graph=str(graph),old_graph_sha256=sha(graph),expected_old_graph=str(current),expected_old_graph_sha256=sha(current),logs=logs,prior_attempts=attempts,whole_system_qualified=False,reason='Replace only exact own8592 recovery859 source828 fullgraph maze16K baseline with9491 source947 refresh8+ordinary-first+temporary-reservation-release full453/S5380/S1350/R256 seven-stage chain. Keep8301 originalmaze64K,6360,9060/1 and9280/1 other active controlled baselines. Actual948/950/956 required, fresh953rawSHA UID/job/node6 PID/cmd/source/out/graph and323.2GiB actualMemAvailable for256GiB forecast checked.940actualnative-zero/full-disconnected snapshot and944independent168cell target island motivate release of only unwired ordinary proxies; actualM11landings and native frozen paths unchanged. All original sources/specs/failures/partials retained; no other own/foreign/externalR or parent touched, and all physical/final gates retained with no acceptance inferred.')
 (record/(str(seed)+'-verified-before.json')).write_text(json.dumps(row,indent=2));subprocess.run(['scancel',targets[0]['step']],check=True);(record/(str(seed)+'-cancelled.json')).write_text(json.dumps(dict(time=time.time(),step=targets[0]['step'])));print('refilled verified own partial pool',seed,targets[0]['step'])
