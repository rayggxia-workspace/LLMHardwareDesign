from pathlib import Path
import subprocess,shlex,json,time
h=Path(__file__).parent;out=h/'control162-watch601';assert not out.exists();out.mkdir();start=time.monotonic();prior=None
code=r'''from pathlib import Path
import json,statistics,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-453/upper-candidates');rows=[]
for seed in [5640,5890]:
 out=b/str(seed);rounds={};patterns={};progress=[];failures=[]
 for p in(out/'route').glob('trial-*/router.log'):
  lines=p.read_text().splitlines();last=None
  for line in lines:
   if not line.startswith('{'):continue
   d=json.loads(line)
   if 'routed'in d:last=d
   if 'conflict_nodes'in d:rounds.setdefault(d['round'],[]).append(d['excess_occupancy'])
   if 'zero_pattern_hits'in d:patterns.setdefault(d['round'],[]).append(d)
  if last:progress.append((last['round'],last['routed']))
  if lines and not lines[-1].startswith('{'):failures.append(lines[-1])
 receipts=[]
 for p in out.glob('*/receipt.json'):
  d=json.loads(p.read_text());receipts.append(dict(path=str(p),passed=d.get('passed'),stage=d.get('stage'),error=d.get('error')))
 rows.append(dict(candidate=seed,rounds={k:dict(trials=len(v),mean_excess=statistics.mean(v))for k,v in rounds.items()},patterns={k:dict(trials=len(v),hits=sum(x['zero_pattern_hits']for x in v),fallbacks=sum(x['zero_pattern_fallbacks']for x in v),checks=sum(x['zero_pattern_point_checks']for x in v))for k,v in patterns.items()},progress=[min(progress),max(progress)]if progress else[],failures=failures,receipts=receipts))
print(json.dumps(dict(time=time.time(),rows=rows,whole_system_qualified=False)))
'''
while time.monotonic()-start<3600:
 try:
  raw=subprocess.check_output(['ssh','-o','ConnectTimeout=12','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],timeout=45);d=json.loads(raw);p=out/(str(time.time_ns())+'.json');p.write_bytes(raw)
  signature=[{k:v for k,v in r.items()if k!='progress'}for r in d['rows']]
  if signature!=prior:print(json.dumps(dict(file=str(p),snapshot=d)),flush=True);prior=signature
  if any(r['failures']or r['receipts']for r in d['rows']):break
 except(subprocess.SubprocessError,ValueError)as e:print(json.dumps(dict(error=str(e))),flush=True)
 time.sleep(25)
print(json.dumps(dict(ended=True,elapsed=time.monotonic()-start)),flush=True)
