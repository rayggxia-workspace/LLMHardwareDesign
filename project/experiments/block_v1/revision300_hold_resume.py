"""Resume S/T from verified placement with finite input delay cells.

The synthesis/placement source is unchanged; CTS/route/finish are rerun.
The 5ps optimization target is not an STA exception or acceptance tolerance.
All final setup/hold, electrical, DRC and equivalence gates remain mandatory.
"""
import json
import re
import shutil


def implement(root, out, cpus, run, kind):
    from io_slots import file_sha, slot
    assert cpus == 16 and kind in ('s', 't')
    policy_path = root/'project/experiments/block_v1/revision300-hold-resume.json'
    policy = json.loads(policy_path.read_text())
    assert policy['schema'] == 'revision300-hold-resume/1' and kind in policy['macros']
    assert policy['placement_run'] == 'block-v1-20261028-234'
    assert policy['input_delay_probe_run'] == 'block-v1-20261028-243'
    assert policy['input_delay_stages'] == 24 and policy['hold_optimization_target_ns'] == 0.005
    base = out.parents[2]
    source = base/('block-v1-20261028-234/tasks/revision300-route-'+kind)
    receipt = json.loads((source/'receipt.json').read_text())
    assert receipt['passed'] is False and receipt['mode'] == out.name
    original = json.loads((source/'revision300-native-flow.json').read_text())
    assert file_sha(source/'revision300-native-flow.json') == receipt['outputs']['revision300-native-flow.json']
    assert original['stages'] == ['do-1_synth', 'do-floorplan', 'do-place']
    for name, digest in original['rtl_sha256'].items():
        assert file_sha(root/name) == digest
    # Bind the actual insertion/placement experiment. It grants no macro
    # qualification; production CTS and every final gate still run afresh.
    probe = base/('block-v1-20261028-243/tasks/revision300-input-delay-'+kind)
    pr = json.loads((probe/'receipt.json').read_text())
    assert pr['passed'] is True
    pp = probe/'revision300-input-delay-probe.json'
    assert file_sha(pp) == pr['outputs'][pp.name]
    measured = json.loads(pp.read_text())
    assert measured['stages_per_input'] == 24 and measured['source_unchanged'] is True
    tested_script = (probe/'input-delay.tcl').read_text()
    assert file_sha(probe/'input-delay.tcl') == pr['outputs']['input-delay.tcl']
    start = tested_script.index('set block ')
    stop = tested_script.index('estimate_parasitics -placement', start)
    hook_text = tested_script[start:stop].replace('open input-delay.tsv w', 'open $::env(RESULTS_DIR)/bv1-input-delay.tsv w')
    hook = out/'input-delay.tcl';hook.write_text(hook_text)
    for name in ('pins.json', 'pins.tcl', 'input.sdc'):
        assert file_sha(source/name) == receipt['outputs'][name]
        shutil.copyfile(source/name, out/name)
    assert file_sha(source/'config.mk') == receipt['outputs']['config.mk']
    config = (source/'config.mk').read_text()
    assert config.count('export HOLD_SLACK_MARGIN = 0.020') == 1
    config = config.replace('export HOLD_SLACK_MARGIN = 0.020', 'export HOLD_SLACK_MARGIN = 0.005')
    config += '\nexport PRE_CTS_TCL = '+str(hook)+'\n'
    (out/'config.mk').write_text(config)
    relative = 'flow/results/nangate45/bv1_'+original['top']+'/base'
    results = out/relative;results.mkdir(parents=True)
    copied = {}
    with slot(base):
        for p in (source/relative).iterdir():
            if not p.is_file() or not re.match(r'^[123]_', p.name):
                continue
            digest = file_sha(p)
            assert digest == receipt['outputs'][str(p.relative_to(source))]
            shutil.copyfile(p, results/p.name)
            copied[p.name] = digest
    assert {'3_place.odb', '3_place.sdc', '1_synth_lec.v'} <= set(copied)
    result = dict(original)
    result.update(passed=False, source_placement_task=str(source), source_placement_receipt_sha256=file_sha(source/'receipt.json'),
                  source_function_task=str(source.parent/('revision300-test-'+kind)),
                  inherited_placement_files_sha256=copied, input_delay_probe_receipt_sha256=file_sha(probe/'receipt.json'),
                  input_delay_hook_sha256=file_sha(hook), input_delay_stages=24, resume_policy_sha256=file_sha(policy_path),
                  hold_optimization_target_ns=0.005, previous_hold_optimization_target_ns=0.020,
                  acceptance_policy='Exact original 300MHz SDC, no exceptions/tolerances; every actual final setup/hold slack must remain nonnegative',
                  config_sha256=file_sha(out/'config.mk'), final_files={}, pipeline_completed=False,
                  qualified_hard_macro=False, scope='Verified original RTL/synthesis/placement; new physical input delay cells and fresh CTS/route/finish; independent same-source acceptance pending')
    def save():
        (out/'revision300-native-flow.json').write_text(json.dumps(result, indent=2)+'\n')
    command = ['make', '-C', '/OpenROAD-flow-scripts/flow', 'DESIGN_CONFIG='+str(out/'config.mk'),
               'WORK_HOME='+str(out/'flow'), 'NUM_CORES=16']
    wanted = dict(original['actual_variables'], HOLD_SLACK_MARGIN='0.005', PRE_CTS_TCL=str(hook), SKIP_CTS_REPAIR_TIMING='0')
    result['actual_variables'] = {}
    for name, expected in wanted.items():
        log = 'variable-'+name+'.log';run(command+['print-'+name], log)
        value = re.search(r'(?m)^'+name+r': (.+)$', (out/log).read_text()).group(1).strip()
        assert value == expected, (name, value, expected)
        result['actual_variables'][name] = value
    save()
    for stage in ('do-cts', 'do-route', 'do-finish'):
        run(command+[stage], stage+'.log')
        result['stages'].append(stage);save()
    for suffix in ('v', 'sdc', 'def', 'odb', 'spef'):
        p = results/('6_final.'+suffix)
        assert p.is_file()
        result['final_files'][p.name] = dict(path=str(p), sha256=file_sha(p), bytes=p.stat().st_size)
    assert all(file_sha(source/relative/name) == digest for name, digest in copied.items())
    assert file_sha(source/'receipt.json') == result['source_placement_receipt_sha256']
    result.update(passed=True, pipeline_completed=True);save()
