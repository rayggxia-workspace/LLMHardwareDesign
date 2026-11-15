"""Admit every CALL in both complete packages into the actual macro registry."""
import json,importlib.util
from pathlib import Path
from collections import Counter
from native_package_runtime import load
from native_tlm_local import descriptor_key
from native_tlm_timing import Clock
from macro_memory import profiles,MacroSram,Memory
from macro_memory_transport import SharedMemory
from macro_provider_registry import build
class NoExecution:
 def submit(self,*args,**kwargs):raise AssertionError('binding check attempted execution')
def missing(_):raise KeyError()
env=json.loads(Path('reproducibility/environment.json').read_text())
spec=importlib.util.spec_from_file_location('g_reference',env['g_reference']);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
result=[]
for stage in ('prefill','decode'):
 root=Path('evidence/architecture-revision-185/shared-memory-bound-packages-114908')/(stage+'-package')
 manifest,payloads,pages=load(root);hardware=json.loads(payloads['hardware.json']);wiring=json.loads(payloads['candidate-wiring.json'])
 clock=Clock();memory=Memory(missing,[]);ps,_=profiles(hardware,manifest['payloads']['hardware.json']['sha256'])
 srams={n:MacroSram(clock,core_ps=3333,profile=v) for n,v in ps.items()}
 transport=SharedMemory(clock,NoExecution(),hardware['base_rtl_contract'],core_ps=3333)
 providers,models,_=build(hardware,wiring,manifest['plan_sha256'],clock=clock,transport=transport,memory=memory,srams=srams,g_packet=g.packet,core_ps=3333)
 counts=Counter();raw=payloads['descriptors.bin']
 for i,call in enumerate(json.loads(payloads['calls.json'])):
  record=raw[128*i:128*(i+1)];key=(call['target'],*descriptor_key(record,manifest['topology']))
  if key not in providers:raise ValueError('missing macro provider '+str(key))
  providers[key](record);counts[str(key)]+=1
 assert not clock.events
 result.append({'stage':stage,'calls':sum(counts.values()),'routes':len(counts),'macro_sites':sorted(srams),
  'owners':sorted(models),'binding_complete':True,'execution_accepted':False})
print(json.dumps(result))
