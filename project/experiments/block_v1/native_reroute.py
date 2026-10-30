"""Repeat standard route/final with stricter cap/optional hold repair targets.

This is prefabrication repair, charged to the same native budgets. It neither
changes Liberty limits nor mutates the original candidate or the fixed plan.
"""
import json
from pathlib import Path
import re
import shutil
from io_slots import slot, file_sha


PIPELINE = 'native_pipeline_cap20.json'
SUFFIX = '\nexport CAP_MARGIN = 20\n'
VIA_ONLY_ARGS='-via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5 -via_access_layer metal10'


def config_suffix(margin,hold_margin=None,diode_hook=None,via_access_layer=None):
    assert margin in (20,40)
    suffix='\nexport CAP_MARGIN = %d\n'%margin
    if hold_margin is not None:
        assert margin==40 and hold_margin==.005
        suffix+='export HOLD_SLACK_MARGIN = 0.005\n'
    if diode_hook is not None:
        assert margin==40 and hold_margin==.005
        assert Path(diode_hook).is_absolute() and not re.search(r'[\s$#]',str(diode_hook))
        suffix+='export PRE_GLOBAL_ROUTE_TCL = '+str(diode_hook)+'\n'
        suffix+='export VIA_IN_PIN_MIN_LAYER = metal10\nexport VIA_IN_PIN_MAX_LAYER = metal10\n'
    if via_access_layer is not None:
        assert via_access_layer=='metal10'and diode_hook is not None
        suffix+='export DETAILED_ROUTE_ARGS = '+VIA_ONLY_ARGS+'\n'
    return suffix


def variant(margin,hold_margin=None,diode=False,via_access_layer=None):
    if via_access_layer is not None:
        assert via_access_layer=='metal10'and diode and margin==40 and hold_margin==.005
        return 'cap40-hold5ps-input-diode-via-only-m10-from-sealed-cts'
    config_suffix(margin,hold_margin)
    if diode:
        assert margin==40 and hold_margin==.005
        return 'cap40-hold5ps-input-diode-via-in-m10-from-sealed-cts'
    return 'cap40-hold5ps-from-sealed-cts'if hold_margin is not None else 'cap-margin-%d-from-sealed-cts'%margin


def checked_config(source, receipt, original,margin=20,hold_margin=None,diode=False,via_access_layer=None):
    """Bind actual configuration to the original plus exact repair targets."""
    path = source / 'config.mk'
    assert file_sha(path) == receipt['outputs']['config.mk']
    hook=source/'input-diodes.tcl'if diode else None
    if diode:assert file_sha(hook)==receipt['outputs'][hook.name]
    assert path.read_bytes() == original.read_bytes() + config_suffix(margin,hold_margin,hook,via_access_layer).encode()
    record = source / 'native-candidate.json'
    assert file_sha(record) == receipt['outputs'][record.name]
    candidate = json.loads(record.read_text())
    assert candidate['repair_variant'] == variant(margin,hold_margin,diode,via_access_layer)
    assert candidate['actual_variables']['CAP_MARGIN'] == str(margin)
    if hold_margin is not None:
        assert candidate['actual_variables']['HOLD_SLACK_MARGIN']=='0.005'
        assert candidate['hold_margin_ns']==hold_margin
    assert candidate['actual_variables']['LEC_CHECK'] == '1'
    assert candidate['actual_variables']['SEC_CHECK'] == '0'
    if diode:
        assert candidate['actual_variables']['PRE_GLOBAL_ROUTE_TCL']==str(hook)
        assert candidate['actual_variables']['VIA_IN_PIN_MIN_LAYER']==candidate['actual_variables']['VIA_IN_PIN_MAX_LAYER']=='metal10'
    if via_access_layer is not None:
        assert candidate['actual_variables']['DETAILED_ROUTE_ARGS']==VIA_ONLY_ARGS
        assert candidate['actual_detailed_route_commands']and all(command.endswith(VIA_ONLY_ARGS)for command in candidate['actual_detailed_route_commands'])
    assert candidate['actual_config_sha256'] == file_sha(path)
    return path


def implement(root, out, cpus, run, top, policy,pipeline=PIPELINE):
    assert top in ('shared109', 'transaction6k') and policy in ('A', 'C') and cpus >= 16
    assert pipeline in ('native_pipeline_cap20.json','native_pipeline_cap40.json','native_pipeline_hold5.json','native_pipeline_diode.json','native_pipeline_viaonly.json')
    config = json.loads((root / 'project/experiments/block_v1' / pipeline).read_text())
    margin=config.get('cap_margin',20)
    assert margin==(20 if pipeline=='native_pipeline_cap20.json'else 40)
    hold_margin=config.get('hold_margin_ns')
    diode=pipeline in ('native_pipeline_diode.json','native_pipeline_viaonly.json')
    via_access_layer=config.get('via_access_layer')
    assert (via_access_layer=='metal10')==(pipeline=='native_pipeline_viaonly.json')
    if via_access_layer:assert top=='transaction6k'
    assert hold_margin==(.005 if pipeline in ('native_pipeline_hold5.json','native_pipeline_diode.json','native_pipeline_viaonly.json')else None)
    assert config['repair_variant']==variant(margin,hold_margin,diode,via_access_layer)
    base = out.parents[2]
    if diode:
        proof=base/'block-v1-20261027-110/tasks/native-antenna-fixture'
        bound=json.loads((proof/'receipt.json').read_text());assert bound['passed']is True
        path=proof/'native-antenna-fixture.json';assert file_sha(path)==bound['outputs'][path.name]
        qualified=json.loads(path.read_text());assert qualified['passed']is True and qualified['formal']['passed']is True
        hook_probe=base/'block-v1-20261027-113/tasks/native-diode-hook-probe'
        hook_receipt=json.loads((hook_probe/'receipt.json').read_text());assert hook_receipt['passed']is True
        hook_path=hook_probe/'native-diode-hook.json';assert file_sha(hook_path)==hook_receipt['outputs'][hook_path.name]
        assert json.loads(hook_path.read_text())['passed']is True
        assert hook_receipt['inputs']['project/experiments/block_v1/native_input_diodes.tcl']==file_sha(root/'project/experiments/block_v1/native_input_diodes.tcl')
        hook=out/'input-diodes.tcl';shutil.copyfile(root/'project/experiments/block_v1/native_input_diodes.tcl',hook)
    else:hook=None
    via_probe_binding=None
    if via_access_layer:
        probe=base/'block-v1-20261027-132/tasks/native-pin-access-probe'
        probe_receipt=json.loads((probe/'receipt.json').read_text());assert probe_receipt['passed']is True
        path=probe/'native-pin-access-probe.json';assert file_sha(path)==probe_receipt['outputs'][path.name]
        measured=json.loads(path.read_text());assert measured['passed']is True
        assert [case['mode']for case in measured['cases']]==['baseline','via-only']and all(case['pin_access_viable']for case in measured['cases'])
        script=Path('/OpenROAD-flow-scripts/flow/scripts/detail_route.tcl')
        assert file_sha(script)==measured['actual_flow_scripts'][script.name]['sha256']=='a21fd34d5104533a865f2e138c9fed546416ac6a37b1457baa8c0715537e0ba0'
        # This installed script REPLACES additional_args when the override is
        # set. Preserve every previously measured default, not just the new flag.
        prior=base/'block-v1-20261027-111/tasks/native-diode-run-transaction6k-a'
        prior_receipt=json.loads((prior/'receipt.json').read_text());assert prior_receipt['passed']is True
        route_log=prior/'do-route.log';assert file_sha(route_log)==prior_receipt['outputs'][route_log.name]
        commands=re.findall(r'(?m)^detailed_route .+$',route_log.read_text());assert commands
        baseline_args=VIA_ONLY_ARGS.removesuffix(' -via_access_layer metal10')
        assert all(command.endswith(baseline_args)for command in commands)
        via_probe_binding=dict(receipt_sha256=file_sha(probe/'receipt.json'),report_sha256=file_sha(path),
                               installed_route_script_sha256=file_sha(script),prior_route_log_sha256=file_sha(route_log),
                               prior_default_args=baseline_args,detail_route_args=VIA_ONLY_ARGS,
                               measured_pin_access_policy='A',current_policy=policy,
                               scope='A actual option viability and installed script binding; current candidate still requires complete actual route and independent acceptance')
    source = base / config['source_candidate_run'] / ('tasks/native-run-' + top + '-' + policy.lower())
    receipt = json.loads((source / 'receipt.json').read_text())
    assert receipt['passed'] is True
    record_path = source / 'native-candidate.json'
    assert file_sha(record_path) == receipt['outputs'][record_path.name]
    original_record = json.loads(record_path.read_text())
    assert original_record['pipeline_completed'] is True
    prep = base / config['preparation_run'] / 'tasks/native-prepare'
    accepted = json.loads((prep / 'receipt.json').read_text())
    assert accepted['passed'] is True
    original_config = prep / (top + '-' + policy) / 'config.mk'
    assert file_sha(original_config) == accepted['outputs'][str(original_config.relative_to(prep))]
    assert original_record['inputs_receipt_sha256'] == file_sha(prep / 'receipt.json')
    folder = out / 'config.mk'
    folder.write_bytes(original_config.read_bytes() + config_suffix(margin,hold_margin,hook,via_access_layer).encode())
    nickname = 'bv1_' + top + '_' + policy
    relative = Path('flow/results/nangate45') / nickname / 'base'
    results = out / relative
    results.mkdir(parents=True)
    copied = {}
    with slot(base):
        for path in sorted((source / relative).iterdir()):
            if not path.is_file() or not re.match(r'^[1-4]_', path.name):
                continue
            digest = file_sha(path)
            assert digest == receipt['outputs'][str(path.relative_to(source))]
            target = results / path.name
            shutil.copyfile(path, target)
            target.chmod(0o444)
            assert file_sha(target) == digest
            copied[path.name] = digest
    assert {'4_cts.odb', '4_cts.sdc', '1_synth_lec.v', '1_2_yosys.v', '1_2_yosys.sdc'} <= set(copied)
    record = dict(schema='block-v1-native-candidate/1', top=top, policy=policy, cpus=cpus,
        inputs_source=str(prep), inputs_receipt_sha256=file_sha(prep / 'receipt.json'),
        source=str(source), source_receipt_sha256=file_sha(source / 'receipt.json'),
        source_candidate_sha256=file_sha(record_path), copied_checkpoint_files=copied,
        repair_variant=variant(margin,hold_margin,diode,via_access_layer),hold_margin_ns=hold_margin,via_probe_binding=via_probe_binding,
        actual_config=str(folder), actual_config_sha256=file_sha(folder), stages=[],
        qualified_hard_macro=False,
        scope='Native prefabrication route/final repair; all original electrical limits, area budgets and independent gates still apply')
    def save():
        (out / 'native-candidate.json').write_text(json.dumps(record, indent=2) + '\n')
    save()
    command = ['make', '-C', '/OpenROAD-flow-scripts/flow', 'DESIGN_CONFIG=' + str(folder),
               'WORK_HOME=' + str(out / 'flow'), 'NUM_CORES=' + str(cpus)]
    wanted = dict(TECH_LEF='/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef',
        MAX_ROUTING_LAYER='metal10', MIN_ROUTING_LAYER='metal1',
        RCX_RULES='/OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules',
        KEEP_VARS='1', LEC_CHECK='1', SEC_CHECK='0', CAP_MARGIN=str(margin))
    if hold_margin is not None:wanted['HOLD_SLACK_MARGIN']='0.005'
    if diode:wanted.update(PRE_GLOBAL_ROUTE_TCL=str(hook),VIA_IN_PIN_MIN_LAYER='metal10',VIA_IN_PIN_MAX_LAYER='metal10')
    if via_access_layer:wanted['DETAILED_ROUTE_ARGS']=VIA_ONLY_ARGS
    record['actual_variables'] = {}
    for name, expected in wanted.items():
        run(command + ['print-' + name], 'variable-' + name + '.log')
        value = re.search(r'(?m)^' + name + r': (.+)$', (out / ('variable-' + name + '.log')).read_text())
        assert value and value.group(1).strip() == expected
        record['actual_variables'][name] = value.group(1).strip()
    save()
    for stage in ['do-route', 'do-finish']:
        run(command + [stage], stage + '.log')
        if via_access_layer and stage=='do-route':
            record['actual_detailed_route_commands']=re.findall(r'(?m)^detailed_route .+$',(out/'do-route.log').read_text())
            assert record['actual_detailed_route_commands']and all(value.endswith(VIA_ONLY_ARGS)for value in record['actual_detailed_route_commands'])
        with slot(base):
            for name, digest in copied.items():
                assert file_sha(results / name) == file_sha(source / relative / name) == digest
            assert file_sha(folder) == record['actual_config_sha256']
            assert file_sha(source / 'receipt.json') == record['source_receipt_sha256']
        record['stages'].append(stage)
        save()
    record['pipeline_completed'] = True
    record['final_files'] = {p.name: dict(path=str(p), sha256=file_sha(p)) for p in results.glob('6_final.*') if p.is_file()}
    assert all('6_final.' + suffix in record['final_files'] for suffix in ['odb', 'sdc', 'v', 'spef', 'def'])
    save()
