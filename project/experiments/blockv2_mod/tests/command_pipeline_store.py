import unittest
from command_pipeline_activation import Clock
from macro_service_runner import Runner,store_span
from macro_memory import Data
class SRAM:
 def __init__(self,c,raw):self.c=c;self.raw=raw;self.active=0;self.peak=0;self.reads=0
 def access(self,w,done):
  self.active+=1;self.peak=max(self.peak,self.active);self.reads+=1
  def response():self.active-=1;done(Data.of(self.raw[w*16:w*16+16]))
  self.c.after(7,response)
class Memory:
 def __init__(self):self.data={}
 def begin_write(self,a,t,p):return lambda:self.data.update({a:p.require()})
class Write:
 def __init__(self,c,s):self.c=c;self.s=s;self.active=0;self.peak=0;self.first_ack_reads=0;self.acks=0;self.last=0
 def submit(self,t,done):
  self.active+=1;self.peak=max(self.peak,self.active)
  def ack():
   self.active-=1;self.acks+=1;self.last=self.c.now
   if self.acks==1:self.first_ack_reads=self.s.reads
   done()
  self.c.after(60,ack)
class Store(unittest.TestCase):
 def test_production_runner(self):
  for n in (1,2,8,128):
   c=Clock();raw=bytes(i%251 for i in range(n*64));s=SRAM(c,raw);m=Memory();w=Write(c,s);r=Runner(c,s,None,w,m,core_ps=1);done=[]
   r.execute(store_span(0,4096,n*64,77),lambda:done.append(c.now));c.drain()
   self.assertEqual(b''.join(m.data[4096+i*64] for i in range(n)),raw)
   self.assertEqual((s.active,w.active),(0,0));self.assertEqual((s.peak,w.peak),(2,1))
   self.assertEqual(len(done),1);self.assertGreater(done[0],w.last);self.assertFalse(r.busy)
   self.assertEqual(r.stats['store_read_words'],n*4);self.assertEqual(r.stats['store_write_beats'],n)
   self.assertLessEqual(r.stats['store_slots_peak'],2)
   if n>1:self.assertEqual(w.first_ack_reads,8)
if __name__=='__main__':unittest.main()
