"""Native small control: expose output RC separately from a core timing model.

This partitions a known DFF example, not an automatic real-block exporter.
The physical block/pins are not changed; only a timing representation is tested.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import time

from audit import require, file_sha
from native_control import probe_spef
from native_pair import run, verify, native_log_diagnostics, tcl_list
from output_path_control import scenario_sdc


def partition(full):
    marker = '*D_NET q 2\n'
    require(full.count(marker) == 1, 'known q partition marker')
    prefix, tail = full.split(marker)
    require(tail.startswith('*CONN\n*P q O\n*I ff:Q O\n*CAP\n1 q 1\n2 ff:Q 1\n*RES\n1 q ff:Q ')
            and tail.endswith('\n*END\n') and tail.count('*END') == 1, 'known q partition topology')
    resistance = float(tail.split('1 q ff:Q ', 1)[1].splitlines()[0])
    require(full == probe_spef(1, resistance) or full == probe_spef(1, int(resistance)), 'known full source topology')
    core = prefix+'*D_NET q 0\n*CONN\n*P q O\n*I ff:Q O\n*CAP\n1 q 0\n2 ff:Q 0\n*RES\n1 q ff:Q 0\n*END\n'
    parent_header = prefix.split('*D_NET ', 1)[0].replace('*DESIGN "qa_probe"', '*DESIGN "qa_wrapper"')
    parent = parent_header+marker+tail.replace('ff:Q', 'macro0:q')
    return core, parent


def validate_partition(full, core, parent):
    expected = partition(full)
    require((core, parent) == expected, 'output RC partition changed or double-counted')
    return {'passed': True, 'source_output_capacitance_ff': 2,
        'core_output_wire_capacitance_ff': 0, 'core_output_wire_resistance_ohm': 0,
        'parent_output_capacitance_ff': 2,
        'scope': 'Exact known two-node q network, including both capacitances and resistor; clock/data networks retained byte-for-byte in core'}


def output_difference(folder):
    views = [json.loads((folder/view/'observed.json').read_text()) for view in ('flat', 'abstract')]
    indexed = [{tuple(row['key']): row for row in v['observations'] if row['key'][0] == 'output'} for v in views]
    deltas = [{'key': list(key), 'abstract_minus_flat_slack_ps': 1000*(indexed[1][key]['slack_ns']-row['slack_ns'])}
              for key, row in indexed[0].items()]
    a, b = [v['ports']['q']['slew_ns'] for v in views]
    return {'output_slack': deltas, 'maximum_absolute_slack_difference_ps': max(abs(r['abstract_minus_flat_slack_ps']) for r in deltas),
        'maximum_absolute_slew_difference_ps': max(abs(x-y)*1000 for x,y in zip(a,b)),
        'flat_output_slew_ns': a, 'abstract_output_slew_ns': b,
        'qualified_hard_macro': False, 'scope': 'Output aggregate/port-slew diagnostic; whole-pair input failures remain visible'}


def execute(executable, library, output):
    executable, library, output = [Path(p).resolve() for p in (executable, library, output)]
    require(not output.is_relative_to(executable.parent) and not output.is_relative_to(library.parent), 'control output overlap')
    originals = {p: file_sha(p) for p in [executable, library, Path(__file__),
        *[Path(__file__).with_name(name) for name in ('native_control.py','native_pair.py','output_path_control.py','audit.py','spef_inventory.py')]]}
    output.mkdir(parents=True, exist_ok=False)
    (output/'producer.py').write_bytes(Path(__file__).read_bytes())
    receipt = {'schema': 'block-v1-explicit-output-rc-control/1', 'passed': False, 'started': time.time(),
        'qualified_hard_macro': False, 'flat_abstract_boundary_qualified': False,
        'inputs': {str(p): sha for p, sha in originals.items()}, 'exports': [], 'cases': [], 'exact_rereads': [],
        'scope': 'Known DFF output RC partition; no actual T6K/C8 view change, physical pin move, new source qualification or general extraction proof'}
    try:
        for resistance in (1, 20000):
            folder = output/('r'+str(resistance)); folder.mkdir()
            full = probe_spef(1, resistance)
            core, parent = partition(full)
            partition_proof = validate_partition(full, core, parent)
            flat = 'module qa_probe(input clk,d,output q); DFF_X1 ff(.CK(clk),.D(d),.Q(q)); endmodule\n'
            wrapper = 'module qa_wrapper(input clk,d,output q); QA127_MACRO macro0(.clk(clk),.d(d),.q(q)); endmodule\n'
            for name, value in [('flat.v', flat), ('wrapper.v', wrapper), ('full.spef', full), ('core.spef', core), ('parent.spef', parent),
                ('whole-export.sdc', scenario_sdc('BUF_X2', 2)), ('core-export.sdc', scenario_sdc('BUF_X2', 0))]:
                (folder/name).write_text(value)
            for mode, spef in [('whole', 'full.spef'), ('core', 'core.spef')]:
                script = '\n'.join(['read_liberty '+tcl_list([library]), 'read_verilog flat.v', 'link_design qa_probe',
                    'read_sdc '+mode+'-export.sdc', 'read_spef '+spef, 'set_propagated_clock [all_clocks]',
                    f'write_timing_model -library_name QA127_{mode}_{resistance} -cell_name QA127_MACRO {mode}.lib'])
                script = 'if {[catch {\n'+script+'\n} problem options]} {puts stderr $problem;puts stderr [dict get $options -errorinfo];exit 1}\nexit 0\n'
                (folder/(mode+'.tcl')).write_text(script)
                argv = [str(executable), '-no_init', '-exit', mode+'.tcl']
                with (folder/(mode+'.log')).open('w') as log:
                    code = subprocess.run(argv, cwd=folder, env=dict(os.environ, OMP_NUM_THREADS='1'), stdout=log, stderr=subprocess.STDOUT).returncode
                diagnostics = native_log_diagnostics(folder/(mode+'.log'))
                require(code == 0 and diagnostics['native_error_count'] == 0 and diagnostics['exact_source_annotation_binding_accepted'], 'partition export failed')
                receipt['exports'].append({'resistance_ohm': resistance, 'mode': mode, 'argv': argv, 'returncode': code,
                    'diagnostics': diagnostics, 'partition': partition_proof,
                    'files': {str(folder/n): file_sha(folder/n) for n in [mode+'.tcl', mode+'.log', mode+'.lib', spef, mode+'-export.sdc', 'flat.v']}})
            for load in (0, 2, 10):
                sdc = folder/f'load{load}.sdc'; sdc.write_text(scenario_sdc('BUF_X2', load))
                for mode in ('whole', 'core'):
                    files = {'base_lib_0': library, 'flat_verilog': folder/'flat.v', 'flat_spef': folder/'full.spef',
                        'abstract_verilog': folder/'wrapper.v', 'macro_lib': folder/(mode+'.lib'), 'sdc': sdc}
                    if mode == 'core': files['abstract_spef'] = folder/'parent.spef'
                    request = {'schema': 'block-v1-native-boundary-request/1', 'evidence_kind': 'native-control',
                        'flat_top': 'qa_probe', 'abstract_top': 'qa_wrapper',
                        'abstract_parent_interconnect': 'explicit-spef' if mode == 'core' else 'ideal',
                        'expected_ports': {'clk': 'input', 'd': 'input', 'q': 'output'},
                        'time_tolerance_ns': .001, 'slew_tolerance_ns': .001,
                        'files': {r: {'path': str(p), 'sha256': file_sha(p)} for r,p in files.items()}}
                    request_path = folder/f'{mode}-load{load}-request.json'; request_path.write_text(json.dumps(request,indent=2)+'\n')
                    pair_folder = output/f'r{resistance}-{mode}-load{load}'
                    result = run(request_path, pair_folder, executable, 1)
                    binding = verify(pair_folder, request_path)
                    receipt['cases'].append({'resistance_ohm': resistance, 'output_load_ff': load, 'mode': mode,
                        'pair_result': result, 'binding': binding, 'output': output_difference(pair_folder),
                        'request_sha256': file_sha(request_path), 'receipt': json.loads((pair_folder/'receipt.json').read_text())})
            same = deepcopy(request)
            same['abstract_top'] = 'qa_probe'; same['abstract_parent_interconnect'] = 'explicit-spef'
            same['files']['abstract_verilog'] = same['files']['flat_verilog']
            same['files']['abstract_spef'] = same['files']['flat_spef']
            same_path = folder/'exact-request.json'; same_path.write_text(json.dumps(same,indent=2)+'\n')
            same_folder = output/f'r{resistance}-exact'
            result = run(same_path, same_folder, executable, 1)
            require(result['passed'], 'partition exact reread failed')
            receipt['exact_rereads'].append(verify(same_folder, same_path))
        require(all(file_sha(p) == sha for p,sha in originals.items()), 'partition original inputs changed')
        receipt['passed'] = True
        return receipt
    finally:
        receipt['finished'] = time.time()
        receipt['outputs'] = {str(p.relative_to(output)): file_sha(p) for p in output.rglob('*') if p.is_file() and p != output/'report.json'}
        (output/'report.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('executable', 'library', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); result = execute(args.executable, args.library, args.output)
    print(json.dumps({'passed': result['passed'], 'cases': len(result['cases'])}))
