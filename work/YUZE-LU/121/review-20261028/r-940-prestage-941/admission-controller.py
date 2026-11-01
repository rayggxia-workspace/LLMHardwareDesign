from pathlib import Path
import json,shlex,subprocess,time,hashlib
base='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121';run=base+'/block-v1-20261101-940';local=Path('work/YUZE-LU/121/review-20261028')
bindings={n:hashlib.sha256((local/f).read_bytes()).hexdigest()for n,f in [('manifest.json','stage940-manifest.json'),('node-queue.json','node-queue-940.json')]}
q=r'''from pathlib import Path
import hashlib,json,subprocess
r=Path(RUN)
for n,h in BINDINGS.items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==h
parent=r.parent/'block-v1-20261101-938'
producer_file=parent/'node-queue-state.json'
producer=json.loads(producer_file.read_text())['tasks'].get('revision300-geometry-r',{}).get('status','WAITING')if producer_file.exists()else'WAITING'
state=json.loads((r/'dispatch-state.json').read_text())
if state.get('tasks'):print(json.dumps(dict(status='dispatched',state=state)));raise SystemExit(0)
assert producer not in ('FAILED','BLOCKED'),producer
if producer=='PASSED':
 subprocess.run(['python3',str(r/'src/project/experiments/block_v1/dispatch.py'),str(r/'manifest.json'),'--submit'],check=True,stdout=subprocess.PIPE)
 state=json.loads((r/'dispatch-state.json').read_text())
print(json.dumps(dict(status='dispatched'if state.get('tasks')else'waiting_dependency_or_cap',producer=producer,state=state)))
'''.replace('RUN',repr(run)).replace('BINDINGS',repr(bindings))
out=Path('.local/issue121/admit940-log.jsonl')
while True:
 raw=subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=240)
 d=json.loads(raw);record=dict(captured_epoch=time.time(),**d)
 with out.open('ab')as stream:stream.write((json.dumps(record)+'\n').encode())
 print(json.dumps(record),flush=True)
 if d['status']=='dispatched':break
 time.sleep(60)
