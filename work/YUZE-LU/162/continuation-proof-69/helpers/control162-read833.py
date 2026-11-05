import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time,subprocess
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-older-placement-live-readback-833';assert not out.exists();out.mkdir();rows=[];nodes=[]
for folder,tag,job in [('dynamic-02/node6',6720,95101),('dynamic-03/node5',6920,95155)]:
 queue=b/folder;state=json.loads((queue/'queue-state.json').read_text());forecasts=[]
 for name in state['active']:
  p=queue/'pending'/(name+'.json');s=json.loads(p.read_text());a=s['args'];forecasts.append(dict(name=name,forecast_gib=s['forecast_gib']))
  if '--out'in a and Path(a[a.index('--out')+1]).parent.name==str(tag):
   raw=p.read_bytes();row=dict(tag=tag,path=str(p),sha256=hashlib.sha256(raw).hexdigest(),spec=s);rows.append(row);(out/(str(tag)+'-spec.json')).write_bytes(raw)
 mem=subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',"import json;print(json.dumps({k:int(v.split()[0]) for k,v in [l.split(':',1)for l in open('/proc/meminfo')] if k=='MemAvailable'}))"],universal_newlines=True);nodes.append(dict(folder=folder,job=job,forecasts=forecasts,mem=json.loads(mem)))
assert len(rows)==2;(out/'receipt.json').write_text(json.dumps(dict(passed=True,time=time.time(),whole_system_qualified=False,rows=rows,nodes=nodes),indent=2));print(json.dumps(dict(rows=[dict(tag=r['tag'],sha256=r['sha256'],source=r['spec']['source_root'],graph=r['spec']['args'][r['spec']['args'].index('--graph')+1],placement=r['spec']['args'][r['spec']['args'].index('--reuse-placement')+1],forecast=r['spec']['forecast_gib'])for r in rows],nodes=nodes)))
'''
compile(q,'remote739','exec');print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
