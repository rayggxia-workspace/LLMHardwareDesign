"""Observed-shift K128 conversion: two response owners and two 16-byte packs."""
import struct
from macro_memory import Data
from macro_numeric import rne
class Quantize:
 def __init__(self,runner):self.runner=runner;self.busy=False
 def start(self,source_word,target_word,shift,done):
  if self.busy or not 0<=shift<=17:raise ValueError('quantizer busy/shift')
  if source_word<target_word+16 and target_word<source_word+32:raise ValueError('quantizer overlap')
  self.busy=True;r=self.runner
  slots={};read=write=acked=pending=0;scheduled=False;output=[None]*16
  def schedule():
   nonlocal scheduled
   if not scheduled:
    scheduled=True;r.edge(issue)
  def issue():
   nonlocal scheduled,read,write,pending
   scheduled=False
   if acked==16:
    if pending or slots:raise ValueError('quantizer completion before drain')
    self.busy=False;done(b''.join(output),shift);return
   if pending==2:return
   slot=slots.get(write%2)
   if write<16 and slot is not None and slot['index']==write and len(slot['parts'])==2 and not slot['writing']:
    index=write;write+=1;slot['writing']=True
    payload=slot['parts'][0]+slot['parts'][1];output[index]=payload;pending+=1
    r.stats['quantize_write_words']+=1
    def committed(_):
     nonlocal acked,pending
     pending-=1;acked+=1;del slots[index%2];schedule()
    r.sram.access(target_word+index,committed,Data.of(payload))
   elif read<32 and (read%2 or (read//2)%2 not in slots):
    index=read;read+=1;pending+=1;pack=index//2
    if index%2==0:slots[pack%2]={'index':pack,'parts':{},'writing':False}
    r.stats['quantize_read_words']+=1
    def returned(data):
     nonlocal pending
     pending-=1
     values=[rne(v,shift) for v in data.i32()]
     if any(v < -32768 or v>32767 for v in values):raise ValueError('quantizer overflow')
     slots[pack%2]['parts'][index%2]=struct.pack('<4h',*values);schedule()
    r.sram.access(source_word+index,returned)
   else:return
   r.stats['quantize_response_peak']=max(r.stats['quantize_response_peak'],pending)
   r.stats['quantize_pack_peak']=max(r.stats['quantize_pack_peak'],len(slots))
   schedule()
  schedule()
