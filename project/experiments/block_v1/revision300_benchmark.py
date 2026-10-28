"""Measure actual RTL handshakes, including the immutable old M cycle baseline."""
import json
from pathlib import Path


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
    run([COMPILER, '--cc', '--exe', '--build', '-j', '16', '-Wno-fatal',
         '--x-initial', 'unique', '--x-assign', 'unique', '--top-module', 'block_v1_m',
         '-Mdir', str(out/'obj'), '-CFLAGS', '-std=c++17 -O2', rtl, bench], 'build.log')
    layout = 'packed' if variant == 'packed' else 'legacy'
    observed = []
    for label, initial, seed in [('ones', 1, 121), ('random', 2, 122)]:
        name = label+'.json'
        run([out/'obj/Vblock_v1_m', layout, '+verilator+rand+reset+'+str(initial),
             '+verilator+seed+'+str(seed)], name)
        result = json.loads((out/name).read_text())
        assert result['passed'] is True and len(result['cases']) == 16
        for row in result['cases']:
            phases = [row[x] for x in ('preload', 'work', 'finalization_and_readback')]
            assert row['logical_k'] == 1024 and row['logical_n'] == 8 and row['logical_macs'] == 8192
            assert row['total_cycles'] == sum(p['cycles'] for p in phases)
            for phase in phases:
                assert phase['cycles'] == sum(phase['cycle_attribution'].values())
                assert phase['accepted_commands'] == phase['retired_responses']
                assert phase['command_container_bytes'] == 16*phase['accepted_commands']
                assert phase['response_container_bytes'] == 16*phase['retired_responses']
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
