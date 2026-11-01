from pathlib import Path
import hashlib,json,shlex,subprocess,time
b=Path('work/YUZE-LU/121/review-20261028');remote='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-938'
bindings={name:hashlib.sha256((b/local).read_bytes()).hexdigest()for name,local in [('manifest.json','stage938-manifest.json'),('node-queue.json','node-queue-938.json')]}
q=r'''from pathlib import Path
import hashlib,json,subprocess
r=Path(REMOTE)
for n,h in BINDINGS.items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==h
state=json.loads((r/'dispatch-state.json').read_text())
if state.get('tasks'):print(json.dumps(dict(status='dispatched',state=state)));raise SystemExit(0)
queue=json.loads((r/'node-queue.json').read_text());deps=queue['tasks'][0]['receipts'];observed={};ready=True
source=r.parent/'block-v1-20261101-926/tasks/revision300-final-source-r/receipt.json'
source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
for dep in deps:
 producer=json.loads(Path(dep['producer_state']).read_text())['tasks'].get(dep['producer_task'],{}).get('status','WAITING')
 observed[dep['path']]=producer
 assert producer not in ('FAILED','BLOCKED'),observed
 if producer!='PASSED':ready=False;continue
 path=Path(dep['path']);receipt=json.loads(path.read_text());assert receipt['passed']and receipt['mode']==dep['mode']
 for name in dep['reports']:
  p=path.parent/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==receipt['outputs'][name]
  proof=json.loads(p.read_text());assert proof['passed']and proof['source_receipt_sha256']==source_sha
if ready:
 subprocess.run(['python3',str(r/'src/project/experiments/block_v1/dispatch.py'),str(r/'manifest.json'),'--submit'],check=True,stdout=subprocess.PIPE)
 state=json.loads((r/'dispatch-state.json').read_text())
print(json.dumps(dict(status='dispatched'if state.get('tasks')else'waiting_actual_gates_or_cap',observed=observed,state=state)))
'''.replace('REMOTE',repr(remote)).replace('BINDINGS',repr(bindings))
while True:
 raw=subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=240)
 d=json.loads(raw);row=dict(captured_epoch=time.time(),**d)
 with Path('.local/issue121/admit938-log.jsonl').open('ab')as f:f.write((json.dumps(row)+'\n').encode())
 print(json.dumps(row),flush=True)
 if d['status']=='dispatched':break
 time.sleep(60)
