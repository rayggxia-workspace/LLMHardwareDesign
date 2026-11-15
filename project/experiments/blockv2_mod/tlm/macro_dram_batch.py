"""Batch real DRAM ticks without crossing a Python event or a DRAM return."""
import ctypes as c
from native_tlm_timing import Dram
class BatchDram(Dram):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  self.lib.native_dram_pair_ticks.restype=c.c_uint64
  self.lib.native_dram_pair_ticks.argtypes=[c.c_void_p,c.c_void_p,c.c_uint64]
  self.lib.native_dram_flush.restype=None;self.lib.native_dram_flush.argtypes=[c.c_void_p]
 def tick(self):
  # Keep the ordinary offer/tick ordering at the current event time.
  for channel,model in enumerate(self.models):
   queue=self.queue[channel]
   if queue and self.active[channel]<self.credits:
    transfer,done=queue[0];write=transfer.payload is not None
    if self.lib.native_dram_offer(model,transfer.address,write):
     queue.popleft();self.pending[channel,transfer.address,write].append(done)
     self.active[channel]+=1;self.stats['writes' if write else 'reads']+=1
    else:self.stats['dram_backpressure_ticks']+=1
   self.lib.native_dram_tick(model)
  if self.failure:raise self.failure
  self.stats['python_tick_calls']+=1
  # No queued transaction may skip its next ordinary offer opportunity.
  if not any(self.queue):
   deadline=self.clock.events[0][0] if self.clock.events else self.clock.now+630*4097
   limit=min(4096,max(0,(deadline-self.clock.now-1)//630))
   if limit:
    ticks=self.lib.native_dram_pair_ticks(*self.models,limit)
    self.clock.now+=630*ticks;self.stats['batched_ticks']+=ticks
    # Python callbacks now see their exact original DRAM cycle timestamp.
    for model in self.models:self.lib.native_dram_flush(model)
    if self.failure:raise self.failure
  self.clock.after(630,self.tick)
