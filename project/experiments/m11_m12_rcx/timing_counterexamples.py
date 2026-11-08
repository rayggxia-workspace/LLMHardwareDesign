"""Materialize every observed setup false pass as an explicit detailed path.

Reuses the exact completed updated-reference setup. Adds path traces and
source electrical-domain classification; no P&R or field extraction.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess

from timing_native import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--comparison', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path(os.environ.get('TIMING_OUT', '.')) / 'result')
    a = p.parse_args(); a.out.mkdir()
    with (a.comparison / 'boundary-comparison.tsv').open() as f:
        rows = [r for r in csv.DictReader(f, delimiter='\t') if int(r['macro_false_pass_after'])]
    assert rows and all(r['mode'] == 'max' for r in rows)
    original_script = a.reference / 'timing.tcl'
    text = original_script.read_text().split('report_units\n', 1)[0]
    assert text.count('read_spef') > 10 and 'ideal-parent.spef' in text
    text += '''report_units
set checks [open counterexamples.tsv w]
puts $checks "net\tdriver\tpropagated_slack_ns\texplicit_slack_ns\tmacro_slack_ns\tdifference_ps\tstartpoint\tendpoint"
set points [open path-points.tsv w]
puts $points "net\tindex\tpin\tmaster\tslew_rise_ns\tslew_fall_ns\tarrival_ns"
'''
    for row in rows:
        net, driver = row['net'], row['detailed_measurement_pin']
        text += f'set driver [get_pins {{{driver}}}]\n'
        text += 'set propagated [get_property $driver slack_max]\nset worst 1e30\nset chosen ""\n'
        text += 'foreach path [find_timing_paths -through $driver -path_delay max -group_path_count 1 -endpoint_path_count 1 -sort_by_slack] {\nset value [get_property $path slack]\nif {$value<$worst} {set worst $value;set chosen $path}\n}\n'
        text += 'if {$chosen eq "" || $worst>=0} {error "Claimed false pass not confirmed by explicit detailed path"}\n'
        text += 'set difference [expr {1000*($propagated-$worst)}]\nif {abs($difference)>0.01} {error "Explicit-path discrepancy exceeds numerical crosscheck"}\n'
        text += f'puts $checks "{net}\t{driver}\t$propagated\t$worst\t{row["macro_after_slack_ns"]}\t$difference\t[get_full_name [get_property $chosen startpoint]]\t[get_full_name [get_property $chosen endpoint]]"\nflush $checks\n'
        text += 'set i 0\nforeach point [get_property $chosen points] {\nset pin [get_property $point pin]\nset name [get_full_name $pin]\nset master ""\nset divider [string last / $name]\n'
        text += 'if {$divider>=0} {set instance [get_cells -quiet [list [string range $name 0 [expr {$divider-1}]]]];if {[llength $instance]==1} {set master [get_property $instance ref_name]}}\n'
        text += f'puts $points "{net}\t$i\t$name\t$master\t[get_property $pin slew_max_rise]\t[get_property $pin slew_max_fall]\t[get_property $point arrival]"\nincr i\n}}\n'
        text += f'report_checks -through $driver -path_delay max -group_path_count 1 -format full_clock_expanded -fields {{slew capacitance input_pin net}} -digits 9 > {net}.rpt\n'
    text += 'close $checks\nclose $points\nputs COUNTEREXAMPLES_COMPLETE\nexit\n'
    script = a.out / 'counterexamples.tcl'; script.write_text(text)
    with (a.out / 'openroad.log').open('xb') as log:
        process = subprocess.Popen(['openroad', '-no_init', '-threads', os.environ.get('TIMING_CPUS', '1'), '-exit', str(script.resolve())],
                                   cwd=a.out, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in process.stdout:
            log.write(line); log.flush()
            if b'[warning' in line.lower() and b'not found' in line.lower():
                process.terminate(); process.wait(); raise RuntimeError(line.decode(errors='replace'))
        assert process.wait() == 0
    assert 'COUNTEREXAMPLES_COMPLETE' in (a.out / 'openroad.log').read_text()
    with (a.out / 'counterexamples.tsv').open() as f: actual = list(csv.DictReader(f, delimiter='\t'))
    assert len(actual) == len(rows)
    result = dict(confirmed_false_pass_signal_count=len(actual), reference=str(a.reference),
                  reference_script_sha256=sha(original_script), comparison=str(a.comparison),
                  comparison_sha256=sha(a.comparison / 'boundary-comparison.tsv'),
                  all_explicit_detailed_paths_negative=True,
                  maximum_propagated_vs_explicit_difference_ps=max(abs(float(r['difference_ps'])) for r in actual),
                  files={f.name: dict(bytes=f.stat().st_size, sha256=sha(f)) for f in a.out.iterdir() if f.is_file()})
    (a.out / 'counterexamples.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}), flush=True)


if __name__ == '__main__': main()
