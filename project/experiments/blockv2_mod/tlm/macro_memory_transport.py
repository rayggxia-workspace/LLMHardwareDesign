"""Finite shared read/write transport over the PR260 backend callback interface.

The native RTL client table, channels, 64-byte beats and combined rolling issue
limit are explicit. This is a transaction-level model; timing is not calibrated.
"""
from collections import Counter,deque
class Client:
 def __init__(self,parent,identity):self.parent,self.identity=parent,identity
 def submit(self,transfer,done,*,channel=None):
  self.parent.submit(self.identity,transfer,done,channel=channel)
class SharedMemory:
 def __init__(self,clock,backend,contract,*,core_ps):
  if core_ps<=0:raise ValueError('positive native clock required')
  t=contract['transport']
  if (t['channels'],t['lanes_per_channel'],t['beat_bytes'],t['entries_per_channel'],
      t['return_skids_per_channel'],t['issue_limit_per_3_cycles_per_channel'])!=(2,2,64,32,3,4):
   raise ValueError('unsupported declared transport contract')
  if len(contract['memory_clients'])!=30:raise ValueError('complete registered read/write client table required')
  if (contract.get('read_slots_per_owner'),contract.get('write_slots_per_owner'))!=(4,1):
   raise ValueError('current shared native source adapters require four read slots and one write slot')
  self.source_limits=[2]*9+[32]*3+[contract['read_slots_per_owner']]*9+[contract['write_slots_per_owner']]*9
  self.clock,self.backend,self.core_ps=clock,backend,core_ps
  self.queues=[deque() for _ in range(30)];self.pending=[0]*30
  self.channel_active=[0,0];self.returns=[deque(),deque()]
  self.history=[deque(),deque()];self.rr=[0,0];self.stats=Counter()
  self.scheduled=False;self.return_scheduled=False
  self.clients=[Client(self,i) for i in range(30)]
 def client(self,identity):return self.clients[identity]
 def submit(self,client,transfer,done,*,channel=None):
  if not 0<=client<30 or transfer.address%64:raise ValueError('native client/address')
  if transfer.payload is not None and len(transfer.payload)!=64:raise ValueError('64B write payload required')
  if (transfer.payload is not None)!=(client>=21):raise ValueError('read/write client class mismatch')
  # Descriptor requests arrive as two beats; M has at most four open records.
  limit=self.source_limits[client]
  if len(self.queues[client])+self.pending[client]>=limit:
   raise ValueError('provider exceeded its finite native source window')
  channel=(transfer.address>>11)&1 if channel is None else channel
  if channel not in (0,1):raise ValueError('DDR channel')
  self.queues[client].append((channel,transfer,done,self.clock.now))
  self.stats['submitted']+=1;self._schedule()
 def _schedule(self):
  if not self.scheduled:
   self.scheduled=True
   self.clock.after(self.core_ps-self.clock.now%self.core_ps,self._pump)
 def _pump(self):
  self.scheduled=False;cycle=self.clock.now//self.core_ps
  for ch in range(2):
   h=self.history[ch]
   while h and h[0]<cycle-2:h.popleft()
   budget=min(2,4-len(h),32-self.channel_active[ch])
   for _ in range(budget):
    chosen=None
    for step in range(30):
     i=(self.rr[ch]+step)%30
     if self.queues[i] and self.queues[i][0][0]==ch:chosen=i;break
    if chosen is None:break
    _,transfer,done,issued=self.queues[chosen].popleft()
    self.rr[ch]=(chosen+1)%30;self.pending[chosen]+=1;self.channel_active[ch]+=1;h.append(cycle)
    self.stats['queue_wait_ps']+=self.clock.now-issued
    self.stats['write_beats' if chosen>=21 else 'read_beats']+=1
    self.stats['peak_channel_entries']=max(self.stats['peak_channel_entries'],self.channel_active[ch])
    self.backend.submit(transfer,lambda c=chosen,ch=ch,d=done:self._returned(c,ch,d),channel=ch)
  if any(self.queues):self._schedule()
 def _returned(self,client,channel,done):
  # Returned backend tokens remain owned until the bounded native return slots
  # deliver them. No client credit is released at an early backend callback.
  self.returns[channel].append((client,done))
  if len(self.returns[channel])>32:raise ValueError('return ownership exceeded transport entries')
  if not self.return_scheduled:
   self.return_scheduled=True
   self.clock.after(self.core_ps-self.clock.now%self.core_ps,self._deliver)
 def _deliver(self):
  self.return_scheduled=False
  seen=set();first=(self.clock.now//self.core_ps)%2
  for ch in (first,1-first):
   delivered=0
   for _ in range(len(self.returns[ch])):
    client,done=self.returns[ch].popleft()
    if client in seen or delivered==3:
     self.returns[ch].append((client,done));continue
    seen.add(client);delivered+=1
    self.pending[client]-=1;self.channel_active[ch]-=1
    self.stats['client_completions']+=1;done()
  if any(self.returns):
   self.return_scheduled=True;self.clock.after(self.core_ps,self._deliver)
  if any(self.queues):self._schedule()
 def drained(self):return not (any(self.queues) or any(self.pending) or any(self.returns))
 def close(self):
  if not self.drained():raise ValueError('shared memory transport not drained')
  self.backend.close()
