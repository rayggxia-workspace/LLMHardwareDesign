import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162')
import hashlib,time,re,subprocess
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();new=b/'route-selection-102/sready344-r256-placement3071/tasks.json';nr=json.loads(new.read_text());assert len(nr['tasks'])==14
for row in nr['tasks']:assert sha(row['path'])==row['sha256']and row['spec']['source_root']==str(b/'source-335')
record=b/'route-selection-102/sready345-r256-node6-refill';assert not record.exists();record.mkdir()
for node,job,queuepath,name,seed,source in [(6,95101,'dynamic-02/node6','00-k-sready163clear-route-1631',1631,157),(6,95101,'dynamic-02/node6','00-k-sready169local-route-1691',1691,157)]:
 queue=b/queuepath;old=queue/'pending'/(name+'.json');spec=json.loads(old.read_text());args=spec['args'];out=Path(args[args.index('--out')+1]);assert spec['script']=='system_upper.py'and spec['source_root']==str(b/('source-'+str(source)))and out==b/('s-ready-composition-01/1391/upper-candidates/'+str(seed)+'/route')
 state=json.loads((queue/'queue-state.json').read_text());assert name in state['active'];replacement=[r for r in nr['tasks']if Path(r['path']).parent==queue/'pending'and r['spec']['script']=='system_upper.py'];assert len(replacement)==2
 details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node'+str(node)+' 'in details
 steps=subprocess.check_output(['scontrol','show','step',str(job),'-o'],universal_newlines=True);found=[m.groups()for m in re.finditer(r'StepId=('+str(job)+r'\.\d+).*?SrunHost:Pid=(node\d+):(\d+)',steps)]
 code="import os,json;d={}"+chr(10)+"for p in "+repr([r[2]for r in found])+":"+chr(10)+" try:"+chr(10)+"  assert os.stat('/proc/'+p).st_uid==10011;d[p]=open('/proc/'+p+'/cmdline','rb').read().decode().split(chr(0))"+chr(10)+" except OSError:pass"+chr(10)+"print(json.dumps(d))"
 procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));targets=[]
 for step,host,pid in found:
  cmd=procs.get(pid,[])
  if '--out'in cmd and cmd[cmd.index('--out')+1]==str(out)and str(b/('source-'+str(source)+'/project/experiments/control_v1/system_upper.py'))in cmd:targets.append(dict(step=step,host=host,pid=pid,command=cmd))
 assert len(targets)==1 and targets[0]['host']=='node'+str(node)
 log=out/('trial-0/router.log'if node==25 else'openroad-search/case-0/openroad.log');raw=log.read_bytes()
 if node==25:
  rounds=[json.loads(l)for l in raw.decode().splitlines()if l.startswith('{')and '"conflict_nodes"'in l];assert rounds and rounds[-1]['conflict_nodes']>0;progress=rounds[-3:]
 else:
  counts=re.findall(r'with (\d+) violations',raw.decode());assert counts and int(counts[-1])>0;progress=dict(last_actual_violations=int(counts[-1]))
 before=dict(time=time.time(),target=targets[0],old_spec=str(old),old_spec_sha256=sha(old),old_log=dict(path=str(log),bytes=len(raw),prefix_sha256=hashlib.sha256(raw).hexdigest(),actual_progress=progress),replacement=replacement[0],replacement_record_sha256=sha(new),queue_state=state,job_details=details,whole_system_qualified=False,reason='Two genuine345-instance R256 alternative3071 route chains and all12 successors queued after actual whole-native and measured native/input-pin necessary placements passed. Retain current3070 candidate searches and unchanged qualified types. Retire only this exact own old235-instance duplicate search; retain all old specs/partials and other comparison runs. Parent allocations, original4x16/6x16 dynamic/memory gate, externalR and other tasks unchanged. An incomplete search retirement is not a final physical fail or success.')
 (record/('node'+str(node)+'-'+str(seed)+'-verified-before.json')).write_text(json.dumps(before,indent=2));subprocess.run(['scancel',targets[0]['step']],check=True);(record/('node'+str(node)+'-'+str(seed)+'-cancelled.json')).write_text(json.dumps(dict(time=time.time(),step=targets[0]['step'])));print('retired only',targets[0]['step'],'on node',node)
'''
compile(q,'retire345','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
