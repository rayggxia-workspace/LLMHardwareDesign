import heapq,itertools,unittest,json,hashlib,os
from pathlib import Path
observed=[]
from macro_projection_model import Projection
class Clock:
 def __init__(self):self.now=0;self.q=[];self.ids=itertools.count()
 def after(self,n,f):heapq.heappush(self.q,(self.now+n,next(self.ids),f))
 def drain(self):
  while self.q:self.now,_,f=heapq.heappop(self.q);f()
class Dram:
 def __init__(self,c):self.c=c;self.active=0;self.peak=0;self.issues=[];self.returns=[]
 def submit(self,t,done,channel=None):
  self.active+=1;self.peak=max(self.peak,self.active);self.issues.append(self.c.now)
  delay=100+(31-(t.address//64)%32)*3
  def reply():
   self.active-=1;self.returns.append(t.address);done()
  self.c.after(delay,reply)
class Sram:core_ps=1
class Tests(unittest.TestCase):
 def test_a_source_two_credits_ordered_assembly(self):
  c=Clock()
  class Reads:
   core_ps=1
   active=peak=0
   issues=[]
   def access(self,word,done):
    self.active+=1;self.peak=max(self.peak,self.active);self.issues.append(c.now)
    def reply():
     self.active-=1;done(bytes([word])*16)
    c.after(12 if word%2==0 else 4,reply)
  ram=Reads();p=Projection(c,Dram(c),lambda _:bytes(64),ram,ram,source_word=0,scratch_word=32)
  result=[];p.read_span(ram,0,16,result.append);c.drain()
  self.assertEqual(result,[b''.join(bytes([i])*16 for i in range(16))])
  self.assertEqual(ram.peak,2);self.assertEqual(ram.active,0)
  self.assertTrue(all(b-a>=2 for a,b in zip(ram.issues,ram.issues[1:])))

 def test_four_records_32_credits_out_of_order_and_drain(self):
  c=Clock();d=Dram(c);memory=lambda a:bytes([a//64%256])*64
  p=Projection(c,d,memory,Sram(),Sram(),source_word=0,scratch_word=32)
  completed={}
  for i in range(4):
   base=i*4096
   p.fetch(base,1152,lambda raw,i=i:completed.setdefault(i,raw))
  c.drain()
  observed.append({"peak_outstanding":d.peak,"returned":p.stats["weight_read_returns"],"pending_at_end":p.fetch_pending,"source":"test DDR callbacks"})
  self.assertEqual(d.peak,32);self.assertEqual(p.fetch_pending,0);self.assertFalse(p.fetch_queue)
  self.assertEqual(len(completed),4);self.assertEqual(p.stats['weight_read_returns'],72)
  self.assertNotEqual(d.returns,sorted(d.returns))
  self.assertTrue(all(b-a>=1 for a,b in zip(d.issues,d.issues[1:])))
  for i,raw in completed.items():self.assertEqual(raw,b''.join(memory(i*4096+j*64) for j in range(18)))
 def test_ordinary_record_not_padded_to_head16(self):
  c=Clock();d=Dram(c);p=Projection(c,d,lambda a:bytes(64),Sram(),Sram(),source_word=0,scratch_word=32)
  result=[];p.fetch(0,1088,result.append);c.drain()
  self.assertEqual(len(result[0]),1088);self.assertEqual(len(d.issues),17)
if __name__=='__main__':
 suite=unittest.main(exit=False)
 base=Path('/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/rtl/w8a16_v1')
 sources=[base/n for n in ['m_native_leaf_s32.sv','m_native_s32.sv','weight_records.sv']]
 sources += [Path('tlm/macro_projection_model.py'),Path(__file__)]
 receipt={'passed':suite.result.wasSuccessful(),'observed':observed,'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
 'scope':'TLM bounded-request and reassembly tests; RTL source contract trace, not RTL execution equivalence'}
 out=Path('evidence/command-pipeline')/('weight-'+os.environ.get('SLURM_JOB_ID','manual')+'.json')
 out.write_text(json.dumps(receipt,indent=2)+'\n')
 raise SystemExit(0 if receipt['passed'] else 1)
