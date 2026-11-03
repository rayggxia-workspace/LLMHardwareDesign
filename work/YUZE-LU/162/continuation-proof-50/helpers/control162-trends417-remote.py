from pathlib import Path
import json,time,collections,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-359';out=b/'r256-current-route-trends-417';assert not out.exists();rows=[];inputs={};sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for seed in [3931,4050,4080,4081,4160,4161]:
 groups=collections.defaultdict(list);failures=collections.Counter();logs=list((root/'upper-candidates'/str(seed)/'route').glob('trial-*/router.log'))
 for p in logs:
  raw=p.read_bytes();inputs[str(p)]=hashlib.sha256(raw).hexdigest();lines=raw.decode().splitlines()
  for line in lines:
   if line.startswith('{'):
    d=json.loads(line)
    if 'conflict_nodes'in d:groups[d['round']].append(d)
  if lines and not lines[-1].startswith('{'):failures[lines[-1]]+=1
 rows.append(dict(seed=seed,started_attempts=len(logs),failed_attempts=sum(failures.values()),failures=dict(failures),rounds={k:dict(completed_attempts=len(v),minimum_conflict_positions=min(r['conflict_nodes']for r in v),maximum_conflict_positions=max(r['conflict_nodes']for r in v),mean_excess_occupancy=sum(r['excess_occupancy']for r in v)/len(v),mean_occupied_cells=sum(r['occupied_cells']for r in v)/len(v))for k,v in groups.items()}))
for seed in [3690,4140,4141]:
 p=root/'cap-candidates'/str(seed)/'placement.json';inputs[str(p)]=sha(p)
for folder in ['dynamic-05/node2','dynamic-02/node3','dynamic-05/node4','dynamic-03/node5','dynamic-02/node6','dynamic-04/node25','dynamic-07/node7','dynamic-06/node26']:
 p=b/folder/'queue-state.json'
 if p.exists():inputs[str(p)]=sha(p)
out.mkdir();result=dict(captured_at=time.time(),inputs=inputs,rows=rows,whole_system_qualified=False,scope='Live prefix round metrics, not accepted routes. Conflicting position count and excess occupancy are distinct:3931/4050 mean excess falls after round1 while conflict-position count remains around1.65million. Cannot rank success by one metric or declare convergence. Current22 candidate chains include failed/running/waiting; new414placements have larger area and necessary-high ratios near1, no RC margin claim. Other sources and raw logs retained.')
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(rows=rows,scope=result['scope'])))
