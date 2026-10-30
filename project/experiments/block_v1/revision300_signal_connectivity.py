"""Bind whole-signal geometry proof to the selected immutable final package."""
import json


def prove(root, out, cpus, run, kind):
    from io_slots import file_sha
    from revision300_receive import source
    from signal_connectivity import audit, controls
    assert cpus == 16 and kind == 'v'
    folder, receipt, flow, results = source(root, out, kind)
    assert folder.name == 'revision300-final-source-v'
    selection = json.loads((root/'project/experiments/block_v1/revision300-selected-sources.json').read_text())
    assert folder == out.parents[2]/selection['macros']['v']
    inputs = {name: file_sha(results/name) for name in ('6_final.odb', '6_final.def')}
    for name, digest in inputs.items():
        assert digest == flow['final_files'][name]['sha256']
    proof = dict(passed=False, source_task=str(folder), source_receipt_sha256=file_sha(folder/'receipt.json'),
                 source_report_sha256=file_sha(folder/'revision300-final-source.json'),
                 actual_input_sha256=inputs, controls=controls(), cpus=cpus)
    def save():
        (out/'revision300-signal-connectivity.json').write_text(json.dumps(proof, indent=2)+'\n')
    save()
    helper = root/'project/experiments/block_v1'
    script = 'set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\n'
    script += 'set ::env(BV1_GEOMETRY_SOURCE) {'+str(helper/'odb_geometry.tcl')+'}\n'
    script += 'source {'+str(helper/'signal_connectivity.tcl')+'}\n'
    script += 'signal_connectivity_export {signal-geometry.tsv}\n'
    (out/'signal-connectivity.tcl').write_text(script)
    geometry = out/'signal-geometry.tsv'
    if out.name == 'revision300-signal-connectivity-audit-v':
        assert folder.parent.parent.name == 'block-v1-20261031-767'
        previous = out.parents[2]/'block-v1-20261031-776/tasks/revision300-signal-connectivity-v'
        failed = json.loads((previous/'receipt.json').read_text())
        assert failed['passed'] is False and failed['mode'] == previous.name
        assert failed['error'] == "AssertionError('Incomplete DEF net coverage')"
        prior_report = previous/'revision300-signal-connectivity.json'
        assert file_sha(prior_report) == failed['outputs'][prior_report.name]
        old = json.loads(prior_report.read_text())
        assert old['source_receipt_sha256'] == proof['source_receipt_sha256']
        assert old['actual_input_sha256'] == inputs
        commands = failed['commands']
        assert len(commands) == 1 and commands[0]['argv'][0] == 'openroad' and commands[0]['returncode'] == 0
        for name in ('signal_connectivity.tcl', 'odb_geometry.tcl'):
            relative = 'project/experiments/block_v1/'+name
            assert failed['inputs'][relative] == file_sha(helper/name)
        geometry = previous/'signal-geometry.tsv'
        assert file_sha(geometry) == old['geometry_sha256'] == failed['outputs'][geometry.name]
        proof['read_only_audit'] = dict(original_failed_task=str(previous),
            original_failed_receipt_sha256=file_sha(previous/'receipt.json'),
            original_actual_openroad_command=commands[0], eda_rerun=False,
            original_geometry_sha256=file_sha(geometry))
        save()
    else:
        assert out.name == 'revision300-signal-connectivity-v'
        run(['openroad', '-no_init', '-exit', out/'signal-connectivity.tcl'], 'signal-export.log')
    # Validate actual exported tech layer semantics before interpreting contacts.
    layers = {}
    with geometry.open() as stream:
        assert stream.readline().strip() == '# SIGNAL-CONNECTIVITY 1 DBU 2000'
        for line in stream:
            if line.startswith('# NET '):
                break
            if line.startswith('# SKIP '):
                continue
            assert line.startswith('# LAYER ')
            _, _, name, typ, level = line.split()
            layers[name] = (typ, int(level))
    for i in range(1, 11):
        assert layers['metal'+str(i)] == ('ROUTING', i)
    for i in range(1, 10):
        assert layers['via'+str(i)][0] == 'CUT'
    proof.update(geometry_path=str(geometry), geometry_sha256=file_sha(geometry),
                 geometry_bytes=geometry.stat().st_size, exported_technology_layers=layers)
    save()
    proof['connectivity'] = audit(geometry, results/'6_final.def', out/'signal-net-results.jsonl.gz', cpus)
    proof['results_sha256'] = file_sha(out/'signal-net-results.jsonl.gz')
    proof['original_inputs_unchanged'] = all(file_sha(results/n) == h for n, h in inputs.items())
    proof['passed'] = proof['connectivity']['passed'] and proof['original_inputs_unchanged']
    save()
    assert proof['passed'], 'Actual routed geometry is disconnected; see signal-net-results and report'
