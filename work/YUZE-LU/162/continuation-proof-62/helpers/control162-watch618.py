from pathlib import Path
import subprocess,shlex,json,time,datetime
home=Path(__file__).parent;out=home/'control162-watch618';assert not out.exists();out.mkdir();start=time.monotonic();prior=None
q=r'''from pathlib import Path
import json,time,subprocess,statistics,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453/upper-candidates';rows=[]
for seed in [5010,5260,5400,5450,5451,5550,5551,5640,5890,6140,6141]:
 metrics=[];fail=[];rounds={};receipts=[]
 for p in(root/str(seed)/'route').glob('trial-*/router.log'):
  lines=p.read_text().splitlines();last=None
  for x in lines:
   if not x.startswith('{'):continue
   d=json.loads(x);last=d
   if'conflict_nodes'in d:rounds.setdefault(d['round'],[]).append(d)
  if last and'routed'in last:metrics.append((last['round'],last['routed']))
  if lines and not lines[-1].startswith('{'):fail.append(lines[-1])
 for p in(root/str(seed)).glob('*/receipt.json'):
  try:r=json.loads(p.read_text())
  except(OSError,ValueError):continue
  receipts.append(dict(path=str(p),passed=r.get('passed'),stage=r.get('stage'),error=r.get('error')))
 rows.append(dict(candidate=seed,progress_range=[min(metrics),max(metrics)]if metrics else[],completed_rounds={str(k):dict(trials=len(v),mean_excess=statistics.mean(x['excess_occupancy']for x in v))for k,v in rounds.items()},failures=dict(collections.Counter(fail)),receipts=receipts))
s=subprocess.check_output(['scontrol','show','job','96222','-o'],universal_newlines=True);f=dict(x.split('=',1)for x in s.split()if'='in x);print(json.dumps(dict(time=time.time(),rows=rows,eighth={k:f.get(k)for k in['JobId','JobState','Reason','NodeList','NumCPUs','ReqNodeList']},whole_system_qualified=False)))
'''
while time.monotonic()-start<3600:
 try:
  raw=subprocess.check_output(['ssh','-o','ConnectTimeout=12','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45);d=json.loads(raw);name=str(time.time_ns())+'.json';(out/name).write_bytes(raw)
  sig=dict(eighth=d['eighth'],rows=[dict(candidate=x['candidate'],completed_rounds=x['completed_rounds'],failures=x['failures'],receipts=x['receipts'])for x in d['rows']])
  if sig!=prior:print(json.dumps(dict(event='changed',file=str(out/name),snapshot=sig)),flush=True);prior=sig
  if any(x['receipts']for x in d['rows']):print('New final-stage receipt; return for diagnosis/verification',flush=True);break
 except(subprocess.SubprocessError,ValueError)as e:print(json.dumps(dict(event='read_retry',error=str(e))),flush=True)
 time.sleep(25)
print(json.dumps(dict(event='monitor_ended',elapsed_seconds=time.monotonic()-start,whole_system_qualified=False)),flush=True)
