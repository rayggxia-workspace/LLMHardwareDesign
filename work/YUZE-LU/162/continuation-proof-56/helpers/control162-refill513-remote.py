from pathlib import Path
import json,hashlib,subprocess,re,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');record=b/'route-selection-102/sready513-current-search-cost-refill';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
replacement=b/'route-selection-102/sready511-separate-ordinary-cost/tasks.json';tasks=json.loads(replacement.read_text());assert len(tasks['tasks'])==8
for row in tasks['tasks']:assert sha(row['path'])==row['sha256']
record.mkdir();(record/'replacement.json').write_text(json.dumps(dict(path=str(replacement),sha256=sha(replacement),whole_system_qualified=False)))
for node,job,folder,seed in [(6,95101,'dynamic-02/node6',3931)]:
 queue=b/folder;state=json.loads((queue/'queue-state.json').read_text());matches=[]
 for name in state['active']:
  path=queue/'pending'/(name+'.json');spec=json.loads(path.read_text());a=spec['args']
  if '--seed'in a and a[a.index('--seed')+1]==str(seed):matches.append((path,spec))
 assert len(matches)==1;(path,spec)=matches[0];a=spec['args'];out=a[a.index('--out')+1];source=Path(spec['source_root']);assert spec['script']=='system_upper.py'and source.parent==b and re.fullmatch('source-[0-9]+',source.name)and(source/'source-manifest.json').is_file()
 graph=Path(a[a.index('--graph')+1]);g=json.loads(graph.read_text());assert len(g['instances'])==345 and 'macro_r'in g['instances']
 current=b/'r256-composition-359/topology/boundary-graph.json';cg=json.loads(current.read_text());assert len(cg['instances'])==345 and 'macro_r'in cg['instances']
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
 assert source.name=='source-388'and graph==current
 assert json.loads((b/'r256-padding-final-function-audit-472/receipt.json').read_text())['passed']
 row=dict(time=time.time(),target=targets[0],job_details=details,spec=str(path),spec_sha256=sha(path),old_graph=str(graph),old_graph_sha256=sha(graph),current_graph=str(current),current_graph_sha256=sha(current),logs=logs,whole_system_qualified=False,reason='Replace exactly one verified own current359 older-source388 search3931 after actual453 programs and independent472 audit passed and494 exact-prefix profile identifies ordinary S/PG heap search. New source510 actual regression then controlled5120 full7stage candidate453 queued first. This is resource reallocation to test a specific measured search hypothesis, not a failure or mathematical infeasibility claim about old3931. Preserve source/spec/raw/partial route and all other current searches. Only exact owned step retired; parent, externalR and foreign tasks untouched. No fixed macro or gate changes. Preserve all original source/spec/partial output, other steps, parent allocations, external R and foreign tasks. No claim old search mathematically impossible; diagnostic evidence retained.')
 (record/(str(seed)+'-verified-before.json')).write_text(json.dumps(row,indent=2));subprocess.run(['scancel',targets[0]['step']],check=True);(record/(str(seed)+'-cancelled.json')).write_text(json.dumps(dict(time=time.time(),step=targets[0]['step'])));print('refilled verified own older-source search',seed,targets[0]['step'])
