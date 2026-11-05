from pathlib import Path
import subprocess,shlex,json,time
h=Path(__file__).parent;out=h/'control162-watch662';assert not out.exists();out.mkdir();started=time.monotonic();known={};prior=None;failure_floor=None
code=r'''from pathlib import Path
import json,time,statistics,collections,sys
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');known=json.loads(sys.argv[1]);active=[]
for folder in ['dynamic-05/node2','dynamic-02/node3','dynamic-05/node4','dynamic-03/node5','dynamic-02/node6','dynamic-04/node25','dynamic-07/node7','dynamic-06/node26']:
 q=b/folder;state=json.loads((q/'queue-state.json').read_text())
 for name in state['active']:
  spec=json.loads((q/'pending'/(name+'.json')).read_text());a=spec['args'];active.append(dict(queue=folder,name=name,script=spec['script']))
  if spec['script']=='system_upper.py'and'--seed'in a:
   route=Path(a[a.index('--out')+1]);assert route.name=='route'and b in route.parents
   known[str(route.parent)]=dict(source=spec['source_root'],graph=a[a.index('--graph')+1],queue=folder,name=name)
rows=[]
for path,meta in sorted(known.items()):
 root=Path(path);rounds={};patterns={};progress=[];fail=[];logs=list((root/'route').glob('trial-*/router.log'))
 for p in logs:
  index=int(p.parent.name.split('-')[1]);last=None
  with p.open('rb')as f:
   f.seek(0,2);size=f.tell();f.seek(max(0,size-65536));raw=f.read().decode(errors='replace')
  lines=raw.splitlines()
  if size>65536:lines=lines[1:]
  for line in lines:
   if not line.startswith('{'):continue
   try:d=json.loads(line)
   except ValueError:continue
   if 'routed'in d:last=d
   if index<16 and'conflict_nodes'in d:rounds.setdefault(d['round'],[]).append(d['excess_occupancy'])
   if index<16 and'zero_pattern_hits'in d:patterns.setdefault(d['round'],[]).append(d)
  if last:progress.append((last['round'],last['routed']))
  if lines and not lines[-1].startswith('{'):fail.append(lines[-1])
 receipts=[]
 for stage in ['route','geometry','pg-audit','timing/low','timing/base','timing/high','delivery']:
  p=root/stage/'receipt.json'
  if not p.exists():continue
  try:d=json.loads(p.read_text())
  except(OSError,ValueError):continue
  receipts.append(dict(path=str(p),passed=d.get('passed'),stage=d.get('stage'),error=d.get('error')))
 complete=[k for k,v in rounds.items()if len(v)==16];latest=max(complete)if complete else None
 metric=dict(round=latest,initial_trials=16,mean_excess=statistics.mean(rounds[latest]))if latest is not None else None
 paired={str(k):dict(mean_hits=statistics.mean(x['zero_pattern_hits']for x in v),mean_fallbacks=statistics.mean(x['zero_pattern_fallbacks']for x in v))for k,v in patterns.items()if len(v)==16}
 rows.append(dict(root=path,metadata=meta,attempt_logs=len(logs),progress=[min(progress),max(progress)]if progress else[],latest_complete_initial16=metric,paired_initial16_patterns=paired,failures=dict(collections.Counter(fail)),receipts=receipts))
print(json.dumps(dict(time=time.time(),known=known,active=active,rows=rows,whole_system_qualified=False)))
'''
while time.monotonic()-started<3600:
 try:
  command='python3 -c '+shlex.quote(code)+' '+shlex.quote(json.dumps(known))
  raw=subprocess.check_output(['ssh','-o','ConnectTimeout=12','yuzelu@10.129.166.172',command],timeout=45);d=json.loads(raw);known=d['known'];p=out/(str(time.time_ns())+'.json');p.write_bytes(raw)
  sig=[dict(root=r['root'],metric=r['latest_complete_initial16'],patterns=r['paired_initial16_patterns'],failures=r['failures'],receipts=r['receipts'])for r in d['rows']]
  if sig!=prior:print(json.dumps(dict(event='cohort_or_gate_changed',snapshot=str(p),known_roots=len(known),active_steps=len(d['active']),changed=[r for r in sig if r['metric']or r['failures']or r['receipts']])),flush=True);prior=sig
  failures={r['root']:sum(r['failures'].values())for r in d['rows']};new_failure=failure_floor is not None and any(n>failure_floor.get(root,0)for root,n in failures.items());failure_floor=failures
  if new_failure or any(r['receipts']for r in d['rows']):print('Actual route failure/final-stage receipt: return for diagnosis',flush=True);break
 except(subprocess.SubprocessError,ValueError)as exc:print(json.dumps(dict(event='metadata_read_retry',error=str(exc))),flush=True)
 time.sleep(25)
print(json.dumps(dict(ended=True,elapsed=time.monotonic()-started)),flush=True)
