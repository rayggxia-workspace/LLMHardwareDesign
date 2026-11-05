import subprocess,shlex
code=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-old359-four-slot-readback-654';assert not out.exists();out.mkdir();rows=[]
for folder,seed,job,node in [('dynamic-05/node2',4270,95341,2),('dynamic-02/node3',4160,95098,3),('dynamic-04/node25',4161,95204,25),('dynamic-05/node4',4250,95391,4)]:
 q=b/folder;state=json.loads((q/'queue-state.json').read_text());matches=[]
 for name in state['active']:
  p=q/'pending'/(name+'.json');spec=json.loads(p.read_text());a=spec['args']
  if '--seed'in a and a[a.index('--seed')+1]==str(seed):matches.append((p,spec,a))
 assert len(matches)==1;p,s,a=matches[0];raw=p.read_bytes();row=dict(seed=seed,job=job,node=node,folder=folder,spec=str(p),sha256=hashlib.sha256(raw).hexdigest(),source=s['source_root'],graph=a[a.index('--graph')+1],trials=a[a.index('--route-trials')+1],trial_attempts=a[a.index('--route-trial-attempts')+1]if '--route-trial-attempts'in a else None,out=a[a.index('--out')+1],log_count=len(list(Path(a[a.index('--out')+1]).glob('trial-*/router.log'))));(out/(str(seed)+'-spec.json')).write_bytes(raw);rows.append(row)
r=dict(passed=True,time=time.time(),whole_system_qualified=False,rows=rows,scope='Read-only complete current spec snapshot of four exact own older candidate slots before considering controlled congestion-scale sweep. No cancellation or queue/source/output modification. Preserve source/graph/mode/specSHA actual facts instead of copying stale assumptions.');(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(rows))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],universal_newlines=True))
