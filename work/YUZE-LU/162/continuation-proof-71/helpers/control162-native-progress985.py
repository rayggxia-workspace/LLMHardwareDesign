from pathlib import Path
import subprocess,shlex,json,time
q=r'''from pathlib import Path
import json,time,statistics,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');rows=[]
for tag in [9810,9811]:
 root=b/'r256-composition-453/upper-candidates'/str(tag);p=root/'route';trials=[]
 for log in sorted(p.glob('trial-*/router.log')):
  def read_tail(path):
   if not path.exists():return[]
   with path.open('rb')as f:f.seek(0,2);size=f.tell();f.seek(max(0,size-262144));lines=f.read().decode(errors='replace').splitlines()
   if size>262144:lines=lines[1:]
   return lines
  lines=read_tail(log);records=[]
  for line in lines:
   if line.startswith('{'):
    try:records.append(json.loads(line))
    except ValueError:pass
  native=read_tail(log.parent/'output.txt.native-prefix.log');ns=[]
  for line in native:
   if line.startswith('{'):
    try:ns.append(json.loads(line))
    except ValueError:pass
  latest=lambda xs,key:next((r for r in reversed(xs)if key in r),None)
  trials.append(dict(trial=log.parent.name,native=latest(ns,'conflict_nodes'),native_routed=latest(ns,'routed'),stage=latest(records,'native_prefix_stage_passed'),full=latest(records,'conflict_nodes'),failure=lines[-1]if lines and not lines[-1].startswith('{')else None))
 receipts=[]
 for stage in ['route','geometry','pg-audit','timing/low','timing/base','timing/high','delivery']:
  f=root/stage/'receipt.json'
  if f.exists():d=json.loads(f.read_text());receipts.append(dict(stage=stage,passed=d.get('passed'),error=d.get('error')))
 rows.append(dict(candidate=tag,trials=trials,receipts=receipts))
print(json.dumps(dict(time=time.time(),rows=rows,whole_system_qualified=False)))
'''
compile(q,'progress867','exec');h=Path(__file__).parent;raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]);out=h/'control162-native-progress985';out.mkdir(exist_ok=True);(out/(str(time.time_ns())+'.json')).write_bytes(raw);d=json.loads(raw)
for row in d['rows']:
 ts=row['trials'];print(json.dumps(dict(candidate=row['candidate'],attempts=len(ts),native_passed=sum(bool(t['stage'])for t in ts),native_rounds=sorted(set(t['native']['round']for t in ts if t['native'])),native_excess=[min([t['native']['excess_occupancy']for t in ts if t['native']],default=None),max([t['native']['excess_occupancy']for t in ts if t['native']],default=None)],full_rounds=sorted(set(t['full']['round']for t in ts if t['full'])),failure_counts=dict(__import__('collections').Counter(t['failure']for t in ts if t['failure'])),receipts=row['receipts'])))

