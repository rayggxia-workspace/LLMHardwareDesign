from pathlib import Path
import json,hashlib,subprocess,re,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');record=b/'route-selection-102/sready566-s-local-bidirectional-refill';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
replacement=b/'route-selection-102/sready564-s-local-existing-bidirectional/tasks.json';tasks=json.loads(replacement.read_text());assert len(tasks['tasks'])==7
for row in tasks['tasks']:assert sha(row['path'])==row['sha256']
record.mkdir();(record/'replacement.json').write_text(json.dumps(dict(path=str(replacement),sha256=sha(replacement),whole_system_qualified=False)))
for node,job,folder,seed,expected_source,minimum_failed in [(7,96297,'dynamic-07/node7',3750,'source-358',0)]:
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
 for f in [Path(out)/'router.log',Path(out)/'trial-0/router.log',Path(out)/'openroad-search/case-0/openroad.log']:
  if f.exists():logs.append(dict(path=str(f),bytes=f.stat().st_size,sha256=sha(f),tail=f.read_text()[-1200:]))
 assert logs
 assert source.name==expected_source and graph==current and '--route-trial-attempts'not in a and a[a.index('--router')+1]=='openroad'and a[a.index('--openroad-global-router')+1]=='cugr'
 assert json.loads((b/'r256-padding-final-function-audit-472/receipt.json').read_text())['passed']and json.loads((b/'r256-bidirectional-search-regression-500/receipt.json').read_text())['passed']
 p=Path(out)/'openroad-search/case-0/openroad.log';raw=p.read_text();iterations=[int(x)for x in re.findall(r'Start (\d+)(?:st|nd|rd|th) optimization iteration',raw)];violations=[int(x)for x in re.findall(r'with (\d+) violations',raw)];assert max(iterations)>=10 and violations[-1]>2000000
 attempts=[dict(path=str(p),sha256=sha(p),latest_optimization_iteration=max(iterations),last_reported_violations=violations[-1],scope='Running older359 CUGR search, not terminal failure/infeasibility')]
 row=dict(time=time.time(),target=targets[0],job_details=details,spec=str(path),spec_sha256=sha(path),old_graph=str(graph),old_graph_sha256=sha(graph),current_graph=str(current),current_graph_sha256=sha(current),logs=logs,prior_attempts=attempts,whole_system_qualified=False,reason='Replace only individually verified own source358 older359 CUGR3750 step on node7 after actual at-least10 detailed optimization iterations and still over2million reported violations. Preserve complete original raw logs/partial physical files/source/spec and independent CUGR3751 comparator; do not claim eventual old infeasibility. Actual500-passed original source474 bidirectional component is reused unchanged, current453 real programs/473/480 audit and S5380 reconstruction/three necessary budgets passed. Controlled5640 full seven-stage chain queued first, differs5010 only actual5380 S translation and corresponding residual. This is bounded task-local resource reallocation to the verified current wiring and shorter physical scene, not claimed speed, convergence or final acceptance. Original sixteen-active finite64attempt pool with dynamic refill, real memory admission and every final geometry/nativeXOR/PG/threeRC300MHz/current-function/joint gate retained. Only exact UID/job/node/cmd/out/graph/source-owned step replaced; all parent allocations, other current searches, CUGR3751 and foreign/R tasks stay untouched.')
 (record/(str(seed)+'-verified-before.json')).write_text(json.dumps(row,indent=2));subprocess.run(['scancel',targets[0]['step']],check=True);(record/(str(seed)+'-cancelled.json')).write_text(json.dumps(dict(time=time.time(),step=targets[0]['step'])));print('refilled verified own partial pool',seed,targets[0]['step'])
