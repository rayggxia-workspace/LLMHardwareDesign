from pathlib import Path
import json,hashlib,statistics,time,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-search-phase-profile-494/profile';rp=root/'receipt.json'
if not rp.exists():print('profile494 pending');raise SystemExit(0)
r=json.loads(rp.read_text());assert r['passed']and not r['route_qualified'];out=b/'r256-search-phase-analysis-498';assert not out.exists();g=json.loads((b/'r256-composition-453/topology/boundary-graph.json').read_text());bindings={};trials=[];durations=[];stops=[]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for i in range(16):
 p=root/('trial-'+str(i))/'profile.log';bindings[str(p)]=sha(p);events=[]
 for line in p.read_text().splitlines():
  try:d=json.loads(line)
  except ValueError:continue
  if 'diagnostic_event'in d:events.append(d)
 starts={};completed=[]
 for d in events:
  if d['diagnostic_event']=='net_start':starts[d['net']]=d
  elif d['diagnostic_event']=='net_end':
   start=starts.pop(d['net']);elapsed=d['monotonic_ms']-start['monotonic_ms'];assert elapsed>=0;row=dict(trial=i,net=d['net'],milliseconds=elapsed,ordinary_heap_pops=d['ordinary_heap_pops'],wire_limited=start['wire_limited'],search_weight=start['search_weight']);completed.append(row);durations.append(row)
 last=events[-1]if events else None;trial=next(t for t in r['trials']if t['trial']==i);stops.append(dict(trial=i,returncode=trial['returncode'],termination_reason=trial['termination_reason'],last=last,unfinished=list(starts.values())))
 trials.append(dict(trial=i,diagnostic_events=len(events),completed_nets=len(completed),max_observed_completed_milliseconds=max([x['milliseconds']for x in completed]or[0]),ordinary_heap_pops_completed=sum(x['ordinary_heap_pops']for x in completed)))
def netrow(name):
 bit=name[4:]
 if bit not in g['connections']:
  assert bit in ['PG_VDD','PG_VSS']
  return dict(net=name,kind='fixed-power-network',binding='Actual original4760 router input/SHA in494 profile receipt; PG is added by original source-bound fixed-PG wrapper mechanism, outside signal boundary graph.')
 c=g['connections'][bit];return dict(net=name,driver=c['driver'],sinks=c['sinks'],sink_count=len(c['sinks']))
top=sorted(durations,key=lambda d:d['milliseconds'],reverse=True)[:20];names=set(d['net']for d in top)
for d in stops:
 for x in d['unfinished']:names.add(x['net'])
result=dict(passed=True,whole_system_qualified=False,route_qualified=False,time=time.time(),profile_receipt_sha256=sha(rp),inputs=bindings,trials=trials,stops=stops,slowest_completed_nets=top,actual_graph_nets=[netrow(n)for n in sorted(names)],scope='Actual bounded software instrumentation at round7/routed>=1200 only; source removal exact and every actual original first7round full stdout prefix replayed exactly. Times are monotonic inside this instrumented diagnostic, not inferred original durations. Net names and actual source/sink pins bound to actual453 graph. Finite diagnostic stop is not route infeasibility or physical qualification.');out.mkdir();(out/'receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(passed=True,completed_nets=sum(x['completed_nets']for x in trials),stops=stops[:2],slowest_completed=top[:4],selected_net_count=len(names))))
