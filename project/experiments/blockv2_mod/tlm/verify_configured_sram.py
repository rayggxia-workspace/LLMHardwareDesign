"""Compare actual callback/data traces with PR260 under contention and capacity."""
import json,random,sys
from pathlib import Path
from native_tlm_timing import Clock,S128
from configured_sram import ConfiguredSram,profiles
from tlm_sram_profile import Sram,load_sram_profile
random.seed(219)
requests=[(random.randrange(1024),bytes([i%256])*16) for i in range(4096)]
def replay(factory):
    clock=Clock();sram=factory(clock);trace=[]
    for i,(word,data) in enumerate(requests):
        clock.after(i%11*1000,lambda i=i,w=word,d=data:sram.access(
            w,lambda value:trace.append((i,clock.now,value.hex())),d))
    clock.until(lambda:len(trace)==len(requests))
    return trace,sram.words,sram.stats['port_wait_ps']
reference=replay(lambda c:S128(c,core_ps=1000))
for bits in (128,256,512):
    result=replay(lambda c:ConfiguredSram(c,core_ps=1000,profile=Sram('U0',16384,bits,bits)))
    assert result==reference,'external width changed serial narrow-request semantics'
p=Path(sys.argv[1]);manifest=json.loads((p/'manifest.json').read_text())
hardware=json.loads((p/'hardware.json').read_text())
default,_=profiles(hardware,manifest['payloads']['hardware.json']['sha256'],None)
assert len(default)==9 and all(r.capacity_bytes==16384 for r in default.values())
out=Path(sys.argv[2])
example={'base_sha256':manifest['payloads']['hardware.json']['sha256'],
         'sram':{g:{**vars(r),'read_bits':512,'write_bits':512} for g,r in default.items()}}
config=out.with_suffix('.config.json');config.write_text(json.dumps(example,indent=2)+'\n')
parsed,digest=profiles(hardware,manifest['payloads']['hardware.json']['sha256'],config)
assert len(parsed)==9 and all(r.read_bits==512 for r in parsed.values())
try:profiles(hardware,'wrong-base',config)
except ValueError:pass
else:raise AssertionError('foreign-base SRAM config admitted')
small=ConfiguredSram(Clock(),core_ps=1000,profile=Sram('U0',8192,128,128))
try:small.access(512,lambda _:None,bytes(16))
except ValueError:pass
else:raise AssertionError('out-of-capacity access admitted')
report={'passed':True,'contention_requests_per_width':4096,'widths':[128,256,512],
        'same_callback_data_and_time_as_PR260':True,'physical_instances':9,
        'scope':'external config binding/capacity and narrow-service finite-ACK equivalence; no wide-service speedup claimed'}
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
