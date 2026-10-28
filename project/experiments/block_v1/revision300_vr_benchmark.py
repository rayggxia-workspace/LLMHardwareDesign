"""Measured public handshakes, exact old RTL, and finite schedules for V/R."""
import json
from pathlib import Path


def measure(root,out,cpus,run,kind,variant):
    from io_slots import file_sha
    from revision300_rtl import COMPILER,sources
    assert cpus==16 and kind in ('v','r') and variant in ('baseline','revised','extended')
    top,rtls,numeric=sources(root,kind)
    bound=rtls+([rtls[0].parent/'block_v1_v_tables.svh']if kind=='v'else[])
    old=json.loads((root/'project/experiments/block_v1/baseline-vr-sha256.json').read_text())
    if variant=='baseline':
        prefix=out.parents[2]/'block-v1-20261027-196/src'
        for p in bound:assert file_sha(prefix/p.relative_to(root))==old[str(p.relative_to(root))]
        bound=[prefix/p.relative_to(root)for p in bound]
        rtls=bound[:-1]if kind=='v'else bound
    bench=root/'project/experiments/block_v1/bench_vector_recurrent.cpp'
    flags='-std=c++17 -O2'+(' -DBENCH_RECURRENT'if kind=='r'else'')+(' -DBASELINE_VR'if variant=='baseline'else'')+(' -DEXTENDED_VR'if variant=='extended'else'')
    run([COMPILER,'--cc','--exe','--build','-j','16','-Wno-fatal','--x-initial','unique','--x-assign','unique',
         '--top-module',top,'-I'+str(rtls[0].parent),'-Mdir',out/'obj','-CFLAGS',flags]+rtls+[bench],'build.log')
    results=[]
    for label,initial,seed in [('ones',1,121),('random',2,122)]:
        run([out/'obj'/('V'+top),'+verilator+rand+reset+'+str(initial),'+verilator+seed+'+str(seed)],label+'.json')
        value=json.loads((out/(label+'.json')).read_text());assert value['passed']is True
        assert len(value['cases'])==((36 if kind=='v'else 9)if variant=='extended'else(42 if kind=='v'else 24))
        identities=set()
        for row in value['cases']:
            key=(row['workload'],row['size'],row['profile']);assert key not in identities;identities.add(key)
            assert row['total_cycles']==sum(p['cycles']for p in row['phases'].values())
            for p in row['phases'].values():
                assert p['cycles']==sum(p['cycle_attribution'].values())
                assert p['accepted_commands']==p['responses']
                assert p['request_container_bytes']==p['response_container_bytes']==16*p['accepted_commands']
                assert p['request_data_valid_bytes']<=p['request_container_bytes']
                assert p['response_data_valid_bytes']<=p['response_container_bytes']
            row['modeled_output_gbytes_per_second_at_300mhz']=.3*row['semantic_output_bytes']/row['total_cycles']
        results.append(value)
    assert results[0]==results[1],'Undefined payload affected public-port benchmark'
    result=dict(passed=True,macro=kind.upper(),variant=variant,initial_runs=2,measurements=results[0],
        rtl_sha256={str(p):file_sha(p)for p in bound},bench_sha256=file_sha(bench),numeric_reference_sha256=file_sha(numeric),
        compiler_sha256=file_sha(Path(COMPILER)),baseline_git_commit='ad3c2b34511d58792ec5b550252590912f03252e'if variant=='baseline'else None,
        physical_implementation_completed=False,final_netlist_verified=False,
        profiles={'0':'continuous producer/consumer','1':'three producer-gap cycles after each fourth accepted command within a stream',
                  '2':'consumer not ready two of each five local stream cycles'},
        scope='Actual public handshakes and independent integer-reference outputs. Reset excluded; all phase barriers, acknowledgements, padding, reads, and R commit/state export included. R state_export is explicit optional external traffic priced separately, not a mandatory resident per-token transfer. V baseline long function schedules padded eight-element invocations; revised uses finite replay. Valid bytes include actual scheduled padding; semantic_output_bytes identifies useful output. Phase schedules are sequential and do not claim cross-phase overlap. No S execution, internal pipeline occupancy, clock-based speedup, or model/system qualification.300MHz bandwidth is arithmetic on measured cycles only.')
    (out/'revision300-vr-benchmark.json').write_text(json.dumps(result,indent=2)+'\n')


def compare(root,out,cpus,run,kind):
    from io_slots import file_sha
    assert cpus==16 and kind in ('v','r')
    data={};bindings={}
    for variant in ('baseline','revised'):
        folder=out.parent/('revision300-bench-'+kind+'-'+variant)
        r=json.loads((folder/'receipt.json').read_text());assert r['passed'] and r['mode']==folder.name
        p=folder/'revision300-vr-benchmark.json';assert file_sha(p)==r['outputs'][p.name]
        d=json.loads(p.read_text());assert d['passed'] and d['variant']==variant
        assert d['bench_sha256']==file_sha(root/'project/experiments/block_v1/bench_vector_recurrent.cpp')
        data[variant]={(row['workload'],row['size'],row['profile']):row for row in d['measurements']['cases']}
        bindings[variant]=dict(receipt_sha256=file_sha(folder/'receipt.json'),report_sha256=file_sha(p))
    assert set(data['baseline'])==set(data['revised'])
    rows=[]
    for key in sorted(data['baseline']):
        old,new=(data[v][key]for v in ('baseline','revised'))
        assert old['semantic_output_bytes']==new['semantic_output_bytes']
        rows.append(dict(workload=key[0],size=key[1],profile=key[2],baseline_cycles=old['total_cycles'],
            revised_cycles=new['total_cycles'],cycle_ratio_old_over_new=old['total_cycles']/new['total_cycles'],
            baseline_phases=old['phases'],revised_phases=new['phases']))
    (out/'revision300-vr-comparison.json').write_text(json.dumps(dict(passed=True,macro=kind.upper(),bindings=bindings,cases=rows,
        scope='Same semantic finite workload, measured old/new public cycles including all stated phases. Cycle ratio is not a physical-clock or model/system speedup.'),indent=2)+'\n')
