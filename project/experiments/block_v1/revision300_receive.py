"""Bind revised final sources before independent same-source reception."""
import json
import re
import shutil


def finalize(root, out, cpus, run, kind):
    from io_slots import file_sha, slot
    from constraint_readback import audit
    from constraints import generate
    assert cpus == 16 and kind in 'mvrst'
    selection=json.loads((root/'project/experiments/block_v1/revision300-selected-sources.json').read_text())
    assert selection['schema']=='revision300-selected-sources/1'
    raw = out.parents[2]/selection['native'][kind]
    assert out.parents[2]in raw.resolve().parents and raw.name=='revision300-route-'+kind
    receipt = json.loads((raw/'receipt.json').read_text())
    assert receipt['passed'] is True and receipt['mode'] == 'revision300-route-'+kind
    proof = raw/'revision300-native-flow.json'
    assert file_sha(proof) == receipt['outputs'][proof.name]
    flow = json.loads(proof.read_text())
    assert flow['passed'] is True and flow['pipeline_completed'] is True
    assert flow['stages'] == ['do-1_synth', 'do-floorplan', 'do-place', 'do-cts', 'do-route', 'do-finish']
    for name, digest in flow['rtl_sha256'].items():
        assert file_sha(root/name) == digest
    from revision300_rtl import sources
    top, rtl, bench = sources(root, kind)
    assert top == flow['top']
    tested = raw.parent/('revision300-test-'+kind)
    if 'source_function_task' in flow:
        tested = out.parents[2]/flow['source_function_task']
        assert out.parents[2] in tested.resolve().parents and tested.name == 'revision300-test-'+kind
    tr = json.loads((tested/'receipt.json').read_text())
    assert tr['passed']is True and file_sha(tested/'receipt.json') == flow['source_function_receipt_sha256']
    tp = tested/'revision300-rtl-test.json'
    assert file_sha(tp) == tr['outputs'][tp.name]
    functional = json.loads(tp.read_text())
    assert functional['passed']is True and functional['bench_sha256'] == file_sha(bench)
    assert functional['rtl_sha256'] == flow['rtl_sha256']
    flow['bench_sha256'] = file_sha(bench)
    folder = root/'project/experiments/block_v1'
    budget = json.loads((folder/'physical-budget-300mhz.json').read_text())
    assert flow['budget'] == budget
    relative = 'flow/results/nangate45/bv1_'+flow['top']+'/base'
    results = out/relative;results.mkdir(parents=True)
    raw_results = raw/relative
    for name in ['config.mk', 'pins.json', 'pins.tcl', 'input.sdc']:
        assert file_sha(raw/name) == receipt['outputs'][name]
        shutil.copyfile(raw/name, out/name)
    approved = re.sub(r'create_clock -name core -period [^ ]+',
                      'create_clock -name core -period %.12g'%budget['clock_ns'], generate(budget))
    assert (out/'input.sdc').read_text() == approved
    # ORFS serializes four decimals between stages. Its rounded-down period is
    # stricter than the approved target. Preserve it as provenance, then freeze
    # a new source package at the exact approved contract BEFORE fresh gates.
    legacy_budget = dict(budget, clock_ns=3.3333)
    original_sdc = (raw_results/'6_final.sdc').read_text()
    raw_boundary = audit(original_sdc, json.loads((out/'pins.json').read_text())['pins'], legacy_budget)
    assert legacy_budget['clock_ns'] < budget['clock_ns']
    bound = {}
    for name in ['6_final.v', '6_final.sdc', '6_final.def', '6_final.odb', '6_final.spef', '1_synth_lec.v', 'bv1-input-diodes.tsv']:
        p = raw_results/name
        assert file_sha(p) == receipt['outputs'][str(p.relative_to(raw))]
        if name.startswith('6_final.'):
            assert file_sha(p) == flow['final_files'][name]['sha256']
        bound[name] = dict(path=str(p), sha256=file_sha(p), bytes=p.stat().st_size)
        with slot(out.parents[2]):
            shutil.copyfile(p, results/name)
    (out/'original-flow-final.sdc').write_text(original_sdc)
    (results/'6_final.sdc').write_text(approved)
    flow['final_files'] = {name:dict(path=str(results/name), sha256=file_sha(results/name), bytes=(results/name).stat().st_size)
                           for name in flow['final_files']}
    flow.update(source_native_receipt_sha256=file_sha(raw/'receipt.json'), raw_source=str(raw),
                raw_final_files=bound, original_flow_boundary=raw_boundary,
                final_sdc_policy='Approved input SDC re-frozen before independent acceptance; raw flow used stricter 3.3333ns period; all other final files byte-identical',
                independent_reception_completed=False, qualified_hard_macro=False)
    assert all(file_sha(raw_results/name) == row['sha256'] for name, row in bound.items())
    (out/'revision300-final-source.json').write_text(json.dumps(flow, indent=2)+'\n')


def source(root, out, kind):
    from io_slots import file_sha
    selection=json.loads((root/'project/experiments/block_v1/revision300-selected-sources.json').read_text())
    assert selection['schema']=='revision300-selected-sources/1'
    relative=selection['macros'][kind];assert relative,'No selected revised final source'
    folder = out.parents[2]/relative
    assert out.parents[2]in folder.resolve().parents and folder.name=='revision300-final-source-'+kind
    receipt = json.loads((folder/'receipt.json').read_text())
    assert receipt['passed'] is True and receipt['mode'] == folder.name
    path = folder/'revision300-final-source.json'
    assert file_sha(path) == receipt['outputs'][path.name]
    flow = json.loads(path.read_text())
    assert flow['passed'] is True and flow['pipeline_completed'] is True
    assert flow['independent_reception_completed'] is False and flow['qualified_hard_macro'] is False
    for name, digest in flow['rtl_sha256'].items():
        assert file_sha(root/name) == digest
    from revision300_rtl import sources
    assert file_sha(sources(root, kind)[2]) == flow['bench_sha256']
    results = folder/'flow/results/nangate45'/('bv1_'+flow['top'])/'base'
    for name, row in flow['final_files'].items():
        assert file_sha(results/name) == row['sha256'] == receipt['outputs'][str((results/name).relative_to(folder))]
    for name, field in [('config.mk', 'config_sha256'), ('pins.json', 'pins_sha256')]:
        assert file_sha(folder/name) == flow[field] == receipt['outputs'][name]
    assert flow['budget'] == json.loads((root/'project/experiments/block_v1/physical-budget-300mhz.json').read_text())
    return folder, receipt, flow, results


def receive(root, out, cpus, run, operation, kind):
    from five_macro_receive import physical, drc, function, formal
    selected = lambda target, macro: source(root, target, macro)
    if operation == 'physical':
        physical(root, out, cpus, run, kind, selected=selected)
    elif operation == 'drc':
        drc(root, out, cpus, run, kind, selected=selected)
    elif operation == 'function':
        function(root, out, cpus, run, kind, selected=selected)
    elif operation == 'formal':
        formal(root, out, cpus, run, kind, selected=selected,
               function_folder=out.parent/('revision300-final-function-'+kind))
    else:
        raise ValueError(operation)
