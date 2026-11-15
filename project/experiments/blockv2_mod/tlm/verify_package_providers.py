"""Bind every descriptor in the whole package without executing any service."""
import json,struct,sys,importlib.util
from pathlib import Path
from collections import Counter
from native_package_runtime import load
from native_provider_registry import build
from native_tlm_timing import Clock,S128
from native_tlm_local import descriptor_key
package,hardware_path,g_reference=map(Path,sys.argv[1:4])
manifest,payloads,pages=load(package)
hardware=json.loads(hardware_path.read_text())
clock=Clock();srams={g:S128(clock,core_ps=1000) for g in hardware['leaf_inventory']}
spec=importlib.util.spec_from_file_location('block_g_reference',g_reference)
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
class NoExecution:
    def submit(self,*a,**k):raise AssertionError('admission must not execute')
def memory(address):raise AssertionError('admission must not read memory')
registry,models=build(hardware,json.loads(payloads['candidate-wiring.json']),
                     clock=clock,dram=NoExecution(),memory=memory,srams=srams,
                     g_packet=g.packet,core_ps=1000)
calls=json.loads(payloads['calls.json']);raw=payloads['descriptors.bin'];counts=Counter()
for i,c in enumerate(calls):
    record=raw[128*i:128*(i+1)]
    key=(c['target'],*descriptor_key(record,manifest['topology']))
    if key not in registry:raise ValueError('missing declared TLM service '+repr(key))
    try:
        result=registry[key](record)
        if not callable(result):raise ValueError('provider did not bind execution')
    except Exception as e:
        raise ValueError(f'descriptor {i}, target/schema/abi/op {key}: {e}') from e
    counts[str(key)]+=1
report={'passed':True,'calls_bound':len(calls),'service_bindings':dict(counts),
        'scope':'whole-package hardware-route and provider descriptor admission; services not executed',
        'delivery_accepted':False}
Path(sys.argv[4]).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
