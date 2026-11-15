"""MPR1 local S32 DDR -> selected S_P -> A16 -> actual M projection service model."""
import struct,zlib
from macro_memory import Data
from macro_numeric import rne
from macro_service_runner import load_span,read_words
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
  def packed_tile(tile,done):
   result=[]
   def prepare():
    yield from load_span(source+tile*512,word,512)
    values=(yield from read_words(word,32)).i32()
    peak=max(abs(v) for v in values)
    shift=next(s for s in range(18) if peak<=32767<<s)
    yield ('cycles',1)
    values=(yield from read_words(word,32)).i32()
    result.append((struct.pack('<128h',*(rne(v,shift) for v in values)),shift))
   self.runner.execute(prepare(),lambda:done(*result[0]))
  return self.model.provider(bytes(raw),packed_tile=packed_tile)
