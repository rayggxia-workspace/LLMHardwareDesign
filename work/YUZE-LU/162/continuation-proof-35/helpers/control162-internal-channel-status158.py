"""Read actual diagnostics, occupancy and memory; never infer qualification."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391'
for node in [3,6]:
 d=json.loads((b/'dynamic-02'/('node'+str(node))/'queue-state.json').read_text());print('node',node,'active',d['active']);print('admissions',[(r['name'],r['admitted'])for r in d['memory_admissions']if'sready158'in r['name']])
for seed in range(1580,1584):
 p=c/'cap-capacity-candidates'/str(seed);r=p/'receipt.json';print('seed',seed,'exists',p.exists())
 if r.exists():
  d=json.loads(r.read_text());print('receipt',json.dumps({k:d.get(k)for k in ['passed','stage','placement_proven_cap_infeasible','error']}));f=p/'wire-cap-lower-bound.json'
  if f.exists():
   t=json.loads(f.read_text());print('bound_summary',json.dumps({k:v for k,v in t.items()if k!='rows'}))
 f=p/'placement-search.json'
 if f.exists():
  d=json.loads(f.read_text());print('placement_keys',list(d))
  def report(t):
   if isinstance(t,dict):
    if 'independent_trials'in t:
     best=[r for r in t['independent_trials']if r['seed']==t['selected_seed']][0];print('placement',best['metrics'])
    for v in t.values():report(v)
  report(d)
 if not r.exists():
  logs=sorted(p.glob('electrical-placement-*.log'));print('trial_logs',len(logs),'recent_seconds',round(time.time()-max((f.stat().st_mtime for f in logs),default=time.time())))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
