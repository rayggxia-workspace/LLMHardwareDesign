"""Select proof-bound positive-margin cumulative plans; no EDA or live-file edits."""
import argparse, csv, hashlib, importlib.util, json, re, shutil
from decimal import Decimal
from pathlib import Path

ROOT = Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
SOURCE_SHA = 'b59360079c0e79e335c93b8b014d7f0269d283deb6889c27c64d5ac7e0950ed0'
CATALOG_SHA = 'b8c47e99669b7c9069ad9369301d406ef788af3b0abd78e297bf2a2765bfc963'
HOLD_FLOOR = Decimal('0.001400824')
FIELDS = ['wns_ns', 'tns_ns', 'cap', 'slew', 'setup_count', 'whs_ns', 'hold_count']
RECEIPT_FIELDS = ['wns_ns', 'tns_ns', 'cap_count', 'slew_count', 'setup_count', 'whs_ns', 'hold_count']

def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): result.update(block)
    return result.hexdigest()

def load(path): return json.loads(Path(path).read_text())

def metrics(values):
    result = tuple(Decimal(str(x)) for x in values)
    assert len(result) == 7 and all(x.is_finite() for x in result), 'Invalid metrics'
    for i in (2, 3, 4, 6): assert result[i] >= 0 and result[i] == result[i].to_integral_value()
    return result

def eligible(values):
    return values[0] > 0 and values[1] == 0 and all(values[i] == 0 for i in (2, 3, 4, 6)) and values[5] >= HOLD_FLOOR

def read_plan(path):
    with Path(path).open() as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        assert reader.fieldnames == ['instance', 'old', 'new'], path
        result = {}
        for row in reader:
            assert None not in row and all(row.values()) and row['instance'] not in result, ('Malformed/duplicate plan row', row)
            assert row['old'] != row['new'], row
            result[row['instance']] = (row['old'], row['new'])
    return result

def read_topology(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        row = line.split('\t'); assert len(row) == 6 and row[0] not in result, path
        result[row[0]] = row[1:]
    assert result
    return result

def cumulative(original, current):
    return {n: (old, current[n]) for n, old in original.items() if current[n] != old}

def replay(original, initial, trials, snapshots, validate_change):
    current = dict(original)
    for n, (old, new) in initial.items():
        assert n in original and original[n] == old, ('Initial old not actual source', n)
        validate_change(n, old, new); current[n] = new
    candidates = []; accepted_ids = set()
    for index, row in enumerate(trials, 1):
        assert int(row['trial']) == index, 'Noncontiguous trials'
        n, old, new = row['instance'], row['old'], row['new']
        assert n in current and current[n] == old, ('Trial old not current accepted state', index, n)
        validate_change(n, old, new)
        values = metrics(row[k] for k in FIELDS)
        assert row['accepted'] in ('0', '1')
        if row['accepted'] == '0':
            assert index not in snapshots, ('Rejected trial has snapshot', index)
            continue
        current[n] = new; accepted_ids.add(index)
        assert index in snapshots, ('Accepted trial lacks snapshot', index)
        plan, snapshot_metrics = snapshots[index]
        assert plan == cumulative(original, current), ('Snapshot not exact cumulative accepted plan', index)
        assert snapshot_metrics == values, ('Snapshot metric differs from accepted trial', index)
        for name, (base, target) in plan.items():
            assert original[name] == base
            validate_change(name, base, target)
        if eligible(values): candidates.append(dict(trial=index, plan=plan, metrics=values))
    assert set(snapshots) == accepted_ids, 'Unaccounted snapshot IDs'
    return candidates, current

def rank_unique(candidates):
    ranked = sorted(candidates, key=lambda x: (-x['metrics'][0], -x['metrics'][5], len(x['plan']), x['trial']))
    selected = []; seen = set()
    for row in ranked:
        canonical = tuple(sorted((n, v[1]) for n, v in row['plan'].items()))
        if canonical in seen: continue
        seen.add(canonical); selected.append(row)
        if len(selected) == 6: break
    return selected

def main(planning_dir, output_dir):
    p = Path(planning_dir).resolve(); out = Path(output_dir).resolve()
    assert p.is_dir() and not out.exists(), 'Output must be a new independent directory'
    bound = {}
    def bind(path, expected=None):
        path = Path(path).resolve(); value = sha(path)
        if expected is not None: assert value == expected, ('SHA mismatch', str(path))
        bound[str(path)] = value
        return value
    receipt = load(p/'receipt.json')
    assert receipt['diagnostic_completed'] and receipt['static_wire_model_only']
    assert receipt['all_instance_locations_orientations_pin_to_net_connections_unchanged']
    assert receipt['clock_tree_and_all_top_output_drivers_unchanged']
    bind(p/'receipt.json')
    for name, digest in receipt['hashes'].items(): bind(name, digest)
    for line in (p/'inputs-before.sha256').read_text().splitlines():
        digest, name = line.split(None, 1); path = Path(name.strip().lstrip('*'))
        if not path.is_absolute(): path = p/path
        bind(path, digest)
    frozen = ROOT/'audit/C40-clock-planning-frozen-v1/planning-source.json'
    source = load(frozen); bind(frozen)
    for name, entry in source['files'].items():
        bind(name, entry['sha256']); bind(entry['exact_source'], entry['sha256'])
    for suffix in ('odb', 'spef', 'sdc', 'v'):
        reference = ROOT/('audit/C40-clock-planning-frozen-v1/results/6_final.'+suffix)
        bind(p/('source-snapshot/6_final.'+suffix), sha(reference))
    bind(p/'input.odb', SOURCE_SHA)
    assert sha(ROOT/'audit/C40-clock-planning-frozen-v1/results/6_final.odb') == SOURCE_SHA
    rcx = source['rcx_material']; bind(rcx['path'], rcx['sha256'])
    assert source['whs_ns'] == float(HOLD_FLOOR)
    catalog_path = ROOT/'audit/C-fixture-catalog-v2.json'; bind(catalog_path, CATALOG_SHA)
    catalog = load(catalog_path); assert catalog['passed']
    covered = set(catalog['covered_masters'])
    models = load(p/'models.json'); original_topology = read_topology(p/'topology-before.tsv')
    original = {n: row[0] for n, row in original_topology.items()}
    protected = set((p/'protected-instances.txt').read_text().splitlines()); bind(p/'protected-instances.txt')
    spec = importlib.util.spec_from_file_location('actual_truth', str(p/'truth.py'))
    truth = importlib.util.module_from_spec(spec); spec.loader.exec_module(truth)
    proof_path = ROOT/'audit/C-v40-actual-proof-v2/complete-equivalence-receipt.json'
    proof = load(proof_path); bind(proof_path); assert proof['passed']
    assert proof['hashes'][models['liberty']] == models['liberty_sha256'], 'Actual Liberty provenance mismatch'
    checked_models = {}
    def model_signature(name):
        assert name in covered and name != 'OAI221_X4', name
        assert not re.match(r'^(?:DFF|SDFF|DLH|DLL|TAP|FILL)', name), ('Non-combinational resize', name)
        assert name not in models['dont_use'], ('Forbidden master', name)
        if name not in checked_models:
            m = models['models'][name]
            signature = truth.signature(m['pins'])
            assert signature == m['truth_signature'], ('Stored truth mismatch', name)
            checked_models[name] = signature
        return checked_models[name]
    def validate_change(n, old, new):
        assert n in original and n not in protected, ('Protected or absent instance', n)
        assert new in models['choices'][old], (n, old, new)
        assert models['models'][old]['family'] == models['models'][new]['family']
        assert model_signature(old) == model_signature(new), ('Actual pin/truth mismatch', n)
    initial = read_plan(p/'initial-plan.tsv'); bind(p/'initial-plan.tsv')
    prior = load(p/'initial-planning-receipt.json'); bind(p/'initial-planning-receipt.json')
    assert prior['diagnostic_completed']
    assert {n: list(pair) for n, pair in initial.items()} == prior['sized_instances']
    before = metrics((p/'baseline-metrics.tsv').read_text().split())
    assert before == metrics(receipt['baseline_metrics'][k] for k in RECEIPT_FIELDS)
    assert before[5] >= HOLD_FLOOR and before[6] == 0
    with (p/'trials.tsv').open() as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        assert reader.fieldnames == ['trial','round','instance','old','new']+FIELDS+['accepted']
        trials = list(reader)
    snapshots = {}; paths = {}
    for plan_path in sorted((p/'plans').glob('plan-*.tsv')):
        match = re.fullmatch(r'plan-(\d{4}).tsv', plan_path.name); assert match
        trial = int(match[1]); metric_path = plan_path.with_name('metrics-'+match[1]+'.tsv')
        assert trial not in snapshots
        snapshots[trial] = (read_plan(plan_path), metrics(metric_path.read_text().split()))
        paths[trial] = (plan_path, metric_path); bind(plan_path); bind(metric_path)
    assert len(list((p/'plans').glob('metrics-*.tsv'))) == len(snapshots)
    candidates, current = replay(original, initial, trials, snapshots, validate_change)
    final_plan = read_plan(p/'plan.tsv'); assert final_plan == cumulative(original, current)
    assert {n: list(pair) for n, pair in final_plan.items()} == receipt['sized_instances']
    final_topology = read_topology(p/'topology-after.tsv'); assert set(final_topology) == set(original_topology)
    for n, row in final_topology.items():
        assert row[0] == current[n] and row[1:] == original_topology[n][1:], n
    final_values = metrics((p/'final-metrics.tsv').read_text().split())
    assert final_values == metrics(receipt['final_metrics'][k] for k in RECEIPT_FIELDS)
    accepted = [row for row in trials if row['accepted']=='1']
    assert final_values == (metrics(accepted[-1][k] for k in FIELDS) if accepted else before)
    bind(Path(__file__)); bind(p/'inputs-after-check.log')
    selected = rank_unique(candidates)
    # Recheck all inputs immediately before producing the immutable selection.
    assert all(sha(f)==digest for f,digest in bound.items()), 'Inputs changed during selection'
    out.mkdir(parents=True)
    rows = []
    for index, row in enumerate(selected):
        src, met = paths[row['trial']]; dest=out/('plan%d.tsv'%index); shutil.copyfile(str(src),str(dest))
        rows.append(dict(case=index,trial=row['trial'],plan=str(dest),plan_sha256=sha(dest),source_plan=str(src),source_metrics=str(met),metrics_ns={k:str(v) for k,v in zip(FIELDS,row['metrics'])},changed_instances=len(row['plan']),canonical_sha256=hashlib.sha256(json.dumps(sorted((n,v[1]) for n,v in row['plan'].items()),separators=(',',':')).encode()).hexdigest()))
    selection=dict(passed=True,static_only=True,requires_actual_all_gates=True,selected_count=len(rows),selected=rows,eligible_snapshot_count=len(candidates),accepted_snapshot_count=len(snapshots),criteria=dict(global_wns_ns='>0',global_whs_ns='>=0.001400824',setup_hold_cap_slew_counts=0,tns_ns=0,rank='WNS descending, WHS descending, fewer changed instances, earlier accepted trial; canonical plans distinct'),source_odb_sha256=SOURCE_SHA,planning_source_manifest=str(frozen),planning_source_manifest_sha256=sha(frozen),input_sha256=bound,scope='Static actual-RC planning only. Each selected plan needs independent legal placement, routing, fresh RCX/material, setup/hold/electrical, DRC/ANT/PG/interface and strict functional gates. Fewer than six qualifying plans is permitted; zero is not an accepted implementation.')
    (out/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
    checks=dict(bound); checks[str(out/'selection.json')]=sha(out/'selection.json')
    for row in rows:checks[row['plan']]=row['plan_sha256']
    (out/'selection.sha256').write_text(''.join(digest+'  '+name+'\n' for name,digest in sorted(checks.items())))
    print(json.dumps(dict(selected_count=len(rows),selection=str(out/'selection.json'),selection_sha256=sha(out/'selection.json'))))

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('planning_dir');parser.add_argument('output_dir');args=parser.parse_args();main(args.planning_dir,args.output_dir)
