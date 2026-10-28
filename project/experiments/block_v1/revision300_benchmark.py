"""Measure actual RTL handshakes, including the immutable old M cycle baseline."""
import json
from pathlib import Path


def storage(root,out,cpus,run,kind,variant):
    from io_slots import file_sha
    from revision300_rtl import COMPILER,sources
    assert cpus==16 and kind in ('s','t') and variant in ('baseline','revised')
    top,rtls,_=sources(root,kind);rtl=rtls[0]
    baseline=variant=='baseline'
    if baseline:
        rtl=out.parents[2]/'block-v1-20261027-193/src'/rtl.relative_to(root)
        expected={'s':'f0c7ae7db0bae810e4b17c160e3bc23ec15612fa19ecee4cf5031dba27aae240',
                  't':'0491dc05357b61855a3fadd9598ac738bdf305a8c8306499ac8b6c184fa4b0b5'}
        assert file_sha(rtl)==expected[kind]
    bench=root/'project/experiments/block_v1/bench_store_handoff.cpp'
    flags='-std=c++17 -O2'+(' -DHANDOFF_T' if kind=='t'else'')+(''if baseline else' -DREVISED_ST')
    run([COMPILER,'--cc','--exe','--build','-j','16','-Wno-fatal','--x-initial','unique','--x-assign','unique',
         '--top-module',top,'-Mdir',out/'obj','-CFLAGS',flags,rtl,bench],'build.log')
    observed=[]
    for label,initial,seed in [('ones',1,121),('random',2,122)]:
        run([out/'obj'/('V'+top),'+verilator+rand+reset+'+str(initial),'+verilator+seed+'+str(seed)],label+'.json')
        result=json.loads((out/(label+'.json')).read_text());assert result['passed'] is True
        assert len(result['cases'])==(12 if kind=='t' else 16)
        for row in result['cases']:
            assert row['total_cycles']==sum(row[k]['cycles']for k in ('write','read','control'))
            for phase in ('write','read','control'):
                p=row[phase];assert p['cycles']==sum(p['cycle_attribution'].values())
            row['modeled_end_to_end_payload_gbytes_per_second_at_300mhz']=.3*row['effective_payload_bytes_each_direction']/row['total_cycles']
            row['modeled_read_phase_gbytes_per_second_at_300mhz']=.3*row['effective_payload_bytes_each_direction']/row['read']['cycles']
        observed.append(result)
    assert observed[0]==observed[1]
    result=dict(passed=True,kind=kind,variant=variant,rtl_path=str(rtl),rtl_sha256=file_sha(rtl),bench_sha256=file_sha(bench),
                compiler_sha256=file_sha(Path(COMPILER)),initial_runs=2,measurements=observed[0],
                baseline_git_commit='ad3c2b34511d58792ec5b550252590912f03252e'if baseline else None,
                physical_implementation_completed=False,final_netlist_verified=False,
                scope='Actual public-port cycles, payload and handshakes; storage access counters may overlap transfers. S includes write acknowledgements, T includes begin/commit/release. Reset excluded. Modeled300MHz bandwidth is not physical or system qualification; old baseline100MHz only.')
    (out/'revision300-st-benchmark.json').write_text(json.dumps(result,indent=2)+'\n')


def matrix(root, out, cpus, run, variant):
    from io_slots import file_sha
    from revision300_rtl import COMPILER
    assert cpus == 16 and variant in ('baseline', 'legacy', 'packed')
    bench = root/'project/experiments/block_v1/bench_matrix_macro.cpp'
    baseline = variant == 'baseline'
    rtl = (out.parents[2]/'block-v1-20261027-193/src/project/rtl/block_library_v1/block_v1_m.sv'
           if baseline else root/'project/rtl/block_library_v1/block_v1_m.sv')
    if baseline:
        assert file_sha(rtl) == 'd8ddfc5ff141fdf23d1326ada16491a3d5e0bc56b10ef72b4beb99c4cb41de54'
    flags = '-std=c++17 -O2'+('' if baseline else ' -DBENCH_REVISED')
    run([COMPILER, '--cc', '--exe', '--build', '-j', '16', '-Wno-fatal', '--public-flat-rw',
         '--x-initial', 'unique', '--x-assign', 'unique', '--top-module', 'block_v1_m',
         '-Mdir', str(out/'obj'), '-CFLAGS', flags, rtl, bench], 'build.log')
    layout = 'packed' if variant == 'packed' else 'legacy'
    observed = []
    for label, initial, seed in [('ones', 1, 121), ('random', 2, 122)]:
        name = label+'.json'
        run([out/'obj/Vblock_v1_m', layout, '+verilator+rand+reset+'+str(initial),
             '+verilator+seed+'+str(seed)], name)
        result = json.loads((out/name).read_text())
        assert result['passed'] is True and len(result['cases']) == 64
        for row in result['cases']:
            phases = [row[x] for x in ('preload', 'work', 'finalization_and_readback')]
            assert [row['logical_k'], row['logical_n']] in [[1024,8],[65,7],[9,1],[3072,8]]
            assert row['logical_macs'] == row['logical_k']*row['logical_n']
            assert row['total_cycles'] == sum(p['cycles'] for p in phases)
            for phase in phases:
                assert phase['cycles'] == sum(phase['cycle_attribution'].values())
                assert phase['accepted_commands'] == phase['retired_responses']
                assert phase['command_container_bytes'] == 16*phase['accepted_commands']
                assert phase['response_container_bytes'] == 16*phase['retired_responses']
                occupancy = phase['resource_occupancy_may_overlap']
                for name in ('product_issue_cycles', 'reduction_cycles', 'accumulation_cycles', 'arithmetic_union_cycles'):
                    assert 0 <= occupancy[name] <= phase['cycles']
            assert row['work']['resource_occupancy_may_overlap']['valid_s8_digit_products'] == row['logical_macs']*row['base_s8_products_per_logical_mac']
            row['measured_logical_macs_per_total_cycle'] = row['logical_macs']/row['total_cycles']
            row['modeled_gmac_per_second_at_300mhz'] = 0.3*row['measured_logical_macs_per_total_cycle']
        observed.append(result)
    assert observed[0] == observed[1], 'Uninitialized payload affected benchmark'
    result = dict(passed=True, variant=variant, rtl_path=str(rtl), rtl_sha256=file_sha(rtl),
                  bench_sha256=file_sha(bench), baseline_git_commit=('ad3c2b34511d58792ec5b550252590912f03252e' if baseline else None),
                  compiler_sha256=file_sha(Path(COMPILER)), initial_runs=2, measurements=observed[0],
                  physical_implementation_completed=False, final_netlist_verified=False,
                  scope='Actual RTL cycles and handshakes only; 300MHz rates are modeled, not physical timing qualification or whole-model speed. Old baseline remains 100MHz qualified.')
    (out/'revision300-m-benchmark.json').write_text(json.dumps(result, indent=2)+'\n')
