import unittest,heapq,itertools,json,struct
from macro_memory import Data
from macro_scalar_services import dma,gather
from indexed_gather_descriptor import encode as gather_encode
from collections import Counter
from macro_activation_pipeline import ActivationLoad
from macro_service_runner import Runner
from macro_memory_transport import SharedMemory
from macro_memory import MacroSram
from tlm_sram_profile import Sram
from native_tlm_timing import Transfer
class Clock:
 def __init__(self):self.now=0;self.q=[];self.ids=itertools.count()
 def after(self,n,fn):heapq.heappush(self.q,(self.now+n,next(self.ids),fn))
 def drain(self):
  steps=0
  while self.q:
   self.now,_,fn=heapq.heappop(self.q);fn();steps+=1
   if steps>100000:raise AssertionError('timeout')
class Backend:
 def __init__(self,c):self.c=c;self.times=[];self.active=0;self.peak=0
 def submit(self,t,done,channel=None):
  self.times.append((self.c.now,channel));self.active+=1;self.peak=max(self.peak,self.active)
  def finish():self.active-=1;done()
  self.c.after(2000+(31-(t.address//64)%32)*7,finish)
 def close(self):assert self.active==0
class Tests(unittest.TestCase):
 def test_real_shared_transport_with_activation_and_weight_pressure(self):
  with open('hardware/blockv2-mod-shared-memory.json') as f:contract=json.load(f)['base_rtl_contract']
  contract={**contract,'read_slots_per_owner':4,'write_slots_per_owner':1}
  c=Clock();b=Backend(c);transport=SharedMemory(c,b,contract,core_ps=1);finished=[];runners=[];srams=[];observations=[[] for _ in range(9)]
  for i in range(32):transport.client(9).submit(Transfer(0x80000+64*i),lambda:None,channel=0)
  memory=lambda address:bytes([address//64%256])*64
  for owner in range(9):
   s=MacroSram(c,core_ps=1,profile=Sram(str(owner),16384,128,128));srams.append(s)
   r=Runner(c,s,transport.client(12+owner),None,memory,core_ps=1);runners.append(r)
   ActivationLoad(r).start(0x10000+owner*4096,32,512,lambda o=owner:finished.append(o),observe=lambda data,o=owner:observations[o].append(data.require()))
  c.drain()
  self.assertEqual(sorted(finished),list(range(9)));self.assertTrue(transport.drained());transport.close()
  self.assertEqual(transport.stats['read_beats'],104);self.assertEqual(transport.stats['peak_channel_entries'],32)
  for owner,(s,r) in enumerate(zip(srams,runners)):
   self.assertEqual(r.stats['activation_slots_peak'],2);self.assertEqual(r.stats['activation_writes_peak'],2)
   self.assertEqual(r.stats['activation_read_beats'],8);self.assertEqual(r.stats['activation_write_words'],32)
   self.assertEqual(observations[owner],[memory(0x10000+owner*4096+(word//4)*64)[:16] for word in range(32)])
   for word in range(32):self.assertEqual(s.words[32+word].require(),memory(0x10000+owner*4096+(word//4)*64)[:16])
  per=Counter(t for t,ch in b.times if ch==0)
  self.assertLessEqual(max(per.values()),2)
  for t in per:self.assertLessEqual(sum(per.get(k,0) for k in range(t-2,t+1)),4)
  print('PASS production SharedMemory + ActivationLoad: 104 reads, 32 channel slots, 2 read/2 write activation, rolling 4/3 issue bound')

 def test_production_runner_dma_and_gather(self):
  with open('hardware/blockv2-mod-shared-memory.json') as f:contract=json.load(f)['base_rtl_contract']
  contract={**contract,'read_slots_per_owner':4,'write_slots_per_owner':1}
  for kind,size,offset,index in [('dma',512,0,0),('gather',16384,0,-1),('gather',512,64,1)]:
   with self.subTest(kind=kind,size=size):
    c=Clock();b=Backend(c);transport=SharedMemory(c,b,contract,core_ps=1);done=[];addresses=[]
    source=0x8000+offset
    def memory(address):
     addresses.append(address)
     if address==0x800:return Data.of(struct.pack('<i',index)+bytes(60))
     return Data.of(bytes([address//64%256])*64)
    sram=MacroSram(c,core_ps=1,profile=Sram('test',16384,128,128))
    runner=Runner(c,sram,transport.client(12),None,memory,core_ps=1)
    if kind=='dma':
     raw=bytearray(128);struct.pack_into('<H',raw,16,0);struct.pack_into('<Q',raw,24,source);gen=dma(bytes(raw))
    else:
     raw=gather_encode(topology=1,table_address=0x4000,index_address=0x800,rows=2,
      row_shift=14,index_bytes=4,offset=offset,byte_count=size,sram_word=0);gen=gather(raw)
    runner.execute(gen,lambda:done.append(True));c.drain()
    self.assertEqual(done,[True]);self.assertFalse(runner.busy);self.assertTrue(transport.drained());transport.close()
    expected=[source+i*64 for i in range(size//64)]
    self.assertEqual(sorted(a for a in addresses if a!=0x800),expected)
    self.assertEqual(addresses.count(0x800),int(kind=='gather'))
    self.assertEqual(runner.stats['load_pipeline'],1)
    self.assertEqual(runner.stats['read'],int(kind=='gather'))
    self.assertEqual(runner.stats['swrite'],0)
    self.assertEqual(runner.stats['activation_read_beats'],size//64)
    self.assertEqual(runner.stats['activation_write_words'],size//16)
    self.assertEqual(runner.stats['activation_slots_peak'],2);self.assertEqual(runner.stats['activation_writes_peak'],2)
    for word in range(size//16):self.assertEqual(sram.words[word].require(),bytes([(source+word//4*64)//64%256])*16)
  print('PASS production Runner dma/gather: exact extents, negative index, 16KiB and 512B payloads, pipeline 2/2')
if __name__=='__main__':unittest.main()

