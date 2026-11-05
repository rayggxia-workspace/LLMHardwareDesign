import subprocess,shlex
code=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-old4340-4390-live-spec-readback-694';assert not out.exists();out.mkdir();rows=[]
for folder,seed in [('dynamic-03/node5',4340),('dynamic-02/node3',4390)]:
 q=b/folder;state=json.loads((q/'queue-state.json').read_text());matches=[]
 for n in state['active']:
  p=q/'pending'/(n+'.json');s=json.loads(p.read_text());a=s['args']
  if '--seed'in a and a[a.index('--seed')+1]==str(seed):matches.append((p,s,a))
 assert len(matches)==1;p,s,a=matches[0];raw=p.read_bytes();row=dict(seed=seed,spec=str(p),sha256=hashlib.sha256(raw).hexdigest(),source=s['source_root'],graph=a[a.index('--graph')+1],trials=a[a.index('--route-trials')+1],trial_attempts=a[a.index('--route-trial-attempts')+1]if '--route-trial-attempts'in a else None,out=a[a.index('--out')+1],log_count=len(list(Path(a[a.index('--out')+1]).glob('trial-*/router.log'))));(out/(str(seed)+'-spec.json')).write_bytes(raw);rows.append(row)
r=dict(passed=True,time=time.time(),whole_system_qualified=False,rows=rows,scope='Read-only exact own active older3594340/4390 spec readback before any reallocation; correct stale fixed-pool/source400 narrative. Actual dynamic trial flags retained in raw specs.No running task or source/spec/output changed.');(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(rows))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],universal_newlines=True))
