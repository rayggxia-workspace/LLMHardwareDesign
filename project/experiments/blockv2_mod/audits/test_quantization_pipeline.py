import struct,unittest
from collections import Counter
from macro_quantization_pipeline import Quantize
from macro_memory import Data
from macro_numeric import rne
from native_tlm_timing import Clock
class TestQuantize(unittest.TestCase):
 def test_two_slots_and_exact_values(self):
  for shift in (0,1,8,17):
   clock=Clock();words={}
   values=[((i*331)%60000-30000)*(1<<shift) for i in range(128)]
   # Keep signed32 input legal at large shifts, including negative ties.
   values=[max(-(1<<31),min((1<<31)-1,v)) for v in values]
   for i in range(32):words[832+i]=Data.of(struct.pack('<4i',*values[4*i:4*i+4]))
   ops=[];pending=[0];peak=[0];commits=[]
   class Sram:
    def access(self,word,done,payload=None):
     ops.append((clock.now,word,payload is not None));pending[0]+=1;peak[0]=max(peak[0],pending[0])
     def returned():
      pending[0]-=1
      if payload is not None:words[word]=payload;commits.append(clock.now)
      done(words[word])
     clock.after(7000+(word%3)*1000,returned)
   class Runner:
    core_ps=1000;stats=Counter();sram=Sram()
    def edge(self,fn):clock.after(1000-clock.now%1000,fn)
   runner=Runner();quant=Quantize(runner);done=[]
   quant.start(832,880,shift,lambda data,s:done.append((data,s,clock.now)))
   clock.until(lambda:bool(done))
   expected=struct.pack('<128h',*(rne(v,shift) for v in values))
   self.assertEqual(done[0][:2],(expected,shift));self.assertEqual(Data.join(words[880+i] for i in range(16)).require(),expected)
   self.assertEqual(sum(not wr for _,_,wr in ops),32);self.assertEqual(sum(wr for _,_,wr in ops),16)
   self.assertEqual(peak[0],2);self.assertLessEqual(runner.stats['quantize_pack_peak'],2)
   self.assertGreaterEqual(done[0][2],max(commits));self.assertEqual(pending[0],0)
   self.assertLess(next(t for t,_,wr in ops if wr),max(t for t,_,wr in ops if not wr))
if __name__=='__main__':unittest.main()
