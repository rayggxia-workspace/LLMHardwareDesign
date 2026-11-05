from pathlib import Path
import subprocess,shlex,json,base64,hashlib,time
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');h=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-52';assert not out.exists()
q="""from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');paths=[]
for folder in [b/'source-435',b/'r256-critical-partition-regression-438',b/'route-selection-102/sready439-critical-first',b/'route-selection-102/sready440-critical-priority-refill']:
 for p in folder.glob('*.json'):paths.append(p)
for folder in ['pending','commands','results']:
 for p in(b/'dynamic-02/node3'/folder).glob('*'):
  if 'sready438'in p.name or 'sready439'in p.name:paths.append(p)
for p in(b/'dynamic-02/node3').glob('*sready43[89]*.log'):paths.append(p)
paths.append(b/'dynamic-02/node3/queue-state.json')
rows=[]
for p in sorted(set(paths)):
 data=p.read_bytes();rows.append(dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),base64=base64.b64encode(data).decode(),active_prefix_snapshot='dynamic-02'in str(p)))
reg=json.loads((b/'r256-critical-partition-regression-438/directional-regression.json').read_text())
print(json.dumps(dict(captured_at=time.time(),rows=rows,regression_summary=dict(passed=reg['passed'],cases=len(reg['cases']),resource_cases=len(reg['resource_cases']),pool_cases=len(reg['dynamic_pool_cases']),memory_cases=len(reg['resource_memory_cases']),critical_cases=len(reg['critical_partition_cases']),critical_round_counts=[len(x['rounds'])for x in reg['critical_partition_cases']],negative_controls=len(reg['rejected'])),whole_system_qualified=False)))
"""
d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir()
for row in d['rows']:
 data=base64.b64decode(row.pop('base64'));assert hashlib.sha256(data).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);row['copied']=True
d['helpers']=[]
for name in ['launch439','queue439-remote','refill440','refill440-remote','current441','collect443']:
 p=h/('control162-'+name+'.py');data=p.read_bytes();rel='helpers/'+p.name;dst=out/rel;dst.parent.mkdir(exist_ok=True);dst.write_bytes(data);d['helpers'].append(dict(relative=rel,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),helpers=len(d['helpers']),regression=d['regression_summary'])))
