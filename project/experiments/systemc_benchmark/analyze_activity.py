"""Re-analyze a saved flat routed-M VCD, requiring real activity annotation.

No rebuild or numerical re-run is necessary when only the power tool's scope
was wrong. Original VCD, functional receipts and failed power logs are retained.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def normalize_vcd(source, destination, expected_window_ps, scope, escape_backslashes=False):
    stack, scopes = [], set()
    first = previous = None
    changed_names = 0
    mapping_hash = hashlib.sha256()
    with source.open() as src, destination.open('w') as dst:
        for line in src:
            fields = line.split()
            if fields[:1] == ['$scope']:
                stack.append(fields[2])
                scopes.add('/'.join(stack))
            elif fields[:1] == ['$upscope']:
                stack.pop()
            elif fields[:1] == ['$timescale'] and fields != ['$timescale', '1ps', '$end']:
                raise ValueError('expected explicit 1ps VCD')
            # Flattened Yosys names can contain literal backslashes. STA's SDC
            # name lookup consumes an escape, whereas Verilator emits the
            # literal character once. Escape only scope/reference names, never
            # identifier codes (which may themselves contain backslashes),
            # values or events. Physical pin audit still follows this transform.
            field = 2 if fields[:1] == ['$scope'] else 4 if fields[:1] == ['$var'] else None
            if escape_backslashes and field is not None and '\\' in fields[field]:
                old = line
                fields[field] = fields[field].replace('\\', '\\\\')
                line = ' '.join(fields) + '\n'
                mapping_hash.update((old + line).encode())
                changed_names += 1
            if line.startswith('#'):
                tick = int(line[1:])
                if first is None:
                    first = tick
                if previous is not None and tick < previous:
                    raise ValueError('nonmonotone VCD')
                previous = tick
                line = '#' + str(tick - first) + '\n'
            dst.write(line)
    if scope not in scopes:
        raise ValueError('requested scope absent from VCD')
    if first is None or previous - first != expected_window_ps:
        raise ValueError('VCD interval differs from functional timing receipt')
    return {'source_first_ps': first, 'window_ps': previous - first,
            'transform': 'subtract first timestamp; optional STA escaping of literal backslashes in names only; every value/event/order retained',
            'STA_literal_backslashes_escaped': escape_backslashes,
            'changed_name_records': changed_names,
            'name_mapping_sha256': mapping_hash.hexdigest() if changed_names else None}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('physical', type=Path)
    p.add_argument('liberty', type=Path)
    p.add_argument('vcd', type=Path)
    p.add_argument('functional_receipt', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--scope', default='dut/block_v2_m')
    p.add_argument('--sample-label', default='scalar M')
    p.add_argument('--cores', type=int, default=2)
    p.add_argument('--extra-lib', type=Path, action='append', default=[],
                   help='original characterized macro Liberty; loaded before ODB')
    p.add_argument('--escape-sta-backslashes', action='store_true')
    p.add_argument('--minimum-pin-coverage', type=float, default=.99,
                   help='fail incomplete annotation; all remaining pins still require classification')
    a = p.parse_args()
    if a.cores < 1 or not 0 < a.minimum_pin_coverage <= 1:
        raise ValueError('positive core count required')
    a.output.mkdir(exist_ok=False)
    timing = json.loads(a.functional_receipt.read_text())['timing']
    if not timing.get('passed'):
        raise ValueError('functional receipt did not pass')
    if any('}' in str(x) or '\n' in str(x) for x in [a.physical, a.liberty, a.vcd, a.output, a.scope, *a.extra_lib]):
        raise ValueError('unsupported Tcl path')
    vcd = a.output / 'normalized.vcd'
    window = normalize_vcd(a.vcd, vcd, timing['window_ps'], a.scope, a.escape_sta_backslashes)
    inputs = [a.liberty, *a.extra_lib, a.vcd, a.functional_receipt, Path(__file__)]
    inputs += [a.physical / ('6_final.' + x) for x in ('odb', 'spef', 'sdc', 'v')]
    script = a.output / 'power.tcl'
    script.write_text(''.join('read_liberty {%s}\n' % lib for lib in [a.liberty, *a.extra_lib]) +
        'read_db {%s}\nread_sdc {%s}\nread_spef {%s}\n' %
        (a.physical / '6_final.odb', a.physical / '6_final.sdc', a.physical / '6_final.spef') +
        'set_propagated_clock [all_clocks]\nreport_units\n' +
        'read_vcd -scope {%s} {%s}\nreport_activity_annotation\n' % (a.scope, vcd) +
        'report_power -digits 9\nputs "ACTIVITY_ANALYSIS_COMPLETED"\n')
    log = a.output / 'power.log'
    command = ['openroad', '-no_init', '-threads', str(a.cores), '-exit', str(script)]
    with log.open('w') as f:
        run = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT)
    text = log.read_text()
    annotated = re.findall(r'Annotated (\d+) pin activities\.', text)
    unannotated = re.findall(r'(?m)^unannotated\s+(\d+)', text)
    totals = re.findall(r'(?m)^Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)', text)
    valid = (run.returncode == 0 and 'ACTIVITY_ANALYSIS_COMPLETED' in text and
             not re.search(r'(?m)^(?:Error:|\[ERROR)', text) and len(annotated) == 1 and
             int(annotated[0]) > 0 and len(totals) == 1 and len(unannotated) == 1 and
             'Power (Watts)' in text)
    coverage = int(annotated[0]) / (int(annotated[0]) + int(unannotated[0])) if valid else None
    sufficient = valid and coverage >= a.minimum_pin_coverage
    result = {'tool_completed_with_real_annotation': bool(valid), 'scope': a.scope,
              'window': window, 'annotation_count': int(annotated[0]) if annotated else None,
              'unannotated_count': int(unannotated[0]) if unannotated else None,
              'pin_coverage_fraction': coverage, 'minimum_pin_coverage': a.minimum_pin_coverage,
              'pin_coverage_screen_passed': bool(sufficient),
              'tool_command': command, 'source_sha256': {str(x): sha(x) for x in inputs},
              'normalized_vcd_sha256': sha(vcd), 'power_log_sha256': sha(log),
              'power_w': dict(zip(['internal', 'switching', 'leakage', 'total'], map(float, totals[0]))) if valid else None,
              'energy_qualified': False, 'full_model_energy_qualified': False,
              'limitations': ['unannotated pins need classification', 'sampled ' + a.sample_label + ' only',
                              'zero-delay gate VCD omits delay-induced glitches',
                              'all other macros, clocks, controllers, wiring and DDR still need coverage']}
    (a.output / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['tool_completed_with_real_annotation', 'annotation_count', 'unannotated_count', 'power_w']}))
    if not sufficient:
        raise RuntimeError('power analysis failed or pin annotation coverage is incomplete')


if __name__ == '__main__':
    main()
