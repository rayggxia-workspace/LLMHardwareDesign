"""MPR1 local S32 DDR -> selected S_P -> A16 -> actual M projection service model."""
import struct,zlib
from macro_memory import Data
from macro_quantization_pipeline import Quantize
from macro_activation_pipeline import ActivationLoad
from macro_projection_model import Projection
from projection_local_descriptor import encode

class CheckedSram:
 def __init__(self,sram):self.sram=sram;self.core_ps=sram.core_ps
 def access(self,word,done,payload=None):
  self.sram.access(word,lambda data:done(data.require()),None if payload is None else Data.of(payload))

class LocalProjection:
 def __init__(self,runner,weight_client):
  self.runner=runner;self.memory=runner.memory
  sram=CheckedSram(runner.sram)
  self.model=Projection(runner.clock,weight_client,lambda address:runner.memory(address).require(),
   sram,sram,source_word=832,scratch_word=880)
 def provider(self,record):
  source,word,reserved=struct.unpack_from('<QHH',record,112)
  raw=bytearray(record);struct.pack_into('<I',raw,0,0x02505001)
  struct.pack_into('<I',raw,8,0x02504d02);raw[112:124]=bytes(12)
  struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
  if reserved or encode(bytes(raw),source_address=source,source_word=word)!=record:
   raise ValueError('MPR1 local source descriptor mismatch')
  runner=self.runner
  tiles=struct.unpack_from('<H',record,76)[0]//128
  target_word=struct.unpack_from('<H',record,84)[0]
  class PackedTiles:
   ready_in_sram=True
   def __init__(self):
    self.loader=ActivationLoad(runner);self.loading=None;self.ready=None;self.waiter=None;self.next_tile=0
   def prefetch(self,tile):
    if tile==tiles:return
    if tile!=self.next_tile or self.loading is not None or self.ready is not None:
     raise ValueError('activation prefetch ownership/order')
    self.loading=tile
    peak=0;observed=0
    def observe(payload):
     nonlocal peak,observed
     peak=max(peak,max(abs(v) for v in payload.i32()));observed+=1
    def loaded():
     if observed!=32:raise ValueError('activation statistics extent')
     self.ready_shift=next(s for s in range(18) if peak<=32767<<s)
     self.loading=None;self.ready=tile
     if self.waiter is not None:self.consume()
    self.loader.start(source+tile*512,word,512,loaded,observe=observe)
   def __call__(self,tile,done):
    if self.waiter is not None or tile!=self.next_tile:raise ValueError('activation consumer order')
    self.waiter=done
    if self.ready==tile:self.consume()
    elif self.loading is None:self.prefetch(tile)
    elif self.loading!=tile:raise ValueError('activation window identity')
   def consume(self):
    tile=self.ready
    if tile!=self.next_tile:raise ValueError('activation uncommitted window')
    self.ready=None;callback=self.waiter;self.waiter=None
    def prepared(payload,shift):
     self.next_tile+=1;callback(payload,shift)
    Quantize(runner).start(word,target_word,self.ready_shift,prepared)
  return self.model.provider(bytes(raw),packed_tile=PackedTiles())
