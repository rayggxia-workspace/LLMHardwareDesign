"""Run real M/T/S public-port transactions plus adversarial queue controls."""
import json
from pathlib import Path
from revision300_rtl import COMPILER
from io_slots import file_sha


def verify(root,out,cpus,run):
    assert cpus==16
    folder=root/'project/experiments/block_v1'
    sources=[root/'project/rtl/block_library_v1/block_v1_m.sv',
             root/'project/rtl/block_library_v1/block_v1_s16k.sv',
             root/'project/rtl/block_v1/transaction6k.sv',
             root/'project/rtl/block_v1/linkclose_bridge.sv',
             folder/'linkclose_mts_bench.sv',folder/'test_linkclose_mts.cpp']
    run([COMPILER,'--cc','--exe','--build','-j','16','-Wno-fatal',
         '--x-initial','unique','--x-assign','unique','--top-module','linkclose_mts_bench',
         '-Mdir',out/'obj','-CFLAGS','-std=c++17 -O2']+sources,'build.log')
    runs={}
    for label,init,seed in [('ones',1,121),('random121',2,121),('random122',2,122)]:
        run([out/'obj/Vlinkclose_mts_bench','+verilator+rand+reset+'+str(init),
             '+verilator+seed+'+str(seed)],label+'.json')
        runs[label]=json.loads((out/(label+'.json')).read_text())
        assert runs[label]['passed']
    assert all(r==runs['ones'] for r in runs.values())
    (out/'linkclose-protocol.json').write_text(json.dumps(dict(passed=True,
        sources={str(p.relative_to(root)):file_sha(p) for p in sources},runs=runs,
        physical_qualified=False,scope='Actual finite M response tag/two-slot bridge/T lease/S writes and readback; bounded protocol tests, not an unbounded formal protocol proof.'),indent=2)+'\n')
