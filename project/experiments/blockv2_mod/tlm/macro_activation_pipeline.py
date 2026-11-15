"""Two DDR return slots, ordered SRAM commit, two outstanding 128-bit writes."""
from macro_memory import Data
from native_tlm_timing import Transfer
class ActivationLoad:
 def __init__(self,runner):self.runner=runner;self.busy=False
 def start(self,address,word,size,done,*,observe=None):
  if self.busy or size<=0 or size%64 or address%64:raise ValueError('activation load extent/busy')
  self.busy=True;r=self.runner;n=size//64
  slots={};issued=retired=sent=acked=0;read_scheduled=write_scheduled=False
  def read_schedule():
   nonlocal read_scheduled
   if not read_scheduled and issued<n and len(slots)<2:
    read_scheduled=True;r.edge(read_issue)
  def write_schedule():
   nonlocal write_scheduled
   if not write_scheduled and slots.get(retired) is not None and sent<4 and sent-acked<2:
    write_scheduled=True;r.edge(write_issue)
  def read_issue():
   nonlocal issued,read_scheduled
   read_scheduled=False
   if issued==n or len(slots)==2:return
   index=issued;issued+=1;slots[index]=None
   r.stats['activation_read_beats']+=1
   r.stats['activation_slots_peak']=max(r.stats['activation_slots_peak'],len(slots))
   def returned():
    if index not in slots or slots[index] is not None:raise ValueError('duplicate activation return')
    slots[index]=Data.of(r.memory(address+index*64));write_schedule()
   r.read.submit(Transfer(address+index*64),returned)
   read_schedule()
  def write_issue():
   nonlocal sent,write_scheduled
   write_scheduled=False
   if slots.get(retired) is None or sent==4 or sent-acked==2:return
   index=sent;sent+=1
   r.stats['activation_write_words']+=1
   r.stats['activation_writes_peak']=max(r.stats['activation_writes_peak'],sent-acked)
   payload=slots[retired].slice(index*16,16)
   if observe is not None:observe(payload)
   r.sram.access(word+retired*4+index,write_ack,payload)
   write_schedule()
  def write_ack(_):
   nonlocal acked,retired,sent
   acked+=1
   if acked==4:
    del slots[retired];retired+=1;sent=acked=0
    if retired==n:
     if slots or issued!=n:raise ValueError('activation completion before drain')
     self.busy=False;r.edge(done);return
    read_schedule()
   write_schedule()
  read_schedule()
