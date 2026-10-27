"""Run a min/max PRIVATE model probe on an already bound candidate request.

Both models are freshly exported from the same full timing V/SDC/SPEF.
This is a perturbation experiment, not replacement of the published candidate.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import time

from audit import file_sha, require, load_json
from candidate_request import validate_binding
from native_pair import run, verify, tcl_list, native_log_diagnostics, signed_slack_diagnostic


def execute(original_request, executable, min_executable, min_probe_receipt, output):
    original_request, executable, min_executable, min_probe_receipt, output = [Path(p).resolve() for p in
        (original_request, executable, min_executable, min_probe_receipt, output)]
    request = load_json(original_request.read_bytes())
    require(request['evidence_kind'] == 'native-candidate-diagnostic', 'probe requires original candidate diagnostic')
    paths = {r:(original_request.parent/e['path']).resolve() for r,e in request['files'].items()}
    require(all(file_sha(paths[r]) == e['sha256'] for r,e in request['files'].items()), 'probe original input hash')
    original_binding = validate_binding(request, paths)
    proof = load_json(min_probe_receipt.read_bytes())
    require(proof['schema'] == 'block-v1-min-output-probe-build/1' and proof['passed'] is True
            and proof['original_inputs_unchanged'] is True, 'probe private build status')
    require(proof['outputs'][min_executable.name] == file_sha(min_executable)
            and proof['original_inputs'].get(str(executable)) == file_sha(executable), 'probe native tool identity')
    require(not any(output.is_relative_to(p.parent) for p in paths.values()), 'probe output inside inputs')
    output.mkdir(parents=True,exist_ok=False)
    sealed = {str(p):file_sha(p) for p in [original_request,executable,min_executable,min_probe_receipt,*paths.values()]}
    receipt = {'schema':'block-v1-candidate-split-probe/1','passed':False,'started':time.time(),
        'qualified_hard_macro':False,'purpose':'Private perturbation; fresh max AND min from full timing V, not published candidate models',
        'producer_sha256':file_sha(Path(__file__)),'inputs':sealed,'original_candidate_binding':original_binding,
        'export_clock_source_latency':'Explicit zero, matching main native_views.py export; measurement keeps shared original SDC',
        'exports':[]}
    try:
        for analysis, tool in [('max',executable),('min',min_executable)]:
            script = ''.join('read_liberty '+tcl_list([paths[r]])+'\n' for r in sorted(paths) if r.startswith('base_lib_'))
            script += 'read_verilog '+tcl_list([paths['flat_verilog']])+'\nlink_design '+request['flat_top']+'\n'
            script += 'read_sdc '+tcl_list([paths['sdc']])+'\nread_spef '+tcl_list([paths['flat_spef']])+'\n'
            script += 'set_propagated_clock [all_clocks]\nset_clock_latency -source 0 [all_clocks]\n'
            script += 'write_timing_model -library_name QA127_PROBE_'+analysis.upper()+' -cell_name '+request['flat_top']+' '+analysis+'.lib\n'
            script = 'if {[catch {\n'+script+'} problem options]} {puts stderr $problem;puts stderr [dict get $options -errorinfo];exit 1}\nexit 0\n'
            script_path = output/(analysis+'.tcl')
            script_path.write_text(script)
            argv = [str(tool),'-no_init','-exit',str(script_path)]
            with (output/(analysis+'.log')).open('w') as log:
                code = subprocess.run(argv,cwd=output,env=dict(os.environ,OMP_NUM_THREADS='1'),stdout=log,stderr=subprocess.STDOUT).returncode
            diagnostics = native_log_diagnostics(output/(analysis+'.log'))
            receipt['exports'].append({'analysis':analysis,'argv':argv,'returncode':code,'diagnostics':diagnostics,
                'executable_sha256':file_sha(tool),'script_sha256':file_sha(script_path),'model_sha256':file_sha(output/(analysis+'.lib')) if (output/(analysis+'.lib')).exists() else None})
            require(code == 0 and diagnostics['native_error_count'] == 0 and diagnostics['exact_source_annotation_binding_accepted'], 'probe native export context failed')
        derived = deepcopy(request)
        derived['evidence_kind'] = 'native-control'
        derived['macro_delay_model'] = 'split-min-max'
        derived['probe_origin_request_sha256'] = file_sha(original_request)
        derived['probe_original_candidate_binding'] = derived.pop('candidate_binding')
        for role,model in [('macro_lib','max.lib'),('macro_min_lib','min.lib')]:
            derived['files'][role] = {'path':str(output/model),'sha256':file_sha(output/model)}
        request_path = output/'probe-request.json'
        request_path.write_text(json.dumps(derived,indent=2)+'\n')
        measured = output.parent/(output.name+'-measured')
        pair = run(request_path,measured,executable,1)
        binding = verify(measured,request_path)
        observed = [load_json((measured/v/'observed.json').read_bytes()) for v in ['flat','abstract']]
        receipt['measurement'] = {'folder':str(measured),'receipt_sha256':file_sha(measured/'receipt.json'),
            'report_sha256':file_sha(measured/'native-pair-report.json'),'binding':binding,
            'context_accepted':pair['measurement_context_accepted'],'mismatch_count':len(pair['mismatches']),
            'signed_slack':signed_slack_diagnostic(*observed,.001)}
        require(all(file_sha(Path(p)) == h for p,h in sealed.items()), 'probe input changed')
        receipt['passed'] = True
        return receipt
    finally:
        receipt['finished'] = time.time()
        receipt['outputs'] = {p.name:file_sha(p) for p in output.iterdir() if p.is_file() and p.name != 'probe-receipt.json'}
        (output/'probe-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['original-request','executable','min-executable','min-probe-receipt','output']:
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    result=execute(args.original_request,args.executable,args.min_executable,args.min_probe_receipt,args.output)
    print(json.dumps({'passed':result['passed'],'measurement':result.get('measurement')}))
