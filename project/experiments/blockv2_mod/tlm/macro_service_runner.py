"""Resume each fixed service implementation on its actual resource completions."""
from collections import Counter
from macro_memory import Data
from native_tlm_timing import Transfer

class Runner:
 def __init__(self,clock,sram,read,write,memory,*,core_ps):
  self.clock,self.sram,self.read,self.write,self.memory=clock,sram,read,write,memory
  self.core_ps=core_ps;self.busy=False;self.stats=Counter()
 def edge(self,fn,cycles=1):
  self.clock.after(cycles*self.core_ps-self.clock.now%self.core_ps,fn)
 def execute(self,generator,done):
  if self.busy:raise ValueError('overlapping native CALL on one LC service slot')
  self.busy=True
  def resume(value=None):
   try:action=generator.send(value)
   except StopIteration:self.busy=False;self.stats['completed_calls']+=1;done();return
   op,*args=action;self.stats[op]+=1
   callback=lambda value=None:self.edge(lambda:resume(value))
   if op=='sread':self.sram.access(args[0],callback)
   elif op=='swrite':self.sram.access(args[0],lambda _:callback(),Data.of(args[1]))
   elif op=='read':
    address=args[0]
    self.read.submit(Transfer(address),lambda:callback(self.memory(address)))
   elif op=='write':
    address,payload,*tags=args;payload=Data.of(payload)
    tag=tags[0] if tags else address//64
    commit=self.memory.begin_write(address,tag,payload)
    def committed():commit();callback()
    transfer=Transfer(address,payload.payload);transfer.tag=tag
    self.write.submit(transfer,committed)
   elif op=='load_pipeline':
    from macro_activation_pipeline import ActivationLoad
    ActivationLoad(self).start(*args,done=lambda:callback())
   elif op=='store_pipeline':
    from macro_store_pipeline import StorePipeline
    StorePipeline(self).start(*args,done=lambda:callback())
   elif op=='cycles':self.edge(lambda:resume(),args[0])
   else:raise ValueError('unimplemented hardware action '+op)
  self.edge(resume)
 def bind(self,function,record):
  return lambda done:self.execute(function(record),done)

def read_words(first,count):
 parts=[]
 for i in range(count):parts.append((yield ('sread',first+i)))
 return Data.join(parts)
def write_words(first,data):
 data=Data.of(data)
 if len(data)%16:raise ValueError('whole SRAM words required')
 for i in range(0,len(data),16):yield ('swrite',first+i//16,data.slice(i,16))
def load_span(address,word,size):
 yield ('load_pipeline',address,word,size)
def store_span(word,address,size,tag=None):
 yield ('store_pipeline',word,address,size,tag)
