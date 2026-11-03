"""Verify two exact own old children before releasing their c96 slots."""
import subprocess,shlex

q=r'''from pathlib import Path
import subprocess,json,hashlib,re,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');base=b/'s-ready-composition-01/1391';record=b/'route-selection-102/sready193-weighted-local-refill';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();new_record=b/'route-selection-102/s-ready-cpp-weighted-local-source172.json';new=json.loads(new_record.read_text());assert len(new['tasks'])==14 and new['instance_count']==235
verified=[]
for node,job,fam,oldseed,newseed in [(25,95204,4,1445,1853),(26,95119,2,1446,1852)]:
 queue=b/('dynamic-%02d'%fam)/('node'+str(node));name='00-k-sready140-route-'+str(oldseed);old=queue/'pending'/(name+'.json');spec=json.loads(old.read_text());args=spec['args'];out=args[args.index('--out')+1]
 assert spec['source_root']==str(b/'source-140')and spec['script']=='system_upper.py'and args[args.index('--route-heuristic-weight')+1]=='1'and out==str(base/'upper-candidates'/str(oldseed)/'route')
 state=json.loads((queue/'queue-state.json').read_text());assert name in state['active']and len(state['active'])==6
 replacement=[r for r in new['tasks']if r['spec']['script']=='system_upper.py'and '--seed'in r['spec']['args']and r['spec']['args'][r['spec']['args'].index('--seed')+1]==str(newseed)];assert len(replacement)==1
 replacement=replacement[0];np=Path(replacement['path']);ns=replacement['spec'];na=ns['args'];assert np.parent.parent==queue and sha(np)==replacement['sha256']and ns['source_root']==str(b/'source-172')and na[na.index('--route-heuristic-weight')+1]=='4'and na[na.index('--route-congestion-scale')+1]=='1'
 details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and ('NodeList=node'+str(node)+' ')in details
 steps=subprocess.check_output(['scontrol','show','step',str(job),'-o'],universal_newlines=True);found=[m.groups()for m in re.finditer(r'StepId=('+str(job)+r'\.\d+).*?SrunHost:Pid=(node\d+):(\d+)',steps)]
 code="import os,json;d={}"+chr(10)+"for p in "+repr([r[2]for r in found])+":"+chr(10)+" try:"+chr(10)+"  assert os.stat('/proc/'+p).st_uid==10011;d[p]=open('/proc/'+p+'/cmdline','rb').read().decode().split(chr(0))"+chr(10)+" except OSError:pass"+chr(10)+"print(json.dumps(d))"
 procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));targets=[]
 for step,host,pid in found:
  actual=procs.get(pid,[])
  if '--out'in actual and actual[actual.index('--out')+1]==out and str(b/'source-140/project/experiments/control_v1/system_upper.py')in actual:targets.append(dict(step=step,host=host,pid=pid,command=actual))
 assert len(targets)==1 and targets[0]['host']=='node'+str(node)
 log=base/'upper-candidates'/str(oldseed)/'route/trial-0/router.log';raw=log.read_bytes();parsed=[]
 for line in raw.decode().splitlines():
  try:d=json.loads(line)
  except ValueError:continue
  if'excess_occupancy'in d:parsed.append(d)
 assert parsed and parsed[-1]['excess_occupancy']>400000
 verified.append(dict(node=node,oldseed=oldseed,newseed=newseed,target=targets[0],old_spec=str(old),old_spec_sha256=sha(old),job_details=details,queue_state=state,replacement=str(np),replacement_sha256=sha(np),old_log=dict(path=str(log),bytes=len(raw),prefix_sha256=hashlib.sha256(raw).hexdigest(),last_completed_rounds=parsed[-4:])))
record.mkdir();(record/'verified-before.json').write_text(json.dumps(dict(time=time.time(),new_record=str(new_record),new_record_sha256=sha(new_record),targets=verified,reason='Only two individually verified old dense-placement duplicate own children1445/1446, actual rounds22/14 still more than400000 excess vertices. Keep other original controls/parents and all old specs/partials. New measured/local-density placements clear original necessary gates; heuristic4/scale1 is an already-regressed search parameter and keeps every final physical gate. Both full seven-stage replacement chains queued before releasing exact children. Same eight nodes/c96 six16CPU slots and memory guard; no R/other job changes. Incomplete search retirement, not final physical failure.'),indent=2)+'\n')
for row in verified:
 subprocess.run(['scancel',row['target']['step']],check=True)
 (record/('cancelled-'+str(row['oldseed'])+'.json')).write_text(json.dumps(dict(time=time.time(),step=row['target']['step'],replacement=row['replacement'])))
 print('Retired exact own child',row['target']['step'],'for queued16-trial replacement',row['newseed'])
'''
compile(q,'exact_c96_weighted_refill193','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
