"""Native CALL/WAIT scheduling through the declared LC descriptor clients."""
from itertools import count
from collections import Counter
from native_tlm_timing import Transfer
class MacroScheduler:
 def __init__(self,clock,transport,memory,*,core_ps):
  self.clock,self.transport,self.memory,self.core_ps=clock,transport,memory,core_ps
  self.serial=count();self.terminals={};self.busy=set();self.active={};self.stats=Counter()
 def submit_local(self,target,slot,addresses,dispatch):
  if target not in range(9) or target in self.busy:
   raise ValueError('unavailable declared local controller')
  if len(addresses)!=2 or addresses[0]%128 or addresses[1]!=addresses[0]+64:
   raise ValueError('LC requires one aligned two-beat descriptor')
  self.busy.add(target);handle=next(self.serial);replies=[]
  self.active[target]={"descriptor_address":addresses[0],"slot":slot,"handle":handle}
  def terminal():
   if target not in self.busy or handle in self.terminals:raise ValueError('duplicate local terminal')
   self.busy.remove(target);del self.active[target];self.terminals[handle]=True;self.stats['completed']+=1
  def received(address):
   replies.append((address,self.memory(address).require()))
   if len(replies)==2:
    self.clock.after(124*self.core_ps,lambda:dispatch(replies)(terminal))
  for address in addresses:
   self.transport.client(target).submit(Transfer(address),lambda address=address:received(address))
  self.stats['issued']+=1
  return handle
 def wait_local(self,handles):
  self.clock.until(lambda:all(handle in self.terminals for handle in handles))
 def local_succeeded(self,handle):return self.terminals.pop(handle)
