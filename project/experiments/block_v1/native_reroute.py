"""Repeat standard route/final from a sealed CTS checkpoint with cap margin.

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


def config_suffix(margin):
    assert margin in (20,40)
    return '\nexport CAP_MARGIN = %d\n'%margin


def checked_config(source, receipt, original,margin=20):
    """Bind the actual reroute configuration to the original plus one target."""
    path = source / 'config.mk'
    assert file_sha(path) == receipt['outputs']['config.mk']
    assert path.read_bytes() == original.read_bytes() + config_suffix(margin).encode()
    record = source / 'native-candidate.json'
    assert file_sha(record) == receipt['outputs'][record.name]
    candidate = json.loads(record.read_text())
    assert candidate['repair_variant'] == 'cap-margin-%d-from-sealed-cts'%margin
    assert candidate['actual_variables']['CAP_MARGIN'] == str(margin)
    assert candidate['actual_variables']['LEC_CHECK'] == '1'
    assert candidate['actual_variables']['SEC_CHECK'] == '0'
    assert candidate['actual_config_sha256'] == file_sha(path)
    return path


def implement(root, out, cpus, run, top, policy,pipeline=PIPELINE):
    assert top in ('shared109', 'transaction6k') and policy in ('A', 'C') and cpus >= 16
    assert pipeline in ('native_pipeline_cap20.json','native_pipeline_cap40.json')
    config = json.loads((root / 'project/experiments/block_v1' / pipeline).read_text())
    margin=config.get('cap_margin',20)
    assert margin==(40 if pipeline=='native_pipeline_cap40.json'else 20)
    base = out.parents[2]
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
    folder.write_bytes(original_config.read_bytes() + config_suffix(margin).encode())
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
        repair_variant='cap-margin-%d-from-sealed-cts'%margin,
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
