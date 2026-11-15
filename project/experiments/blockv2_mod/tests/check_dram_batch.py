"""Differential callbacks/timestamps for original and batched real DRAMsim3."""
import sys,json,time,random
from pathlib import Path
from native_tlm_timing import Clock,Dram,Transfer
from macro_dram_batch import BatchDram
oldlib,newlib,config,out=map(Path,sys.argv[1:]);out.mkdir(exist_ok=False)
def run(kind,library,seed,window):
 folder=out/(kind.__name__+'-'+str(seed)+'-'+str(window));folder.mkdir()
 clock=Clock();dram=kind(clock,library,config,folder,credits=32)
 rng=random.Random(seed);events=[];target=600;completed=[0];submitted=[0]
 def issue(index):
  address=0x100000+64*rng.randrange(1024)
  write=index%3==0;channel=index%2
  events.append(('issue',index,clock.now,address,write,channel));submitted[0]+=1
  def done():
   events.append(('return',index,clock.now));completed[0]+=1
   if index+window<target:
    clock.after((500 if index%10==0 else index%7)*3333+(630 if index%5==0 else 0),lambda:issue(index+window))
  dram.submit(Transfer(address,bytes(64) if write else None),done,channel=channel)
 for i in range(window):clock.after((i%5)*630,lambda i=i:issue(i))
 # Force both exact DDR ties and long quiescent intervals.
 for delay in (630,1260,3333,63000,630000,2000000):
  clock.after(delay,lambda delay=delay:events.append(('marker',delay,clock.now)))
 start=time.monotonic();clock.until(lambda:completed[0]==target);elapsed=time.monotonic()-start
 dram.close();return events,dict(dram.stats),elapsed
rows=[]
for seed,window in [(185,1),(260,4),(269,24)]:
 old,os,ot=run(Dram,oldlib,seed,window);new,ns,nt=run(BatchDram,newlib,seed,window)
 if old!=new:
  for i,(a,b) in enumerate(zip(old,new)):
   if a!=b:raise AssertionError((seed,i,a,b))
  raise AssertionError('trace length mismatch')
 for key,value in os.items():assert ns[key]==value,(key,os,ns)
 rows.append({'seed':seed,'outstanding_window':window,'trace_events':len(old),'exact_timestamps_and_order':True,
  'ordinary_wall_seconds':ot,'batch_wall_seconds':nt,'stats':ns})
(out/'receipt.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows))
