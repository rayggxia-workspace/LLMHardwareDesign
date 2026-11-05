from pathlib import Path
import json,hashlib,time,sys,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');folder=b/'r256-current-program-events-412';out=b/'r256-current-program-event-audit-422';assert not out.exists();out.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed']and receipt['stage']=='actual-final-cell-program-event-trace-only'and not receipt['whole_system_qualified'];bindings={str(folder/'receipt.json'):sha(folder/'receipt.json')}
import os
assert os.environ.get('SLURM_JOB_ID')=='95341'and len(os.sched_getaffinity(0))<=16
state=json.loads((b/'dynamic-05/node2/queue-state.json').read_text());forecasts=sum(json.loads((b/'dynamic-05/node2/pending'/(n+'.json')).read_text())['forecast_gib']for n in state['active'])+4
memory={k:int(v.split()[0])*1024 for k,v in(line.split(':',1)for line in Path('/proc/meminfo').read_text().splitlines())}
required=(forecasts*1.2+16)*1024**3;assert memory['MemAvailable']>required
admission=dict(available_bytes=memory['MemAvailable'],forecast_gib=forecasts,required_bytes=required,admitted=True,own_step_cpus=16)
bindings[str(Path(__file__))]=sha(__file__)
for name,digest in receipt['outputs'].items():assert sha(folder/name)==digest;bindings[str(folder/name)]=digest
for name,digest in receipt['inputs'].items():assert sha(name)==digest
sys.path.insert(0,str(b/'source-411/project/experiments/control_v1'));from program_event_trace import audit
old=json.loads((b/'r256-composition-359/function/receipt.json').read_text());results={};negative=[]
def memory_replay(rows):
 active=None;mem={};reads={};writes=[];known=unknown=committed=0
 for row in rows:
  event=row['event']
  if event=='program_begin':
   assert not reads and not writes;active=(row['case'],row['run']);mem={}
  elif event=='AR':
   assert active==(row['case'],row['run'])and row['id']not in reads;assert row['addr']+16*row['beats']<=0x1200040000;reads[row['id']]=[row['addr'],row['beats'],0]
  elif event=='R':
   addr,beats,index=reads[row['id']];data=b''.join(n.to_bytes(4,'little')for n in row['data']);assert row['last']==(index+1==beats)
   for offset,value in enumerate(data):
    a=addr+index*16+offset
    if a in mem:assert mem[a]==value,('External memory data changed without write',a);known+=1
    else:unknown+=1
    mem[a]=value
   reads[row['id']][2]+=1
   if index+1==beats:del reads[row['id']]
  elif event=='AW':
   assert row['addr']+16*row['beats']<=0x1200040000;writes.append([row['addr'],row['beats'],0])
  elif event=='W':
   addr,beats,index=writes[0];data=b''.join(n.to_bytes(4,'little')for n in row['data']);assert row['last']==(index+1==beats)
   for offset,value in enumerate(data):
    if row['strb']>>offset&1:mem[addr+16*index+offset]=value;committed+=1
   writes[0][2]+=1
   if index+1==beats:writes.pop(0)
  elif event=='program_end':assert not reads and not writes;active=None
 assert active is None and known>0 and committed>0
 return dict(passed=True,repeated_or_postwrite_read_bytes_checked=known,first_external_input_bytes_observed=unknown,write_bytes_committed=committed,memory_reset_per_program_to_allow_host_input_preparation=True)
for mode,seed in [(1,162),(2,162),(2,163)]:
 name='initial-'+str(mode)+'-'+str(seed);raw=folder/(name+'.jsonl');value=json.loads((folder/(name+'.json')).read_text());assert value==old['initial_results'][name+'.json'];rows=[json.loads(line)for line in raw.read_text().splitlines()];a=audit(raw,value['cycles']);m=memory_replay(rows);assert a['passed'];results[name]=dict(result=value,trace_sha256=sha(raw),trace_bytes=raw.stat().st_size,event_count=len(rows),protocol=a,memory=m)
 if mode==1:
  cases=[]
  def corrupt(kind,change):
   rows=[json.loads(line)for line in raw.read_text().splitlines()];change(rows);p=out/('negative-'+kind+'.jsonl');p.write_text(''.join(json.dumps(v)+'\n'for v in rows))
   try:audit(p,value['cycles'])
   except AssertionError:negative.append(dict(kind=kind,path=str(p),sha256=sha(p),rejected=True))
   else:raise AssertionError('Auditor accepted '+kind)
  corrupt('missing-first-AR',lambda rows:rows.pop(next(i for i,r in enumerate(rows)if r['event']=='AR')))
  corrupt('wrong-read-tail',lambda rows:next(r for r in rows if r['event']=='R').update(last=1-next(r for r in rows if r['event']=='R')['last']))
  corrupt('descriptor-index',lambda rows:next(r for r in rows if r['event']=='descriptor').update(index=999))
  corrupt('missing-final-completion',lambda rows:rows.pop())
  corrupt('time-reversal',lambda rows:rows[0].update(cycle=-2))
  # A valid-shaped trace with one repeated read value corrupted must fail
  # the independent external-memory model, even when protocol framing passes.
  changed=False;mem={};reads={};writes=[]
  for i,row in enumerate(rows):
   if row['event']=='program_begin':mem={};reads={};writes=[]
   elif row['event']=='AR':reads[row['id']]=[row['addr'],0]
   elif row['event']=='R':
    addr,index=reads[row['id']];key=addr+16*index
    if key in mem:
     damaged=[dict(r)for r in rows];damaged[i]=dict(row,data=list(row['data']));damaged[i]['data'][0]^=1;p=out/'negative-read-data.jsonl';p.write_text(''.join(json.dumps(v)+'\n'for v in damaged));assert audit(p,value['cycles'])['passed']
     try:memory_replay(damaged)
     except AssertionError:negative.append(dict(kind='read-data',path=str(p),sha256=sha(p),rejected=True));changed=True
     else:raise AssertionError('Memory auditor accepted wrong repeated data')
     break
    mem[key]=True;reads[row['id']][1]+=1
    if row['last']:del reads[row['id']]
   elif row['event']=='AW':writes.append([row['addr'],0])
   elif row['event']=='W':
    addr,index=writes[0];mem[addr+16*index]=True;writes[0][1]+=1
    if row['last']:writes.pop(0)
  assert changed
assert len(negative)==6
result=dict(passed=True,admission=admission,time=time.time(),stage='actual-event-protocol-and-memory-audit-only',whole_system_qualified=False,inputs=bindings,results=results,rejected_controls=negative,marker_semantics=dict(program_started='Host start AXI-Lite configuration write has returned; not an internal first-instruction timestamp',program_end='Actual ended/fault/busy ports observed after mandatory transaction drain; not the exact status transition edge',descriptor='Host supplied descriptor words',planned_order='Host program descriptor plan; not captured internal dispatch',AR_R_AW_W_B='Actual ready/valid top-level handshakes at pre-rising sampling'),scope='Three actual complete current345instance final-cell executions, unchanged original checks/cycles/results, observed external handshake protocol and read/write payload consistency, plus six actual corrupted complete trace rejection controls. Eight numerical cases and six error cases; no internal dispatch or per-cycle waveform and no upper geometry/PG/RC300MHz qualification.')
(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,events={k:v['event_count']for k,v in results.items()},memory={k:v['memory']for k,v in results.items()},rejected=len(negative),cases=len(next(iter(results.values()))['protocol']['actual_cases']),program_invocations=len(next(iter(results.values()))['protocol']['programs']))))
