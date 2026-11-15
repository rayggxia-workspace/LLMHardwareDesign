"""Two resident 64B gather slots, two ordered SRAM reads, one DDR write."""
from macro_memory import Data
from native_tlm_timing import Transfer
class StorePipeline:
 def __init__(self,runner):self.runner=runner;self.busy=False
 def start(self,word,address,size,tag,done):
  if self.busy or size<=0 or size%64 or address%64 or word<0 or word+size//16>1024:raise ValueError('store extent/busy')
  self.busy=True;r=self.runner;n=size//64;tag=address//64 if tag is None else tag
  if tag<0 or tag+n>1<<64:raise ValueError('store tag overflow')
  parts={};issued=received=retired=0;writing=False;scheduled=False
  def schedule():
   nonlocal scheduled
   if not scheduled and issued<n*4 and issued<(retired+2)*4 and issued-received<2:
    scheduled=True;r.edge(issue)
  def issue():
   nonlocal issued,scheduled
   scheduled=False
   if issued==n*4 or issued==(retired+2)*4 or issued-received==2:return
   index=issued;issued+=1
   r.stats['store_read_words']+=1
   r.stats['store_reads_peak']=max(r.stats['store_reads_peak'],issued-received)
   r.stats['store_slots_peak']=max(r.stats['store_slots_peak'],(issued+3)//4-retired)
   def response(data):
    nonlocal received
    if index!=received:raise ValueError('unordered untagged SRAM response')
    parts[index]=Data.of(data);received+=1;send();schedule()
   r.sram.access(word+index,response);schedule()
  def send():
   nonlocal writing
   if writing or received<(retired+1)*4:return
   writing=True;index=retired
   payload=Data.join([parts.pop(index*4+i) for i in range(4)])
   transfer=Transfer(address+index*64,payload.payload);transfer.tag=tag+index
   commit=r.memory.begin_write(address+index*64,tag+index,payload)
   def ack():
    nonlocal writing,retired
    commit();writing=False;retired+=1;r.stats['store_write_beats']+=1
    if retired==n:
     if issued!=received or parts:raise ValueError('store completion before drain')
     self.busy=False;r.edge(done);return
    schedule();r.edge(send)
   # Hardware request is stable through shared write adapter backpressure.
   r.edge(lambda:r.write.submit(transfer,ack))
  schedule()
