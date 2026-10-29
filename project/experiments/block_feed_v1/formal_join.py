"""Receive a completed native LEC computation and a successful final simulation.

The producer may have failed only its later function-receipt join. Never reuse
its overall acceptance: inspect every completed command, graph proof and exact
input byte, rerun the real controls, and require the successful function here.
"""
import concurrent.futures
import json
from pathlib import Path
import shutil

from io_slots import file_sha as sha


def join(root, folder, out, run, function, computation):
    from qualify import source, LIB
    from native_formal import inspect, fixture
    from native_projection_control import verify as projection
    folder, source_receipt, flow, results = source(folder)
    top = flow['top']
    producer = json.loads((computation/'receipt.json').read_text())
    assert producer['operation'] == 'formal'
    original,original_receipt,original_flow,original_results=source(Path(producer['source']))
    assert original_flow['top']==top and original_flow['rtl_sha256']==flow['rtl_sha256']
    assert sha(original_results/'1_synth_lec.v')==sha(results/'1_synth_lec.v')
    assert len(producer['commands']) >= 5 and all(c['returncode'] == 0 for c in producer['commands'])
    assert 'formal.json' not in producer['outputs'] or producer['passed']

    # Validate original immutable code and every original output, including the
    # complete graph files. This receives successful computation, not a failed
    # candidate's final qualification.
    producer_root = computation.parents[1]
    manifest = json.loads((producer_root/'source-manifest.json').read_text())
    def check(row):
        path, digest = row
        assert sha(path) == digest, str(path)
    rows = [(producer_root/p, h) for p,h in producer['inputs'].items()]
    rows += [(computation/p, h) for p,h in producer['outputs'].items()]
    rows += [(producer_root/p, h) for p,h in manifest['files'].items()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(check, rows))
    helpers = ['native_formal.py', 'native_logic_projection.py', 'native_tie_projection.py',
               'native_projection_control.py', 'native_cell_gate.py', 'structural_view.py']
    for name in helpers:
        p = 'project/experiments/block_v1/'+name
        assert producer['inputs'][p] == sha(root/p)

    binary = Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    expected = [[str(binary),'--config',str(computation/'kepler.yml')]]
    assert producer['commands'][-1]['command'] == expected[0]
    assert producer['commands'][-1]['log'] == 'formal.log'
    for command in producer['commands']:
        assert sha(computation/command['log']) == command['sha256']
    config = 'format: verilog\ninput_paths:\n  - '+str(computation/'before-logic.v')+'\n  - '+str(computation/'after-logic.v')+'\nliberty_files:\n - '+str(LIB)+'\nlog_file: '+str(computation/'kepler.log')+'\n'
    assert (computation/'kepler.yml').read_text() == config
    native = inspect((computation/'kepler.log').read_text())
    assert native['passed'] and all(native['checks'].values())
    proofs = {}
    for name in ('before','after'):
        proof = json.loads((computation/(name+'-logic-proof.json')).read_text())
        assert proof['passed'] and proof['exact_inverse_reconstruction']
        assert proof['emitted_structural_proof']['passed'] and proof['used_model_audit']['passed']
        assert proof['liberty_sha256'] == sha(LIB)
        assert proof['logic_netlist_sha256'] == sha(computation/(name+'-logic.v'))
        assert proof['projected_graph_sha256'] == proof['constant_functions']['original_graph_sha256']
        assert proof['constant_functions']['passed'] and proof['constant_functions']['exact_inverse_reconstruction']
        proofs[name] = proof
    assert proofs['before']['removed_count'] == 0 and proofs['after']['removed_count'] > 0
    assert proofs['before']['full_netlist_sha256'] == sha(results/'1_synth_lec.v')

    fr = json.loads((function/'receipt.json').read_text()); assert fr['passed']
    f = function/'final-function.json'; assert sha(f) == fr['outputs'][f.name]
    fn = json.loads(f.read_text()); assert fn['passed'] and len(fn['initial_runs']) == 3
    assert all(v['result']['passed'] for v in fn['initial_runs'].values())
    assert fn['top'] == top and fn['source_receipt_sha256'] == sha(folder/'receipt.json')
    assert fn['library_sha256'] == sha(LIB)
    view = fn['full_final_netlist']; actual = Path(view['full_view'])
    view_file = function/'physical-functional-proof.json'
    assert sha(view_file) == fr['outputs'][view_file.name] and json.loads(view_file.read_text()) == view
    assert actual == function/'physical-functional.v'
    assert sha(actual) == view['full_view_sha256'] == fr['outputs'][str(actual.relative_to(function))]
    assert proofs['after']['full_netlist_sha256'] == sha(actual)
    assert view['input_sha256'] == {str(results/n):flow['final_files'][n]['sha256'] for n in ('6_final.odb','6_final.v')}

    controls = out/'controls'; controls.mkdir(); (controls/'lec').mkdir()
    fixture(root,controls/'lec',run)
    for polarity in (0,1):
        p=controls/str(polarity);p.mkdir()
        projection(root,p,1,lambda cmd,log:run(cmd,'control-'+str(polarity)+'-'+log),polarity)
    control = json.loads((controls/'lec/native-formal-control.json').read_text())
    assert control['passed'] and control['binary_sha256'] == sha(binary)
    original_control = json.loads((computation/'controls/lec/native-formal-control.json').read_text())
    assert original_control['passed'] and original_control['binary_sha256'] == sha(binary)
    assert original_control['liberty_sha256'] == sha(LIB)

    for name in ('kepler.log','before-logic-proof.json','after-logic-proof.json'):
        shutil.copyfile(computation/name,out/name); assert sha(out/name) == producer['outputs'][name]
    shutil.copyfile(computation/'receipt.json',out/'computation-receipt.json')
    result = dict(passed=True,top=top,strict_native_lec=native,before=proofs['before'],after=proofs['after'],
        source_receipt_sha256=sha(folder/'receipt.json'),function_receipt_sha256=sha(function/'receipt.json'),
        log_sha256=sha(out/'kepler.log'),binary_sha256=sha(binary),qualified_hard_macro=False,
        computation=dict(receipt=str(computation/'receipt.json'),receipt_sha256=sha(computation/'receipt.json'),
            original_source=str(original),received_source=str(folder),original_rtl_sha256=original_flow['rtl_sha256'],
            exact_synth_lec_sha256=sha(results/'1_synth_lec.v'),
            source_commit=manifest['source_commit'],producer_passed=producer['passed'],
            all_native_commands_successful=True,all_original_outputs_rehashed=True,
            exact_functional_view_sha256=sha(actual),fresh_real_controls_passed=True),
        scope='Fresh reception of successful native LEC substage plus successful three-state final simulation on the identical physical view; failed late producer join is preserved and does not transfer overall acceptance.')
    (out/'formal.json').write_text(json.dumps(result,indent=2)+'\n')
