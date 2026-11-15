"""Byte validity and commit semantics for the declared native macro memories.

Uninitialized padding may be transported, as in RTL, but cannot silently become
an arithmetic input. Reusing a compiled workspace requires a new committed write.
"""
from dataclasses import dataclass
from bisect import bisect_right
from collections import Counter,deque
import struct
from tlm_sram_profile import Sram,load_sram_profile

@dataclass(frozen=True)
class Data:
 payload:bytes
 known:int
 def __post_init__(self):
  if not isinstance(self.payload,bytes) or self.known<0 or self.known>>len(self.payload):
   raise ValueError('invalid data/validity extent')
 @classmethod
 def of(cls,value):return value if isinstance(value,cls) else cls(bytes(value),(1<<len(value))-1)
 @classmethod
 def unknown(cls,size):return cls(bytes(size),0)
 def __len__(self):return len(self.payload)
 def slice(self,first,size):
  if not 0<=first<=first+size<=len(self):raise ValueError('data slice range')
  return Data(self.payload[first:first+size],(self.known>>first)&((1<<size)-1))
 def require(self):
  if self.known!=(1<<len(self))-1:raise ValueError('arithmetic/input read includes uncommitted bytes')
  return self.payload
 @classmethod
 def join(cls,parts):
  parts=list(parts);offset=0;known=0
  for p in parts:known|=p.known<<offset;offset+=len(p)
  return cls(b''.join(p.payload for p in parts),known)
 def i32(self,count=None):
  count=len(self)//4 if count is None else count
  return list(struct.unpack('<'+'i'*count,self.slice(0,4*count).require()))

class Memory:
 def __init__(self,readonly,regions):
  self.readonly=readonly;self.regions=sorted((r['base'],(r['bytes']+63)//64*64) for r in regions)
  self.bases=[x[0] for x in self.regions];self.words={};self.pending={};self.stats=Counter()
  for (a,n),(b,_) in zip(self.regions,self.regions[1:]):
   if a+n>b:raise ValueError('overlapping allocated DDR regions')
 def allocated(self,address):
  i=bisect_right(self.bases,address)-1
  return i>=0 and address+64<=sum(self.regions[i])
 def __call__(self,address):
  if address%64:raise ValueError('DDR beat alignment')
  if address in self.words:return self.words[address]
  try:data=self.readonly(address)
  except KeyError:
   if not self.allocated(address):raise ValueError('DDR address outside base allocation')
   return Data.unknown(64)
  data=Data.of(data)
  if len(data)!=64:raise ValueError('DDR image beat length')
  return data
 def begin_write(self,address,tag,payload):
  payload=Data.of(payload)
  if address%64 or not self.allocated(address) or len(payload)!=64 or type(tag) is not int or not 0<=tag<1<<64:
   raise ValueError('DDR write not bound to allocated address')
  if address in self.pending:raise ValueError('overlapping writes before completion')
  self.pending[address]=payload;self.stats['writes_started']+=1
  def commit():
   if self.pending.get(address) is not payload:raise ValueError('write identity changed')
   del self.pending[address]
   if address in self.words:self.stats['workspace_rewrites']+=1
   self.words[address]=payload;self.stats['writes_committed']+=1
  return commit

class MacroSram:
 def __init__(self,clock,*,core_ps,profile):
  self.clock,self.core_ps,self.profile=clock,core_ps,profile
  self.words={};self.next_port=0;self.responses=deque();self.stats=Counter()
 def access(self,word,done,payload=None):
  self.profile.beats(word,1,write=payload is not None,service_bits=128)
  if payload is not None:
   payload=Data.of(payload)
   if len(payload)!=16:raise ValueError('SRAM word length')
  edge=((self.clock.now+self.core_ps-1)//self.core_ps)*self.core_ps
  while self.responses and self.responses[0]<=edge:self.responses.popleft()
  start=max(edge,self.next_port)
  if len(self.responses)==2:start=max(start,self.responses.popleft())
  self.next_port=start+self.core_ps;self.responses.append(start+2*self.core_ps)
  self.stats['port_wait_ps']+=start-edge
  self.stats['writes' if payload is not None else 'reads']+=1
  def complete():
   if payload is not None:
    self.words[word]=payload
    done(Data.of(bytes(16))) # real compact SRAM write ACK has zero data
   else:done(self.words.get(word,Data.unknown(16)))
  self.clock.after(start-self.clock.now+2*self.core_ps,complete)

def profiles(hardware,hardware_sha,config=None):
 sites={name:m for name,m in hardware['macro_instances'].items() if m['role']=='S'}
 if config:
  rows,digest=load_sram_profile(config,hardware_sha,set(sites))
  if set(rows)!=set(sites) or any(p.assembly!=n for n,p in rows.items()):
   raise ValueError('SRAM config must identify each actual SRAM macro')
  return rows,digest
 return {name:Sram(name,m['source_profile']['capacity_bytes'],128,128) for name,m in sites.items()},None
