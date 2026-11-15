"""Construct only services present on the selected macro/control/data endpoints."""
from collections import Counter
from native_product_binding import validate
from macro_service_runner import Runner
from macro_projection_service import LocalProjection
import macro_scalar_services as scalar

def build(hardware,wiring,plan_sha256,*,clock,transport,memory,srams,g_packet,core_ps):
 validate(wiring,plan_sha256,hardware)
 sites={n for n,m in hardware['macro_instances'].items() if m['role']=='S'}
 if set(srams)!=sites:raise ValueError('one actual model for each declared SRAM macro is required')
 targets=hardware['native_dispatch_overlay']['targets']
 selected={r['owner'] for r in wiring['selected_memory_connections']}
 providers={};models={};busy=set();stats=Counter()
 def wrap(owner,bind):
  def provider(raw):
   run=bind(raw)
   def execute(done):
    if owner in busy:raise ValueError('LC already executing a CALL: '+owner)
    busy.add(owner)
    def terminal():busy.remove(owner);stats[owner]+=1;done()
    run(terminal)
   return execute
  return provider
 def require(owner,master):
  found=[n for n in hardware['control_groups'][owner]['macros'] if hardware['macro_instances'][n]['master']==master]
  if len(found)!=1:raise ValueError('service has no declared macro: '+owner+' '+master)
  return found[0]
 for target in targets:
  owner=target['group'];i=target['id']
  if owner not in selected:continue
  runner=Runner(clock,srams[hardware['control_groups'][owner]['private_sram']],
   transport.client(12+i),transport.client(21+i),memory,core_ps=core_ps)
  models[owner]={'runner':runner,'macro_models':{}}
  local_projection=None
  for route in target['routes']:
   schema,abi,op=route['schema'],route['abi'],route['opcode']
   if schema==0x3152504d:
    macro=require(owner,'m_native_leaf_s32')
    if i not in (0,1,2):raise ValueError('M typed DMA binding')
    local_projection=LocalProjection(runner,transport.client(9+i))
    bind=local_projection.provider;models[owner]['macro_models'][macro]=local_projection
   else:
    if schema==0x314c5244:fn=lambda raw:scalar.dma(raw,False)
    elif schema==0x31535744:fn=lambda raw:scalar.dma(raw,True)
    elif schema==0x32485447:fn=scalar.gather
    elif schema==0x3156534e:require(owner,'n_s32_mod');fn=scalar.n32
    elif schema==0x314d5347:require(owner,'g_s32');fn=lambda raw:scalar.gated(raw,g_packet)
    elif (schema,abi,op)==(3,7,2):require(owner,'e_s32_mac_ap64');fn=scalar.add
    elif schema==0x31455052:require(owner,'e_s32_mac_ap64');fn=scalar.rope
    elif schema==0x31414d52:require(owner,'e_s32_mac_ap64');fn=scalar.rms_apply
    elif schema==0x31444d45:require(owner,'e_s32_mac_ap64');fn=scalar.dot
    else:raise ValueError('TLM lacks declared RTL service model '+repr((owner,schema,abi,op)))
    bind=lambda raw,fn=fn,runner=runner:runner.bind(fn,raw)
   providers[(i,schema,abi,op)]=wrap(owner,bind)
 return providers,models,stats
