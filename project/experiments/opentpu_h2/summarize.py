"""Verify sealed selected evidence and exact full-DEF costs; never qualify pending DRC."""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
import re
from freeze_audit import snapshot

HERE = Path(__file__).resolve().parent
RESULTS = HERE / 'results'
SELECTED = ['inventory-03', 'budget-03', 'boundary-01', 'route-proxy-m8-10', 'composite-m8-03',
            'annotation-01', 'drc-h1-01', 'drc-h2-01']

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def evidence(attempt, name):
    root = RESULTS / attempt
    manifest = json.loads((root / 'terminal.json').read_text())['manifest']
    path = root / name
    raw = path.read_bytes() if path.exists() else gzip.decompress((root / (name + '.gz')).read_bytes())
    assert sha(raw) == manifest[name], (attempt, name, 'changed sealed bytes')
    return raw

def main():
    p = argparse.ArgumentParser()
    p.add_argument('baseline_def', type=Path)
    p.add_argument('final_def', type=Path)
    a = p.parse_args()
    selected = {}
    identities = []
    for attempt in SELECTED:
        receipt = json.loads((RESULTS / (attempt + '-submission.json')).read_text())
        terminal = json.loads((RESULTS / attempt / 'terminal.json').read_text())
        raw_manifest = ''.join(f'{digest}  ./{name}\n' for name, digest in terminal['manifest'].items()).encode()
        assert sha(raw_manifest) == terminal['manifest_sha256'], 'Changed manifest index'
        assert '|COMPLETED|0:0|' in terminal['sacct'] and terminal['sacct'].endswith('|UNLIMITED')
        assert 'TimeLimit=UNLIMITED' in receipt['scheduler_readback']
        assert evidence(attempt, 'exit-code.txt').strip() == b'0'
        assert json.loads(evidence(attempt, 'spec.json')) == receipt['spec']
        for name, digest in receipt['runner_files'].items():
            assert terminal['manifest']['runner/' + name] == digest, (attempt, name)
        for name, digest in receipt.get('h1_support_files', {}).items():
            assert terminal['manifest']['runner/h1/' + name] == digest, (attempt, name)
        for name, digest in receipt.get('h1_root_tcl_aliases', {}).items():
            assert terminal['manifest']['runner/' + name] == digest, (attempt, name)
        identities.append((evidence(attempt, 'image.sha256'), evidence(attempt, 'tools.sha256')))
        # Validate every retained selected artifact against the original remote manifest.
        for path in (RESULTS / attempt).rglob('*'):
            if path.is_file() and path.name != 'terminal.json':
                rel = path.relative_to(RESULTS / attempt).as_posix()
                evidence(attempt, rel[:-3] if rel.endswith('.gz') else rel)
        selected[attempt] = dict(job_id=terminal['job_id'], sacct=terminal['sacct'],
            manifest_sha256=terminal['manifest_sha256'], runner_commit=receipt['spec']['runner_commit'])
    assert len(set(identities)) == 1, 'Tool or image identity differs'
    parent = 'composite-m8-03'
    freeze = json.loads(evidence(parent, 'composite-native-freeze-audit.json'))
    assert freeze['passed'] and freeze['before_sha256'] == sha(a.baseline_def.read_bytes())
    assert freeze['after_sha256'] == sha(a.final_def.read_bytes())
    inventory_manifest=json.loads((RESULTS/'inventory-03/terminal.json').read_text())['manifest']
    parent_manifest=json.loads((RESULTS/parent/'terminal.json').read_text())['manifest']
    assert inventory_manifest['physical.def']==freeze['before_sha256']
    assert parent_manifest['composite-roundtrip.def']==freeze['after_sha256']
    contract_raw = (RESULTS / 'resource-contract-v01.json').read_bytes()
    contract = json.loads(contract_raw)
    assert contract['parent_active_support_total'] == 9609
    assert contract['post_freeze_active_additions_allowed'] == 0
    assert contract['post_freeze_active_master_or_position_changes_allowed'] == 0
    assert contract['custom_metals'] == ['metal8', 'metal9', 'metal10']
    assert contract['custom_vias'] == ['via8', 'via9']
    assert contract['inventory_manifest_sha256'] == selected['inventory-03']['manifest_sha256']
    assert contract['budget_manifest_sha256'] == selected['budget-03']['manifest_sha256']
    proofs = {}
    for name in ['composite-quality.json', 'full-hierarchy-quality.json', 'upper-connectivity.json',
                 'boundary-proof.json', 'final-pg/strict-pg.json']:
        proof_raw = evidence(parent, name)
        value = json.loads(proof_raw)
        assert value['passed'], name
        if name == 'final-pg/strict-pg.json':
            assert value['VDD_pass'] and value['VSS_pass'] and value['macro_pg_iterm_count'] == 4
        if name == 'upper-connectivity.json':
            assert len(value['results']) == value['forest_count'] == 1003
            assert all(row['connected'] for row in value.pop('results'))
        value['sealed_proof_sha256'] = sha(proof_raw)
        proofs[name] = value
    assert re.findall(rb'Number of violations = (\d+)', evidence('route-proxy-m8-10', 'route.log'))[-1] == b'0'
    assert evidence('route-proxy-m8-10', 'restricted-drc.rpt').strip() == b''
    costs = {}
    for name, path in [('h1', a.baseline_def), ('h2', a.final_def)]:
        data = snapshot(path, 8)
        assert len(data['components']) == contract['parent_instances_including_fill_tap_macros']
        cost = {}
        for category in ['fixed', 'custom']:
            wires, vias = collections.Counter(), collections.Counter()
            for key, count in data[category].items():
                if key[1] == 'wire':
                    wires[str(key[2])] += count * (abs(key[3]-key[6]) + abs(key[4]-key[7]))
                else:
                    vias[key[2]] += count
            cost[category] = dict(wire_um=sum(wires.values()) / 2000,
                by_layer_um={k: v / 2000 for k, v in wires.items()}, vias=sum(vias.values()), by_via=dict(vias))
        cost['parent_wire_um'] = sum(v['wire_um'] for v in cost.values())
        cost['parent_vias'] = cost['fixed']['vias'] + cost['custom']['vias']
        costs[name] = cost
    assert costs['h1']['fixed'] == costs['h2']['fixed']
    assert set(costs['h2']['custom']['by_layer_um']) <= {'8', '9', '10'}
    assert set(costs['h2']['custom']['by_via']) <= {'via8_0', 'via9_0'}
    coverage = json.loads(evidence('annotation-01', 'annotation-validation.json'))['h2']
    assert coverage['passed'] and all(coverage['checks'].values())
    assert coverage['source'].endswith('/issue-31/composite-m8-03')
    assert coverage['connectivity_sha256'] == sha(evidence('annotation-01', 'h2-unannotated-connectivity.tsv'))
    known_inputs=json.loads(evidence(parent,'input-sha256.json'))
    known_inputs.update(json.loads(evidence(parent,'h1-qualification-input-sha256.json')))
    root=coverage['source']+'/'
    for name,digest in parent_manifest.items():known_inputs[root+name]=digest
    known_inputs[root+'output.sha256']=selected[parent]['manifest_sha256']
    for path,digest in json.loads(evidence('annotation-01','input-sha256.json')).items():
        assert known_inputs.get(path)==digest,('Changed annotation source',path)
    proofs['annotation-validation.json'] = coverage
    # Standalone DRC is a separate complete-die gate; local/control jobs cannot substitute.
    standalone = {}
    for attempt in ['drc-h1-01', 'drc-h2-01']:
        result = json.loads(evidence(attempt, 'readonly-drc-quality.json'))
        geom = json.loads(evidence(attempt, 'readonly-drc-freeze-audit.json'))
        spec = json.loads(evidence(attempt, 'spec.json'))
        assert spec['mode']=='checks' and not spec.get('box_dbu') and not spec.get('short_control')
        assert result['passed'] and geom['passed'] and all(geom['checks'].values())
        assert not evidence(attempt, 'integrated-drc.rpt').strip()
        assert spec['source']==result['source']
        target=spec['source']+'/flow/results/nangate45/opentpu_top_split/base/6_final.odb'
        inputs=json.loads(evidence(attempt, 'input-sha256.json'))
        expected='6a80303ac643775321e95a49398671a4a5387b589b6eab1b7dfc6d217eec9a81'
        if attempt=='drc-h2-01':
            terminal=json.loads((RESULTS/parent/'terminal.json').read_text())
            expected=terminal['manifest']['flow/results/nangate45/opentpu_top_split/base/6_final.odb']
        assert inputs[target]==expected
        standalone[attempt] = dict(**result, checked_odb_sha256=expected,
            all_geometry_unchanged=geom['passed'],sealed_report_sha256=sha(evidence(attempt,'integrated-drc.rpt')))
    out = dict(qualified_first_slice=True,resource_contract_sha256=sha(contract_raw),
        generator_sha256=sha(Path(__file__).read_bytes()),freeze_parser_sha256=sha((HERE/'freeze_audit.py').read_bytes()),selected=selected, costs=costs,
        proofs=proofs, freeze=freeze, standalone_drc=standalone,
        scope='One same-function H1-conditioned instance. Frozen lower/clock/PG and all active resources; new M8-M10/V8-V9 conductors only. No multi-graph reuse or manufacturing signoff claim.')
    raw = (json.dumps(out, indent=2) + '\n').encode()
    (RESULTS / 'selected-evidence.json').write_bytes(raw)
    print('Selected sealed evidence and exact full-DEF costs verified:', sha(raw))
    print(json.dumps(costs, indent=2))

if __name__ == '__main__':
    main()
