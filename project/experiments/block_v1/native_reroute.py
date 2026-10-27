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


def config_suffix(margin,hold_margin=None,diode_hook=None):
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
    return suffix


def variant(margin,hold_margin=None,diode=False):
    config_suffix(margin,hold_margin)
    if diode:
        assert margin==40 and hold_margin==.005
        return 'cap40-hold5ps-input-diode-via-in-m10-from-sealed-cts'
    return 'cap40-hold5ps-from-sealed-cts'if hold_margin is not None else 'cap-margin-%d-from-sealed-cts'%margin


def checked_config(source, receipt, original,margin=20,hold_margin=None,diode=False):
    """Bind actual configuration to the original plus exact repair targets."""
    path = source / 'config.mk'
    assert file_sha(path) == receipt['outputs']['config.mk']
    hook=source/'input-diodes.tcl'if diode else None
    if diode:assert file_sha(hook)==receipt['outputs'][hook.name]
    assert path.read_bytes() == original.read_bytes() + config_suffix(margin,hold_margin,hook).encode()
    record = source / 'native-candidate.json'
    assert file_sha(record) == receipt['outputs'][record.name]
    candidate = json.loads(record.read_text())
    assert candidate['repair_variant'] == variant(margin,hold_margin,diode)
    assert candidate['actual_variables']['CAP_MARGIN'] == str(margin)
    if hold_margin is not None:
        assert candidate['actual_variables']['HOLD_SLACK_MARGIN']=='0.005'
        assert candidate['hold_margin_ns']==hold_margin
    assert candidate['actual_variables']['LEC_CHECK'] == '1'
    assert candidate['actual_variables']['SEC_CHECK'] == '0'
    if diode:
        assert candidate['actual_variables']['PRE_GLOBAL_ROUTE_TCL']==str(hook)
        assert candidate['actual_variables']['VIA_IN_PIN_MIN_LAYER']==candidate['actual_variables']['VIA_IN_PIN_MAX_LAYER']=='metal10'
    assert candidate['actual_config_sha256'] == file_sha(path)
    return path


def implement(root, out, cpus, run, top, policy,pipeline=PIPELINE):
    assert top in ('shared109', 'transaction6k') and policy in ('A', 'C') and cpus >= 16
    assert pipeline in ('native_pipeline_cap20.json','native_pipeline_cap40.json','native_pipeline_hold5.json','native_pipeline_diode.json')
    config = json.loads((root / 'project/experiments/block_v1' / pipeline).read_text())
    margin=config.get('cap_margin',20)
    assert margin==(20 if pipeline=='native_pipeline_cap20.json'else 40)
    hold_margin=config.get('hold_margin_ns')
    diode=pipeline=='native_pipeline_diode.json'
    assert hold_margin==(.005 if pipeline in ('native_pipeline_hold5.json','native_pipeline_diode.json')else None)
    assert config['repair_variant']==variant(margin,hold_margin,diode)
    base = out.parents[2]
    if diode:
        proof=base/'block-v1-20261027-110/tasks/native-antenna-fixture'
        bound=json.loads((proof/'receipt.json').read_text());assert bound['passed']is True
        path=proof/'native-antenna-fixture.json';assert file_sha(path)==bound['outputs'][path.name]
        qualified=json.loads(path.read_text());assert qualified['passed']is True and qualified['formal']['passed']is True
        hook=out/'input-diodes.tcl';shutil.copyfile(root/'project/experiments/block_v1/native_input_diodes.tcl',hook)
    else:hook=None
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
    folder.write_bytes(original_config.read_bytes() + config_suffix(margin,hold_margin,hook).encode())
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
        repair_variant=variant(margin,hold_margin,diode),hold_margin_ns=hold_margin,
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
    record['actual_variables'] = {}
    for name, expected in wanted.items():
        run(command + ['print-' + name], 'variable-' + name + '.log')
        value = re.search(r'(?m)^' + name + r': (.+)$', (out / ('variable-' + name + '.log')).read_text())
        assert value and value.group(1).strip() == expected
        record['actual_variables'][name] = value.group(1).strip()
    save()
    for stage in ['do-route', 'do-finish']:
        run(command + [stage], stage + '.log')
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
