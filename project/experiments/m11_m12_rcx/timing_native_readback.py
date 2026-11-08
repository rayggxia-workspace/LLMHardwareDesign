"""Compare restored logical-native readback with the original ODB timing.

Uses the same original SDC/libraries/SPEF, without any updated upper RC.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from timing_native import KINDS, sha
from timing_run import PLATFORM, SRAM_LEF


def slacks(log):
    return {m: float(v) for m, v in re.findall(r'worst slack (max|min)\s+([-\d.eE+]+)', log)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path(os.environ.get('TIMING_OUT', '.')) / 'result')
    a = p.parse_args(); a.out.mkdir()
    kind = KINDS[int(os.environ.get('TIMING_INDEX', '0'))]
    assert kind in ('C0', 'F0', 'T0', 'U0')
    d = json.loads((a.prepared / 'prepare.json').read_text())
    old = d['audits'][kind]
    restore = json.loads((a.prepared / 'diode-restoration.json').read_text())
    match = [x for x in restore if x['module'] == old['module']]; assert len(match) == 1
    v = Path(match[0]['restored_verilog'])
    text = ''.join(f'read_lef {{{x}}}\n' for x in
                   (PLATFORM + '/lef/NangateOpenCellLibrary.tech.lef', PLATFORM + '/lef/NangateOpenCellLibrary.macro.mod.lef', SRAM_LEF))
    text += ''.join(f'read_liberty {{{x}}}\n' for x in old['libraries'])
    text += f'read_verilog {{{v}}}\nlink_design -hier {old["module"]}\nread_sdc {{{old["sdc"]}}}\n'
    text += f'read_spef {{{Path(old["native"]).with_suffix(".spef")}}}\n'
    text += '''set_propagated_clock [all_clocks]
set_clock_latency -source 0 [all_clocks]
report_worst_slack -max -digits 9
report_worst_slack -min -digits 9
report_parasitic_annotation > annotation.rpt
puts NATIVE_READBACK_COMPLETE
exit
'''
    script = a.out / 'readback.tcl'; script.write_text(text)
    with (a.out / 'openroad.log').open('xb') as f:
        subprocess.run(['openroad', '-no_init', '-threads', os.environ.get('TIMING_CPUS', '1'), '-exit', str(script.resolve())],
                       cwd=a.out, stdout=f, stderr=subprocess.STDOUT, check=True)
    log = (a.out / 'openroad.log').read_text()
    assert 'NATIVE_READBACK_COMPLETE' in log
    assert 'not found' not in log and 'not connected' not in log
    reference = Path(old['audit']).parent / 'openroad.log'
    before, after = slacks(reference.read_text()), slacks(log)
    assert set(before) == set(after) == {'max', 'min'}
    result = dict(kind=kind, source_odb_audit=old['audit'], source_odb_audit_sha256=sha(old['audit']),
                  restored_verilog=str(v), restored_verilog_sha256=sha(v), original_odb_slack_ns=before,
                  restored_netlist_slack_ns=after, difference_ps={m: 1000 * (after[m] - before[m]) for m in before},
                  annotation_sha256=sha(a.out / 'annotation.rpt'),
                  scope='Native representation readback only, no macro-abstraction acceptance threshold.')
    (a.out / 'readback.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__': main()
