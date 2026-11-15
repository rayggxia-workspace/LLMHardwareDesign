"""Compare new macro providers with frozen RTL vectors, never Qwen acceptance."""
from pathlib import Path
import json,struct,random
from collections import Counter
from macro_memory import Data,Memory
import macro_scalar_services as services
from macro_projection_model import accumulate
from native_tlm_projection import accumulate as original_accumulate
from check_softmax import reference,coefficients
ROOT=Path.cwd();EV=ROOT/'evidence/architecture-revision-185'
def hexwords(p):return [bytes.fromhex(s)[::-1] for s in p.read_text().splitlines() if s]
def execute(gen,sram,ddr=None):
 response=None;stats=Counter()
 while True:
  try:action=gen.send(response)
  except StopIteration:return stats
  kind=action[0];stats[kind]+=1
  if kind=='sread':response=sram[action[1]]
  elif kind=='swrite':sram[action[1]]=action[2];response=Data.of(bytes(16))
  elif kind=='read':response=Data.of(ddr[action[1]])
  elif kind=='cycles':response=None
  else:raise AssertionError(action)
folder=EV/'n32-service-114532'
descs=hexwords(folder/'descriptors.hex');data=hexwords(folder/'vectors.hex')
cases=json.loads((folder/'vectors.json').read_text())['cases'];lut=coefficients()
for i,(raw,row) in enumerate(zip(descs,cases)):
 sram={j:Data.of(b) for j,b in enumerate(data[i*1024:(i+1)*1024])}
 scores=Data.join(list(sram.values())).i32(row['n'])
 stat=execute(services.n32(raw),sram)
 if row['mode']==0:
  n=(row['n']+3)//4
  got=Data.join(sram[j] for j in range(n)).i32(row['n'])
  assert got==reference(scores,lut)[1],('softmax',i)
  assert stat['sread']==3*n and stat['swrite']==2*n
 else:
  factor,index,shift,extra,mode=struct.unpack('<IIbBB5x',sram[1023].require())
  if row['mode']==1:assert (factor,shift,extra,mode)==(row['factor'],row['shift'],row['extra'],1),i
  else:assert (factor,index,mode)==(row['factor'],row['extra'],2),i
folder=EV/'e32-dot-114666';dotcases=json.loads((folder/'cases.json').read_text())
for i,raw in enumerate(hexwords(folder/'descriptors.hex')):
 ddr={}
 for label,base in [('a',0x100000),('b',0x200000)]:
  ddr.update({base+64*j:b for j,b in enumerate(hexwords(folder/(label+'-'+str(i)+'.hex')))})
 sram={};execute(services.dot(raw),sram,ddr)
 assert sram[900].i32()==dotcases[i]['output'],('dot',i)
rng=random.Random(185)
for head16 in (False,True):
 for _ in range(128):
  weights=bytes(rng.randrange(256) for _ in range(1024))
  scales=struct.pack('<'+'H'*(64 if head16 else 8),*[rng.randrange(1,0x1800) for _ in range(64 if head16 else 8)])
  record=weights+scales+(b'' if head16 else bytes(48))
  activation=[rng.randrange(-32768,32768) for _ in range(128)]
  shift=rng.randrange(5);a=[0]*8;b=[0]*8
  accumulate(record,activation,shift,a,head16)
  original_accumulate(record,activation,shift,b,head16)
  assert a==b
def missing(_):raise KeyError()
memory=Memory(missing,[{'base':4096,'bytes':128}])
partial=Data.join([Data.of(b'x'*16),Data.unknown(48)])
commit=memory.begin_write(4096,123,partial)
assert memory(4096).known==0
commit();assert memory(4096).slice(0,16).require()==b'x'*16
try:memory(4096).require()
except ValueError:pass
else:raise AssertionError('unknown padding treated as valid')
commit=memory.begin_write(4096,124,Data.of(b'y'*64));commit()
assert memory(4096).require()==b'y'*64 and memory.stats['workspace_rewrites']==1
print(json.dumps({'n32_RTL_vector_cases':len(cases),'dot_RTL_vector_cases':len(dotcases),
 'projection_PR260_arithmetic_cases':256,'DDR_commit_rewrite_validity':True,
 'scope':'macro numerical contract regression only; Qwen and timing acceptance false'}))
