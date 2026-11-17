"""Compare boundary timing of frozen macro models and detailed old netlists.

Explicit analysis harness: ideal common clock and quiet projected upper RC.
Internal native RC is unchanged, so passing does not certify native coupling.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess

from timing_native import sha

CASES = [('full', 'quiet-baseline'), ('abstract', 'quiet-baseline'),
         ('full', 'quiet-updated'), ('abstract', 'quiet-updated'),
         ('full', 'quiet-updated-source'), ('full', 'quiet-updated-sink'),
         ('abstract', 'quiet-updated-source'), ('abstract', 'quiet-updated-sink')]
PLATFORM = '/OpenROAD-flow-scripts/flow/platforms/nangate45'
SRAM_LEF = '/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.lef'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared', type=Path, required=True)
    p.add_argument('--case', type=int, default=int(os.environ.get('TIMING_INDEX', '0')), choices=range(len(CASES)))
    p.add_argument('--driver-proof', type=Path)
    p.add_argument('--control-table', type=Path)
    p.add_argument('--ideal-parent', type=Path)
    p.add_argument('--out', type=Path, default=Path(os.environ.get('TIMING_OUT', '.')) / 'result')
    a = p.parse_args(); a.out.mkdir()
    prep = json.loads((a.prepared / 'prepare.json').read_text())
    binding = json.loads(Path(prep['binding']).read_text())['endpoints']
    level, rc = CASES[a.case]
    driver_proof = json.loads(a.driver_proof.read_text()) if a.driver_proof else None
    if driver_proof:
        assert driver_proof['nets'] == driver_proof['exclusive_boundary_drivers'] == 2491
        assert driver_proof['prepared_sha256'] == sha(a.prepared / 'prepare.json')
    spef = Path(prep['upper_rc'][rc]['path'])
    assert sha(spef) == prep['upper_rc'][rc]['sha256']
    text = f'read_lef {{{PLATFORM}/lef/NangateOpenCellLibrary.tech.lef}}\n'
    text += f'read_lef {{{PLATFORM}/lef/NangateOpenCellLibrary.macro.mod.lef}}\n'
    text += f'read_lef {{{SRAM_LEF}}}\n'
    if level == 'abstract':
        for name in ('P', 'U', 'C', 'F', 'J'):
            text += f'read_lef {{/public/home/yuzelu/PingyangHuang/issue-204-qwen-switch-r10/inputs/{name}.lef}}\n'
        text += 'read_lef {/public/home/yuzelu/PingyangHuang/issue-204-qwen-switch-r19/run-98673-qwen_nine_transport/native/switch.lef}\n'
    libraries = prep['libraries'] if level == 'full' else [prep['libraries'][0], *[d['model'] for d in prep['audits'].values()]]
    unique = {}
    for f in libraries: unique.setdefault(sha(f), f)
    text += ''.join(f'read_liberty {{{f}}}\n' for f in unique.values())
    if level == 'full': text += ''.join(f'read_verilog {{{f}}}\n' for f in prep['full_verilog'])
    text += f'read_verilog {{{prep["harness"]}}}\nlink_design -hier qwen_timing_harness\n'
    text += '''create_clock -name core -period 3.3333 [get_ports clk]
set_clock_transition 0.05 [get_clocks core]
set_clock_uncertainty 0.1 [get_clocks core]
set_input_delay -max 0.8 -clock core [all_inputs -no_clocks]
set_input_delay -min 0.2 -clock core [all_inputs -no_clocks]
set_input_transition 0.05 [all_inputs -no_clocks]
set_output_delay -max 0.8 -clock core [all_outputs]
set_output_delay -min 0.2 -clock core [all_outputs]
set_load 2.0 [all_outputs]
set_propagated_clock [all_clocks]
'''
    # The top-level reader creates/replaces its parasitic network; subsequent
    # hierarchical reads find it and append the native fragments. Reversing
    # this order loses native-to-parent stitching at the interface.
    text += f'read_spef {{{spef}}}\n'
    if a.ideal_parent:
        ideal = json.loads(a.ideal_parent.read_text())
        assert ideal['prepared_sha256'] == sha(a.prepared / 'prepare.json')
        assert ideal['sha256'] == sha(ideal['path'])
        assert ideal['added_resistance_ohm'] == ideal['added_capacitance_ff'] == 0
        text += f'read_spef {{{ideal["path"]}}}\n'
    if level == 'full':
        for inst, f in prep['full_spefs']: text += f'read_spef -path {{{inst}}} {{{f}}}\n'
    text += '''report_units
report_parasitic_annotation -report_unannotated > annotation.rpt
check_setup -verbose > check-setup.rpt
report_worst_slack -max -digits 9
report_worst_slack -min -digits 9
report_tns -digits 9
report_checks -path_delay max -group_path_count 25 -format full_clock_expanded -fields {slew capacitance input_pin net} -digits 9 > worst-max.rpt
report_checks -path_delay min -group_path_count 25 -format full_clock_expanded -fields {slew capacitance input_pin net} -digits 9 > worst-min.rpt
report_check_types -violators -max_slew -max_capacitance -digits 9 > electrical.rpt
set fp [open boundary.tsv w]
puts $fp "net\tmode\tslack_ns\tarrival_ns\trequired_ns\tstartpoint\tendpoint"
set coverage [open coverage.tsv w]
puts $coverage "net\tsource_pins\tsink_pins\tmax_paths\tmin_paths"
'''
    if driver_proof:
        # Reuse the already-propagated whole-design timing graph. A hierarchy
        # interface shell has no graph vertex; the proven exclusive leaf
        # output has exactly the timing paths crossing its corresponding word.
        text = text[:text.index('set fp [open boundary.tsv w]')]
        text += '''set fp [open boundary.tsv w]
puts $fp "net\tmode\tslack_ns\tmeasurement_pin"
set coverage [open coverage.tsv w]
puts $coverage "net\tsource_pins\tsink_pins\tmax_finite_slack\tmin_finite_slack"
'''
    for net, ((src, sp), (dst, dp)) in binding.items():
        text += f'set from_pin [get_pins {{{src}/{sp}}}]\nset sink_pin [get_pins {{{dst}/{dp}}}]\n'
        text += 'if {[llength $from_pin] != 1 || [llength $sink_pin] != 1} {error "Missing/ambiguous boundary pins"}\n'
        if driver_proof:
            vertex = driver_proof['rows'][net]['leaf_driver'] if level == 'full' else src + '/' + sp
            text += f'set vertex [get_pins {{{vertex}}}]\n'
            text += 'if {[llength $vertex] != 1} {error "Missing actual boundary driver vertex"}\n'
            text += 'set mx [get_property $vertex slack_max]\nset mn [get_property $vertex slack_min]\n'
            text += 'if {abs($mx)>1e20 || abs($mn)>1e20} {error "Boundary has no finite propagated timing slack"}\n'
            text += f'puts $fp "{net}\tmax\t$mx\t{vertex}"\nputs $fp "{net}\tmin\t$mn\t{vertex}"\n'
            text += f'puts $coverage "{net}\t1\t1\t1\t1"\n'
            continue
        text += 'set counts {}\nforeach mode {max min} {\n'
        text += 'set paths [find_timing_paths -through $from_pin -through $sink_pin -path_delay $mode -group_path_count 1 -endpoint_path_count 1 -sort_by_slack]\n'
        text += 'lappend counts [llength $paths]\nforeach path $paths {\n'
        text += 'set endpoint_point [lindex [get_property $path points] end]\n'
        text += f'puts $fp "{net}\t$mode\t[get_property $path slack]\t[get_property $endpoint_point arrival]\t[get_property $endpoint_point required]\t[get_full_name [get_property $path startpoint]]\t[get_full_name [get_property $path endpoint]]"\n'
        text += '}\n}\n'
        text += f'puts $coverage "{net}\t[llength $from_pin]\t[llength $sink_pin]\t[join $counts \\t]"\n'
    text += 'close $fp\nclose $coverage\n'
    if driver_proof:
        samples = {}
        for net, ((src, _), _) in binding.items(): samples.setdefault(src[0], net)
        samples['extreme'] = 'word_1410'
        text += 'set checks [open slack-crosscheck.tsv w]\nputs $checks "net\tmode\tpropagated_ns\tfiltered_ns\tdifference_ps"\n'
        for net in samples.values():
            src, pin = binding[net][0]
            vertex = driver_proof['rows'][net]['leaf_driver'] if level == 'full' else src + '/' + pin
            text += f'set vertex [get_pins {{{vertex}}}]\nforeach mode {{max min}} {{\n'
            text += 'set prop [get_property $vertex slack_$mode]\nset best 1e30\n'
            text += 'foreach path [find_timing_paths -through $vertex -path_delay $mode -group_path_count 1 -endpoint_path_count 1 -sort_by_slack] {set best [expr {min($best,[get_property $path slack])}]}\n'
            text += 'set diff [expr {1000.0*($prop-$best)}]\n'
            text += f'puts $checks "{net}\t$mode\t$prop\t$best\t$diff"\n'
            text += 'flush $checks\nif {abs($diff)>0.01} {error "Propagated vertex slack differs from explicit filtered path beyond 0.01 ps numerical crosscheck"}\n}\n'
        text += 'close $checks\n'
    text += 'puts TIMING_CONTEXT_COMPLETE\nexit\n'
    script = a.out / 'timing.tcl'; script.write_text(text)
    with (a.out / 'openroad.log').open('xb') as f:
        process = subprocess.Popen(['openroad', '-no_init', '-threads', os.environ.get('TIMING_CPUS', '1'), '-exit', str(script.resolve())],
                                   cwd=a.out, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in process.stdout:
            f.write(line); f.flush()
            lower = line.lower()
            if b'[warning' in lower and any(s in lower for s in (b'not found', b'not linked', b'not a valid', b'no liberty')):
                process.terminate(); process.wait()
                raise RuntimeError('Rejected incomplete timing annotation before further analysis: ' + line.decode(errors='replace'))
        assert process.wait() == 0, 'OpenROAD analysis failed; see preserved log.'
    log = (a.out / 'openroad.log').read_text()
    assert 'TIMING_CONTEXT_COMPLETE' in log
    missing = [line for line in log.splitlines() if '[WARNING' in line.upper() and any(s in line.lower() for s in ('not found', 'not linked', 'not a valid', 'no liberty'))]
    assert not missing, missing[:10]
    control_difference_ps = None
    if a.control_table:
        with a.control_table.open() as f:
            control = {(r['net'], r['mode']): float(r['slack_ns']) for r in csv.DictReader(f, delimiter='\t')}
        with (a.out / 'boundary.tsv').open() as f:
            current = {(r['net'], r['mode']): float(r['slack_ns']) for r in csv.DictReader(f, delimiter='\t')}
        assert len(control) == len(current) == 4982 and set(control) == set(current)
        control_difference_ps = max(1000 * abs(current[k] - control[k]) for k in current)
        assert control_difference_ps <= 0.01, control_difference_ps
    result = dict(case=a.case, level=level, upper_rc=rc, prepared=str(a.prepared),
                  prepared_sha256=sha(a.prepared / 'prepare.json'), upper_spef_sha256=sha(spef),
                  script_sha256=sha(script), assumptions=prep['assumptions'], direct_macro_reuse_qualified=False,
                  measurement_method='propagated_slack_at_proven_exclusive_leaf_driver' if driver_proof else 'explicit_filtered_paths',
                  hierarchical_spef_read_order='top_then_native_parent_before_child',
                  explicit_ideal_parent_sha256=sha(a.ideal_parent) if a.ideal_parent else None,
                  driver_proof_sha256=sha(a.driver_proof) if a.driver_proof else None,
                  old_explicit_control_maximum_difference_ps=control_difference_ps,
                  files={f.name: dict(bytes=f.stat().st_size, sha256=sha(f)) for f in a.out.iterdir() if f.is_file()})
    (a.out / 'timing.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(case=a.case, level=level, rc=rc)), flush=True)


if __name__ == '__main__': main()
