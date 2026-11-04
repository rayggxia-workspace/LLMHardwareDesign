from pathlib import Path
import subprocess,shlex,json,time,sys
q=r'''from pathlib import Path
import json,time,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');reg=b/'r256-endpoint-escape-regression-810';r=dict(time=time.time(),regression_receipt=None,phases=[])
if(reg/'receipt.json').exists():r['regression_receipt']=json.loads((reg/'receipt.json').read_text())
for f in(b/'r256-composition-453/upper-candidates/SEED/route').glob('trial-*/router.log'):
 events=[];progress=None
 with f.open('rb')as h:
  h.seek(0,2);h.seek(max(0,h.tell()-262144));raw=h.read().decode(errors='replace')
 for line in raw.splitlines():
  try:d=json.loads(line)
  except ValueError:continue
  if'routed'in d:progress=d
  if'routing_phase_event'in d:events.append(d)
 starts={};pairs=[]
 for d in events:
  key=(d['round'],d['net'])
  if d['routing_phase_event']=='start':starts[key]=d
  elif key in starts:
   a=starts.pop(key);pairs.append(dict(round=key[0],net=key[1],seconds=(d['monotonic_ns']-a['monotonic_ns'])/1e9,wire_limited=a['wire_limited'],terminal_groups=a['terminal_groups'],position=a['phase_routed_before']))
 r['phases'].append(dict(trial=f.parent.name,progress=progress,paired_count=len(pairs),slowest=sorted(pairs,key=lambda d:-d['seconds'])[:4],unfinished=list(starts.values())[-1:]))
print(json.dumps(r))
'''
q=q.replace('/SEED/','/'+str(int(sys.argv[1]))+'/')
raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45);d=json.loads(raw);d['candidate']=int(sys.argv[1]);d['route_root']='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-composition-453/upper-candidates/'+sys.argv[1]+'/route';raw=(json.dumps(d)+'\n').encode();out=Path(__file__).parent/'control162-phase827';out=out/sys.argv[1];out.mkdir(parents=True,exist_ok=True);(out/(str(time.time_ns())+'.json')).write_bytes(raw)
print(json.dumps(dict(time=d['time'],regression_passed=d['regression_receipt'].get('passed')if d['regression_receipt']else None,trials=len(d['phases']),selected=d['phases'][:1],seed=int(sys.argv[1]))))
