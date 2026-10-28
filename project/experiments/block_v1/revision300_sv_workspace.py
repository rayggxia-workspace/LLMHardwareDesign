"""Actual finite S/V public-port global-normalization schedules."""
import json
from pathlib import Path


def measure(root,out,cpus,run):
    from io_slots import file_sha
    from revision300_rtl import COMPILER,sources
    assert cpus==16
    folder=root/'project/experiments/block_v1'
    _,v,numeric=sources(root,'v');_,s,_=sources(root,'s')
    wrapper=folder/'sv_workspace_bench.sv';bench=folder/'bench_sv_workspace.cpp'
    # The original reference includes this generated Verilator class name.
    # An alias allows unchanged reference functions to use the test harness.
    (out/'Vblock_v1_v.h').write_text('#include "Vsv_workspace_bench.h"\nusing Vblock_v1_v=Vsv_workspace_bench;\n')
    flags='-std=c++17 -O2 -I'+str(out)+' -I'+str(folder)
    run([COMPILER,'--cc','--exe','--build','-j','16','-Wno-fatal',
         '--x-initial','unique','--x-assign','unique','--top-module','sv_workspace_bench',
         '-I'+str(v[0].parent),'-Mdir',out/'obj','-CFLAGS',flags]+v+s+[wrapper,bench],'build.log')
    measurements=[]
    for label,initial,seed in [('ones',1,121),('random',2,122)]:
        run([out/'obj/Vsv_workspace_bench','+verilator+rand+reset+'+str(initial),'+verilator+seed+'+str(seed)],label+'.json')
        d=json.loads((out/(label+'.json')).read_text());assert d['passed'] and len(d['cases'])==27
        for row in d['cases']:
            assert row['workspace_payload_bytes']<=16384
            assert row['total_cycles']==sum(p['cycles']for p in row['phases'].values())
            assert sum(p['s_reads']+p['s_writes']for p in row['phases'].values())==sum(p['s_acks']for p in row['phases'].values())
            assert sum(p['v_commands']for p in row['phases'].values())==sum(p['v_responses']for p in row['phases'].values())
        measurements.append(d)
    assert measurements[0]==measurements[1]
    (out/'revision300-sv-workspace.json').write_text(json.dumps(dict(passed=True,
        initial_runs=2,measurements=measurements[0],rtl_sha256={str(p.relative_to(root)):file_sha(p)for p in v+s+[v[0].parent/'block_v1_v_tables.svh']},
        wrapper_sha256=file_sha(wrapper),bench_sha256=file_sha(bench),numeric_reference_sha256=file_sha(numeric),
        profiles={'0':'continuous sources/sinks','1':'source4of7 local cycles','2':'sink not ready2of5 local cycles'},
        maximum_s_payload_bytes=16384,maximum_v_replay_bytes=2048,additional_payload_queue_bytes=0,
        physical_integration_qualified=False,
        scope='Actual unchanged S16KiB and V RTL on one simulation clock; finite public-port benchmark controller. Operands come from S response holding register, EXP results overwrite same S addresses before denominator/global replay barriers. Independent expected arrays only check results and never feed post-initialization operands. Initial S writes, actual payload transactions/acks, simultaneous S/V requests, stalls and final consume counted. No extra payload queue or additional 6KiB/16KiB storage. Control/address/mux implementation and S/V interconnect P&R/timing are not qualified; this is block-level schedule/traffic evidence, not a system performance claim.'),indent=2)+'\n')
