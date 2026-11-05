from pathlib import Path
import subprocess,shlex,json,time
q='''from pathlib import Path
import json
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');rows=[]
for tag in [9810,9811]:
 trials=[]
 for p in sorted((b/'r256-composition-453/upper-candidates'/str(tag)/'route').glob('trial-*/router.log')):
  with p.open('rb')as f:
   f.seek(0,2);size=f.tell();parts=[];offset=size;found=None
   while offset>0 and size-offset<16000000 and found is None:
    take=min(offset,262144);offset-=take;f.seek(offset);chunk=f.read(take);parts.insert(0,chunk)
    data=b''.join(parts)
    for line in reversed(data.splitlines()[1:]if offset else data.splitlines()):
     if b'"conflict_nodes"'in line:
      try:found=json.loads(line);break
      except ValueError:pass
  trials.append(dict(trial=p.parent.name,bytes=size,last_global=found))
 rows.append(dict(candidate=tag,trials=trials))
print(json.dumps(rows))
'''
raw=subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=50);out=Path(__file__).parent/'control162-progress990';out.mkdir(exist_ok=True);(out/(str(time.time_ns())+'.json')).write_bytes(raw)
for row in json.loads(raw):
 v=[t['last_global']for t in row['trials']if t['last_global']];print(json.dumps(dict(candidate=row['candidate'],trials=len(row['trials']),rounds=sorted(set(x['round']for x in v)),conflicts=sorted(x['conflict_nodes']for x in v),minimum_excess=min((x['excess_occupancy']for x in v),default=None))))
