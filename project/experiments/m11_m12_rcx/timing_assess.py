"""Validate and compare matched boundary-path envelopes of four timing cases."""
import argparse
import csv
import json
import math
from pathlib import Path
import re
import statistics

from native_compare import percentile
from timing_native import sha


def statistics_ps(values):
    return dict(minimum=min(values), median=statistics.median(values), p95=percentile(values, .95), maximum=max(values))


def read_run(path):
    meta = json.loads((path / 'timing.json').read_text())
    if meta['level'] == 'full':
        assert meta.get('hierarchical_spef_read_order') == 'top_then_native_parent_before_child', 'Known-invalid native-before-top reference'
        assert meta.get('explicit_ideal_parent_sha256'), 'Ideal parent port/clock connections must be explicit to retain native interface RC.'
    for name, proof in meta['files'].items():
        f = path / name
        assert f.stat().st_size == proof['bytes'] and sha(f) == proof['sha256'], f
    prep = json.loads((Path(meta['prepared']) / 'prepare.json').read_text())
    assert sha(Path(meta['prepared']) / 'prepare.json') == meta['prepared_sha256']
    upper = prep['upper_rc'][meta['upper_rc']]
    assert upper['sha256'] == meta['upper_spef_sha256'] == sha(upper['path'])
    data = {}
    with (path / 'boundary.tsv').open() as f:
        for row in csv.DictReader(f, delimiter='\t'):
            key = (row['net'], row['mode']); assert key not in data
            for field in ('slack_ns', 'arrival_ns', 'required_ns'):
                if field not in row: continue
                row[field] = float(row[field]); assert math.isfinite(row[field])
            data[key] = row
    assert len(data) == 4982 and {m for _, m in data} == {'max', 'min'}
    with (path / 'coverage.tsv').open() as f:
        coverage = list(csv.DictReader(f, delimiter='\t'))
    assert len(coverage) == 2491
    counts = ('max_finite_slack', 'min_finite_slack') if meta.get('measurement_method') == 'propagated_slack_at_proven_exclusive_leaf_driver' else ('max_paths', 'min_paths')
    assert all(all(int(row[k]) == 1 for k in ('source_pins', 'sink_pins', *counts)) for row in coverage)
    crosscheck_maximum_ps = None
    if meta.get('measurement_method') == 'propagated_slack_at_proven_exclusive_leaf_driver':
        with (path / 'slack-crosscheck.tsv').open() as f: crosschecks = list(csv.DictReader(f, delimiter='\t'))
        assert len(crosschecks) >= 12
        crosscheck_maximum_ps = max(abs(float(r['difference_ps'])) for r in crosschecks)
        assert crosscheck_maximum_ps <= .01
    log = (path / 'openroad.log').read_text()
    assert 'TIMING_CONTEXT_COMPLETE' in log and 'time 1ns' in log
    allowed = set(); unused_sources = {}
    for inst in prep['instances']:
        audit = prep['audits'][inst[0] + '0']
        if audit['legacy_model']:
            source = Path(audit['legacy_model']).parent / 'unused-boundaries.tsv'
            unused_sources[str(source)] = sha(source)
            for line in source.read_text().splitlines():
                role, name = line.split('\t'); allowed.add(inst + '/' + name)
    warnings = [line for line in log.splitlines() if '[WARNING ' in line]
    classified = []
    for line in warnings:
        if '[WARNING ORD-0011]' in line:
            classified.append(dict(warning=line, reason='OpenROAD hierarchy implementation warning, retained limitation.'))
        elif '[WARNING STA-1655]' in line:
            m = re.search(r'not connected to net (.+)\.$', line)
            assert m and m[1] in allowed, line
            classified.append(dict(warning=line, reason='Same unused native boundary explicitly listed in the accepted original gate.'))
        else: raise AssertionError(('Unclassified timing warning', line))
    assert 'not found' not in log
    annotation = (path / 'annotation.rpt').read_text()
    unannotated_count = int(re.search(r'Found (\d+) unannotated drivers\.', annotation)[1])
    partial_count = int(re.search(r'Found (\d+) partially unannotated drivers\.', annotation)[1])
    missing_boundary = []
    if meta['level'] == 'full':
        proof_path = Path(meta['prepared']) / 'driver-proof.json'
        assert sha(proof_path) == meta['driver_proof_sha256']
        driver_proof = json.loads(proof_path.read_text())
        actual = {r['leaf_driver'] for r in driver_proof['rows'].values()}
        assert len(actual) == 2491
        names = {re.sub(r'\\(.)', r'\1', line.strip()) for line in annotation.splitlines() if not line.startswith('Found ')}
        missing_boundary = sorted(actual & names)
        assert not missing_boundary, ('Unannotated real top-word drivers', missing_boundary[:10])
        assert partial_count == 0, ('Incomplete parasitic connections remain', partial_count)
    annotation_proof = dict(unannotated_driver_count=unannotated_count, partially_unannotated_driver_count=partial_count,
                            unannotated_boundary_drivers=missing_boundary,
                            raw_report=str(path / 'annotation.rpt'), sha256=sha(path / 'annotation.rpt'),
                            scope='All boundary drivers checked. Original non-boundary unannotated objects are counted; their complete physical extraction is not newly qualified.')
    globals_ = {m: float(v) for m, v in re.findall(r'worst slack (max|min)\s+([-\d.eE+]+)', log)}
    return meta, prep, data, dict(path=str(path), timing_sha256=sha(path / 'timing.json'),
                                 classified_warnings=classified, unused_boundary_sources=unused_sources,
                                 annotation=annotation_proof, global_slack_ns=globals_,
                                 explicit_path_crosscheck_maximum_difference_ps=crosscheck_maximum_ps,
                                 old_explicit_control_maximum_difference_ps=meta.get('old_explicit_control_maximum_difference_ps'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs', type=Path, nargs='+', required=True)
    p.add_argument('--readback-root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); a.out.mkdir()
    runs = {}; proofs = {}; shared = None
    for folder in a.runs:
        meta, prep, data, proof = read_run(folder)
        key = (meta['level'], meta['upper_rc']); assert key not in runs
        signature = (sha(prep['harness']), sha(prep['binding']),
                     tuple(sorted((k, sha(v['model'])) for k, v in prep['audits'].items())))
        if shared is None: shared = signature
        assert signature == shared, 'Changed harness, endpoint identity or macro model.'
        runs[key] = data; proofs[str(key)] = proof
    for rc in ('quiet-baseline', 'quiet-updated'):
        assert ('full', rc) in runs and ('abstract', rc) in runs
    ref = runs['full', 'quiet-baseline']
    assert all(set(rows) == set(ref) for rows in runs.values())
    before = runs['full', 'quiet-baseline']; after = runs['full', 'quiet-updated']
    liveness_delta_ps = [1000 * (after[k]['slack_ns'] - before[k]['slack_ns']) for k in ref]
    assert max(map(abs, liveness_delta_ps)) > 1, 'Changed upper C did not measurably affect the detailed reference'
    ab_before = runs['abstract', 'quiet-baseline']; ab_after = runs['abstract', 'quiet-updated']
    rows = []
    for net, mode in sorted(ref):
        k = (net, mode)
        fb, fa, mb, ma = [d[k]['slack_ns'] for d in (before, after, ab_before, ab_after)]
        rows.append(dict(net=net, mode=mode, detailed_before_slack_ns=fb, detailed_after_slack_ns=fa,
                         macro_before_slack_ns=mb, macro_after_slack_ns=ma,
                         detailed_upper_change_ps=1000 * (fa - fb), macro_upper_change_ps=1000 * (ma - mb),
                         old_macro_optimism_ps=1000 * (mb - fb), new_macro_optimism_ps=1000 * (ma - fa),
                         change_prediction_error_ps=1000 * ((ma - mb) - (fa - fb)),
                         macro_false_pass_before=int(mb >= 0 and fb < 0), macro_false_pass_after=int(ma >= 0 and fa < 0),
                         macro_false_fail_after=int(ma < 0 and fa >= 0),
                         detailed_measurement_pin=after[k].get('measurement_pin', ''),
                         macro_measurement_pin=ab_after[k].get('measurement_pin', ''),
                         detailed_startpoint=after[k].get('startpoint', ''), detailed_endpoint=after[k].get('endpoint', ''),
                         macro_startpoint=ab_after[k].get('startpoint', ''), macro_endpoint=ab_after[k].get('endpoint', '')))
    with (a.out / 'boundary-comparison.tsv').open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    summaries = {}
    for mode in ('max', 'min'):
        selection = [r for r in rows if r['mode'] == mode]
        summaries[mode] = dict(nets=len(selection),
            original_macro_absolute_error_ps=statistics_ps([abs(r['old_macro_optimism_ps']) for r in selection]),
            updated_macro_absolute_error_ps=statistics_ps([abs(r['new_macro_optimism_ps']) for r in selection]),
            updated_macro_optimism_ps=statistics_ps([r['new_macro_optimism_ps'] for r in selection]),
            upper_change_detailed_ps=statistics_ps([r['detailed_upper_change_ps'] for r in selection]),
            upper_change_prediction_error_ps=statistics_ps([abs(r['change_prediction_error_ps']) for r in selection]),
            false_pass_before=sum(r['macro_false_pass_before'] for r in selection),
            false_pass_after=sum(r['macro_false_pass_after'] for r in selection),
            false_fail_after=sum(r['macro_false_fail_after'] for r in selection),
            newly_negative_detailed_envelopes=sum(r['detailed_before_slack_ns'] >= 0 and r['detailed_after_slack_ns'] < 0 for r in selection),
            worst_absolute_error=max(selection, key=lambda r: abs(r['new_macro_optimism_ps'])),
            worst_optimism=max(selection, key=lambda r: r['new_macro_optimism_ps']),
            worst_updated_boundary_envelope=min(selection, key=lambda r: r['detailed_after_slack_ns']))
    readbacks = [json.loads(f.read_text()) for f in a.readback_root.glob('job-*/result/readback.json')]
    assert {x['kind'] for x in readbacks} == {'C0', 'F0', 'T0', 'U0'}
    sensitivities = {}
    for level in ('full', 'abstract'):
        main_rows = runs.get((level, 'quiet-updated'))
        for rc in ('quiet-updated-source', 'quiet-updated-sink'):
            if (level, rc) in runs:
                delta = [1000 * (runs[level, rc][k]['slack_ns'] - main_rows[k]['slack_ns']) for k in ref]
                sensitivities[level + '/' + rc] = statistics_ps([abs(x) for x in delta])
    robust = {}
    variants = ('quiet-updated', 'quiet-updated-source', 'quiet-updated-sink')
    if all((level, rc) in runs for level in ('full', 'abstract') for rc in variants):
        for mode in ('max', 'min'):
            keys = [k for k in ref if k[1] == mode]
            stable = [k[0] for k in keys if all(runs['abstract', rc][k]['slack_ns'] >= 0 and runs['full', rc][k]['slack_ns'] < 0 for rc in variants)]
            robust[mode] = dict(signals=len(stable), nets=stable,
                                scope='False passes persist in all three sampled C-placement scenarios, not a mathematical bound for every possible distributed field solution.')
    result = dict(scope='Matched worst-through-net max/min path envelopes under a common ideal-clock harness, not counts of unique complete chip paths.',
                  boundary_nets=2491, boundary_envelopes=len(rows), clock_period_ns=3.3333,
                  detailed_upper_parameter_liveness=dict(passed=True, changed_envelopes=sum(v != 0 for v in liveness_delta_ps),
                                                        maximum_slack_change_ps=max(map(abs, liveness_delta_ps))),
                  summaries=summaries, node_placement_sensitivities_ps=sensitivities,
                  false_passes_persisting_across_node_placements=robust,
                  original_native_readbacks=readbacks,
                  maximum_native_representation_readback_difference_ps=max(abs(v) for x in readbacks for v in x['difference_ps'].values()),
                  source_proofs=proofs,
                  conditions=prep['assumptions'],
                  verdict='unsafe_for_signoff_in_tested_context' if any(x['false_pass_after'] for x in summaries.values()) else 'requires_explicit_error_budget_and_remaining_physics_validation',
                  direct_macro_reuse_qualified=False, true_node_resolved_native_coupling_timing_qualified=False,
                  acceptance_error_budget_ps=None)
    (a.out / 'timing-summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: {x: v for x, v in s.items() if not x.startswith('worst')} for k, s in summaries.items()}), flush=True)


if __name__ == '__main__': main()
