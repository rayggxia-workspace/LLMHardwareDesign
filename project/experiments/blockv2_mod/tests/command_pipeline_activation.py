"""Exercise the production ActivationLoad with reordered DDR and delayed ACKs."""
import heapq,itertools,unittest
from collections import Counter
from macro_service_runner import Runner
from macro_activation_pipeline import ActivationLoad
class Clock:
 def __init__(self):self.now=0;self.q=[];self.ids=itertools.count()
 def after(self,n,fn):heapq.heappush(self.q,(self.now+n,next(self.ids),fn))
 def drain(self):
  count=0
  while self.q:
   self.now,_,fn=heapq.heappop(self.q);fn();count+=1
   if count>100000:raise AssertionError('scheduler did not drain')
class Read:
 def __init__(self,c):self.c=c;self.active=0;self.peak=0;self.returns=[];self.issues=[]
 def submit(self,transfer,done):
  # First of each pair returns after its successor.
  i=len(self.issues);self.issues.append((self.c.now,transfer))
  self.active+=1;self.peak=max(self.peak,self.active)
  def returned():self.active-=1;self.returns.append(i);done()
  self.c.after(31 if i%2==0 else 2,returned)
class Sram:
 def __init__(self,c,latency):self.c=c;self.latency=latency;self.active=0;self.peak=0;self.words={};self.issues=[];self.last_ack=0
 def access(self,w,done,payload):
  self.active+=1;self.peak=max(self.peak,self.active);self.issues.append((self.c.now,w))
  def ack():
   self.active-=1;self.words[w]=payload.require();self.last_ack=self.c.now;done(None)
  self.c.after(self.latency,ack)
class Tests(unittest.TestCase):
 def run_case(self,bursts,delay):
  c=Clock();read=Read(c);sram=Sram(c,delay)
  raw=bytes((i*7)%256 for i in range(bursts*64))
  memory=lambda a:raw[a-4096:a-4096+64]
  r=Runner(c,sram,read,None,memory,core_ps=1);loader=ActivationLoad(r);done=[]
  loader.start(4096,20,len(raw),lambda:done.append((c.now,sram.active,read.active)))
  with self.assertRaises(ValueError):loader.start(4096,20,64,lambda:None)
  c.drain()
  self.assertEqual(len(done),1);self.assertEqual(done[0][1:],(0,0))
  self.assertGreater(done[0][0],sram.last_ack);self.assertFalse(loader.busy)
  self.assertEqual(b''.join(sram.words[w] for w in range(20,20+bursts*4)),raw)
  self.assertLessEqual(read.peak,2);self.assertEqual(sram.peak,2)
  self.assertEqual(r.stats['activation_read_beats'],bursts)
  self.assertEqual(r.stats['activation_write_words'],bursts*4)
  self.assertLessEqual(r.stats['activation_slots_peak'],2)
  self.assertEqual([w for _,w in sram.issues],list(range(20,20+bursts*4)))
  if bursts>1:self.assertEqual(read.returns[:2],[1,0])
 def test_single_burst(self):
  for delay in (2,7,31):self.run_case(1,delay)
 def test_reordered_multiple_bursts(self):
  for bursts in (2,3,8,17):
   for delay in (2,7,31):self.run_case(bursts,delay)
 def test_invalid_extent(self):
  r=Runner(Clock(),None,None,None,None,core_ps=1)
  for address,size in [(1,64),(0,0),(0,63)]:
   with self.assertRaises(ValueError):ActivationLoad(r).start(address,0,size,lambda:None)
if __name__=='__main__':unittest.main()
