from pathlib import Path
import subprocess,shlex,json
q=r'''from pathlib import Path
import json,time,hashlib,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-real-phase-timing-731';assert not out.exists();out.mkdir();rows=[];groups={};graph=b/'r256-composition-453/topology/boundary-graph.json';g=json.loads(graph.read_text())
for p in(b/'r256-composition-453/upper-candidates/7200/route').glob('trial-*/router.log'):
 raw=p.read_bytes();(out/(p.parent.name+'.log')).write_bytes(raw);starts={}
 for line in raw.decode().splitlines():
  try:d=json.loads(line)
  except ValueError:continue
  if'routing_phase_event'not in d:continue
  key=(d['round'],d['net'])
  if d['routing_phase_event']=='start':starts[key]=d;continue
  if key not in starts:continue
  a=starts.pop(key);kind='finite'if a['wire_limited']else'ordinary-pair'if a['terminal_groups']==2 else'ordinary-multi'
  seconds=(d['monotonic_ns']-a['monotonic_ns'])/1e9;groups.setdefault((a['round'],kind),[]).append(seconds)
  if seconds>=.1:
   c=g['connections'].get(a['net'].removeprefix('net_')if hasattr(str,'removeprefix')else a['net'][4:]);rows.append(dict(trial=p.parent.name,round=a['round'],net=a['net'],seconds=seconds,kind=kind,driver=c['driver']if c else None,sinks=c['sinks']if c and len(c['sinks'])<5 else None))
r=dict(passed=True,time=time.time(),whole_system_qualified=False,graph_sha256=hashlib.sha256(graph.read_bytes()).hexdigest(),sampled_window_only=True,groups=[dict(round=k[0],kind=k[1],count=len(v),sum_seconds=sum(v),max_seconds=max(v))for k,v in sorted(groups.items())],slow=sorted(rows,key=lambda x:-x['seconds']),scope='Actual software monotonic start/end times in bounded last32 critical/first128 ordinary window only,16 running7200 attempts. No whole-round share, algorithmic optimality, hardware waveform, complete route or physical qualification claim. Raw snapshots preserved; incomplete pairs excluded.')
(out/'receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(dict(groups=r['groups'][-6:],slow=r['slow'][:4])))
'''
compile(q,'remote731','exec');r=subprocess.run(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True);print(r.stdout);print(r.stderr[-1000:]if r.returncode else'');assert not r.returncode
