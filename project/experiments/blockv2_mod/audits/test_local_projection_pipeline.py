import unittest,json,struct,zlib
from pathlib import Path
from macro_service_runner import Runner
from macro_projection_service import LocalProjection
from macro_memory import MacroSram,Data
from tlm_sram_profile import Sram
from native_tlm_timing import Clock
from projection_local_descriptor import encode
import macro_projection_model as pm
class TestPipeline(unittest.TestCase):
 def test_cross_k_prefetch_numeric_and_lifetimes(self):
  plan=json.loads(Path('evidence/joint-frontier/with-workspace/decode/plan.json').read_text())
  original=next(bytes.fromhex(c['descriptor_hex']) for c in plan['calls'] if bytes.fromhex(c['descriptor_hex'])[:4]==b'MPR1')
  for k in (256,384,1024):
   raw=bytearray(original);struct.pack_into('<I',raw,0,0x02505001);struct.pack_into('<I',raw,8,0x02504d02)
   raw[112:124]=bytes(12)
   struct.pack_into('<IIHBBHHHBB',raw,64,16,0,8,2,0,k,0,k,1,0)
   struct.pack_into('<6HQQ',raw,84,880,0,0,0,0,0,0,0)
   struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
   record=encode(bytes(raw),source_address=0x10000,source_word=832)
   weight_base=struct.unpack_from('<Q',raw,48)[0]
   clock=Clock();sram=MacroSram(clock,core_ps=1000,profile=Sram('test',16384,128,128))
   values=[(1+i%7)*(8192 if (i//128)%2 else 1) for i in range(k)]
   activation=struct.pack('<'+'i'*k,*values)
   weights=bytes([1])*1024+struct.pack('<8H',*([0x3c00]*8))+bytes(48)
   def memory(address):
    if 0x10000<=address<0x10000+k*4:return Data.of(activation[address-0x10000:address-0x10000+64])
    return Data.of(weights[(address-weight_base)%1088:(address-weight_base)%1088+64])
   issued=[];groups=[];done=[];pending=[0]
   class Dram:
    def submit(self,t,callback,channel=None):
     issued.append((t.address,clock.now));pending[0]+=1
     def returned():pending[0]-=1;callback()
     clock.after(19000+(t.address//64%5)*3000,returned)
   dram=Dram();runner=Runner(clock,sram,dram,dram,memory,core_ps=1000)
   local=LocalProjection(runner,dram)
   old=pm.accumulate
   def observed(w,a,shift,prefix,head):
    groups.append((clock.now,list(a)));return old(w,a,shift,prefix,head)
   pm.accumulate=observed
   try:
    local.provider(record)(lambda:done.append(clock.now));clock.until(lambda:bool(done))
   finally:pm.accumulate=old
   actual=Data.join(sram.words[i] for i in range(4)).i32()
   self.assertEqual(actual,[sum(values)]*16)
   self.assertEqual(pending[0],0);self.assertFalse(runner.busy);self.assertFalse(local.model.busy)
   self.assertEqual(len(groups),2*(k//128))
   self.assertEqual(runner.stats['quantize_read_words'],32*(k//128))
   self.assertEqual(runner.stats['quantize_write_words'],16*(k//128))
   self.assertLessEqual(runner.stats['quantize_response_peak'],2)
   self.assertLessEqual(runner.stats['quantize_pack_peak'],2)
   for tile in range(k//128):
    expected=values[tile*128:(tile+1)*128]
    shift=next(n for n in range(18) if max(abs(v) for v in expected)<=32767<<n)
    expected=[v>>shift for v in expected]
    for _,consumed in groups[2*tile:2*tile+2]:self.assertEqual(consumed,expected)
    if tile+1<k//128:
     next_load=min(t for a,t in issued if a==0x10000+(tile+1)*512)
     self.assertLess(next_load,groups[2*tile+1][0])
if __name__=='__main__':unittest.main()
