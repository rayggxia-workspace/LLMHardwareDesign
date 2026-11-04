from pathlib import Path
import subprocess,shlex,json,time
h=Path(__file__).parent;out=h/'control162-watch987';assert not out.exists();out.mkdir();started=time.monotonic()
q=r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');rows=[];active=[];deliveries=[]
for folder in ['dynamic-05/node2','dynamic-02/node3','dynamic-05/node4','dynamic-03/node5','dynamic-08/node6','dynamic-04/node25','dynamic-07/node7','dynamic-06/node26']:
 queue=b/folder;state=json.loads((queue/'queue-state.json').read_text());active.append(dict(folder=folder,count=len(state['active'])))
 for name in state['active']:
  s=json.loads((queue/'pending'/(name+'.json')).read_text());a=s['args']
  if '--out'not in a:continue
  route=Path(a[a.index('--out')+1])
  if s['script']!='system_upper.py'or route.name!='route':continue
  trials=[]
  for i in range(16):
   p=route/('trial-'+str(i));v={}
   for label,path in [('native',p/'output.txt.native-prefix.log'),('full',p/'router.log')]:
    if not path.exists():continue
    with path.open('rb')as f:f.seek(0,2);size=f.tell();f.seek(max(0,size-16384));lines=f.read().decode(errors='replace').splitlines()
    records=[]
    for line in lines[1:]if size>16384 else lines:
     if line.startswith('{'):
      try:records.append(json.loads(line))
      except ValueError:pass
    v[label]=next((r for r in reversed(records)if 'conflict_nodes'in r),None)
    if label=='full':v['native_passed']=any(r.get('native_prefix_stage_passed')for r in records)
   if v:trials.append(v)
  receipts=[]
  for stage in ['route','geometry','pg-audit','timing/low','timing/base','timing/high','delivery']:
   p=route.parent/stage/'receipt.json'
   if p.exists():
    d=json.loads(p.read_text());receipts.append(dict(stage=stage,passed=d.get('passed'),error=d.get('error')))
  rows.append(dict(seed=route.parent.name,trials=trials,receipts=receipts))
for p in(b/'r256-composition-453/upper-candidates').glob('*/delivery/receipt.json'):
 d=json.loads(p.read_text());deliveries.append(dict(path=str(p),passed=d.get('passed'),error=d.get('error')))
print(json.dumps(dict(time=time.time(),active=active,rows=rows,deliveries=deliveries,whole_system_qualified=False)))
'''
prior=None
while time.monotonic()-started<3600:
 try:
  raw=subprocess.check_output(['ssh','-o','ConnectTimeout=12','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45);d=json.loads(raw);(out/(str(time.time_ns())+'.json')).write_bytes(raw)
  sig=dict(deliveries=d['deliveries'],milestones=[dict(seed=r['seed'],native_passed=sum(bool(t.get('native_passed'))for t in r['trials']),receipts=r['receipts'])for r in d['rows']])
  if sig!=prior:
   print(json.dumps(dict(time=d['time'],active=sum(r['count']for r in d['active']),nodes=len(d['active']),milestones=[r for r in sig['milestones']if r['native_passed']or r['receipts']],deliveries=d['deliveries'],snapshot=str(out))),flush=True);prior=sig
  if d['deliveries']or any(r['receipts']for r in d['rows']):break
 except(subprocess.SubprocessError,ValueError)as e:print(json.dumps(dict(retry=str(e))),flush=True)
 time.sleep(30)
print(json.dumps(dict(ended=True,seconds=time.monotonic()-started)),flush=True)

