"""Package completed timing evidence; never rerun STA or parasitic extraction."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_table(path):
    with Path(path).open(encoding='utf-8') as f: return list(csv.DictReader(f, delimiter='\t'))


def violations(path):
    result = {}; phase = None
    for line in Path(path).read_text().splitlines():
        if line.strip() in ('max slew', 'max capacitance'): phase = line.strip()
        words = line.split()
        if phase and len(words) == 5 and words[-1] == '(VIOLATED)':
            result.setdefault(words[0], {})[phase] = dict(limit=float(words[1]), actual=float(words[2]), slack=float(words[3]))
    return result


def selected_slews(path, std_cells):
    result = []
    for line in Path(path).read_text().splitlines():
        m = re.match(r'^\s*((?:[-+\d.eE]+\s+){3,4})[\^v]\s+(\S+)\s+\(([^)]+)\)', line)
        if m and m[3] in std_cells:
            # Both input-pin rows (3 numbers) and output-pin rows (4 numbers).
            result.append(dict(pin=m[2], master=m[3], slew_ns=list(map(float, m[1].split()))[-3]))
    assert result
    return result


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--binding', type=Path, required=True)
    p.add_argument('--model-domain', type=Path, required=True)
    p.add_argument('--domain-nets', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); a.out.mkdir()
    index = {}
    for f in a.inputs.glob('source-index*.json'):
        for name, proof in json.loads(f.read_text()).items():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            path = a.inputs / name
            assert path.stat().st_size == proof['bytes'] and digest(path) == proof['sha256'], path
            if name in index: assert index[name] == proof
            index[name] = proof
    summary = json.loads((a.inputs / 'final/timing-summary.json').read_text())
    assert summary['boundary_nets'] == 2491 and summary['boundary_envelopes'] == 4982
    assert summary['detailed_upper_parameter_liveness']['passed']
    assert len(summary['node_placement_sensitivities_ps']) == 4
    for proof in summary['source_proofs'].values():
        assert proof['explicit_path_crosscheck_maximum_difference_ps'] <= .01
    rows = load_table(a.inputs / 'final/boundary-comparison.tsv')
    assert len(rows) == 4982 and len({(r['net'], r['mode']) for r in rows}) == 4982
    binding = json.loads(a.binding.read_text())['endpoints']
    assert {r['net'] for r in rows} == set(binding)
    for case in range(8):
        directory = a.inputs / ('connected/' + str(case) if case < 4 else 'final/cases/' + str(case))
        meta = json.loads((directory / 'timing.json').read_text())
        for name, proof in meta['files'].items():
            f = directory / name
            if f.exists():
                assert digest(f) == proof['sha256'] and f.stat().st_size == proof['bytes'], f
                rel = f.relative_to(a.inputs).as_posix()
                if rel not in index:
                    meta_source = index[(directory / 'timing.json').relative_to(a.inputs).as_posix()]['path']
                    index[rel] = dict(path=str(Path(meta_source).parent / name).replace('\\', '/'), **proof)
    compact_fields = ['net', 'mode', 'detailed_before_slack_ns', 'detailed_after_slack_ns',
                      'macro_before_slack_ns', 'macro_after_slack_ns', 'detailed_upper_change_ps',
                      'macro_upper_change_ps', 'new_macro_optimism_ps', 'change_prediction_error_ps',
                      'macro_false_pass_before', 'macro_false_pass_after']
    with (a.out / 'timing-comparison.tsv').open('x', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=compact_fields, delimiter='\t', lineterminator='\n'); writer.writeheader()
        for row in rows:
            values = {k: row[k] if k in ('net', 'mode') else format(float(row[k]), '.9g') for k in compact_fields}
            writer.writerow(values)
    shutil.copyfile(a.inputs / 'final/timing-summary.json', a.out / 'timing-summary.json')
    runtime = json.loads((a.inputs / 'final/runtime-receipt.json').read_text())
    assert not any(x['inherited_exception_commands'] for x in runtime['native_constraints'])
    counter_meta = json.loads((a.inputs / 'final/counter/counterexamples.json').read_text())
    assert counter_meta['confirmed_false_pass_signal_count'] == 18
    for name, proof in counter_meta['files'].items():
        f = a.inputs / 'final/counter' / name
        if f.exists(): assert digest(f) == proof['sha256'] and f.stat().st_size == proof['bytes']
    explicit = {r['net']: r for r in load_table(a.inputs / 'final/counter/counterexamples.tsv')}
    assert set(explicit) == {r['net'] for r in rows if int(r['macro_false_pass_after'])}
    domain_nets = {r['net']: r for r in json.loads(a.domain_nets.read_text())}
    electrical = violations(a.inputs / 'connected/2/electrical.rpt')
    robust = set(summary['false_passes_persisting_across_node_placements']['max']['nets'])
    candidates = []
    for row in rows:
        if not int(row['macro_false_pass_after']): continue
        net = row['net']; ex = explicit[net]
        assert float(ex['explicit_slack_ns']) < 0 <= float(ex['macro_slack_ns'])
        path = a.inputs / 'final/counter' / (net + '.rpt')
        points = selected_slews(path, set(runtime['std_cells']))
        worst = max(points, key=lambda x: x['slew_ns'])
        source_violations = electrical.get(ex['driver'], {})
        path_violations = {point['pin']: electrical[point['pin']] for point in points if point['pin'] in electrical}
        observed_clock = re.search(r'^\s*([\d.eE+\-]+\s+){4}[\^v]\s+clk \(in\)', path.read_text(), re.M)
        assert observed_clock is not None
        clock_slew = float(observed_clock[0].split()[1]); assert clock_slew == 0
        clear = not path_violations and worst['slew_ns'] <= runtime['std_timing_table_slew_max_ns']
        candidates.append(dict(net=net, endpoints=binding[net], detailed_slack_ns=float(ex['explicit_slack_ns']),
            macro_slack_ns=float(ex['macro_slack_ns']), difference_ps=1000 * (float(ex['macro_slack_ns']) - float(ex['explicit_slack_ns'])),
            startpoint=ex['startpoint'], endpoint=ex['endpoint'], persists_across_all_three_placements=net in robust,
            source_electrical_violations=source_violations, reported_path_electrical_violations=path_violations,
            maximum_selected_standard_cell_slew=worst,
            reported_path_rules_and_slew_grid_upper_bound_clear=clear,
            static_external_load_below_global_macro_table_max=not domain_nets[net]['new_over_template'],
            original_report=index['final/counter/' + net + '.rpt']['path'],
            report_sha256=digest(path)))
    assert len(candidates) == len(robust) == 18
    save(a.out / 'false-pass-cases.json', candidates)
    shutil.copyfile(a.inputs / 'final/counter/counterexamples.tsv', a.out / 'explicit-counterexamples.tsv')
    shutil.copyfile(a.inputs / 'final/counter/word_1599.rpt', a.out / 'example-word_1599.rpt')
    findings = dict(boundary_nets=2491, max_min_envelopes=4982, macro_false_pass_signals=18,
        macro_false_pass_signals_before_upper_update=summary['summaries']['max']['false_pass_before'],
        all_18_false_passes_confirmed_by_explicit_paths=True, all_18_persist_across_three_placements=True,
        source_driver_rule_clean_false_passes=sum(not x['source_electrical_violations'] for x in candidates),
        reported_path_rule_and_slew_grid_clear_false_passes=[x['net'] for x in candidates if x['reported_path_rules_and_slew_grid_upper_bound_clear']],
        detail_upper_change_most_negative_ps=summary['summaries']['max']['upper_change_detailed_ps']['minimum'],
        setup_macro_absolute_error_ps=summary['summaries']['max']['updated_macro_absolute_error_ps'],
        hold_macro_absolute_error_ps=summary['summaries']['min']['updated_macro_absolute_error_ps'],
        effective_clock_source_transition_ns_observed_in_explicit_reports=0.0,
        configured_ideal_clock_transition_command_ns=.05, nonclock_external_input_transition_ns=.05,
        clock_note='Propagated-clock reports show an ideal zero-slew source. Do not label the configured ideal clock_transition as the measured propagated source slew.',
        domain_note='Two explicit examples have no reported max-cap/max-slew violations on the printed standard-cell path and their reported slews stay below the original input-slew grid maximum. This is a limited path audit, not full all-arc/PVT qualification. Other examples involve overload or slew extrapolation, so all differences are diagnostics under the stated libraries, not measured silicon errors.',
        model_set_note='Existing same-native P/J macro models reused; missing C/F/U/transport abstractions generated once from unchanged original internal RC.',
        scope='Original 2491 signals, TT static quiet-electrode RC projection. Original native RC unchanged; not new node-resolved native coupling, general SI, real parent clock routing or process-calibrated signoff.',
        direct_macro_reuse_qualified=False, true_coupled_internal_rc_reuse_qualified=False)
    save(a.out / 'timing-findings.json', findings)
    save(a.out / 'final-input-index.json', index)
    save(a.out / 'runtime-receipt.json', runtime)
    save(a.out / 'package-receipt.json', dict(verified_downloaded_files=len(index),
        raw_comparison_sha256=digest(a.inputs / 'final/boundary-comparison.tsv'),
        raw_summary_sha256=digest(a.inputs / 'final/timing-summary.json'),
        binding_sha256=digest(a.binding), model_domain_sha256=digest(a.model_domain), domain_nets_sha256=digest(a.domain_nets),
        files={f.name: dict(bytes=f.stat().st_size, sha256=digest(f)) for f in a.out.iterdir() if f.is_file()}))
    print(json.dumps(dict(nets=2491, rows=4982, false_passes=18, limited_rule_clean_examples=findings['reported_path_rule_and_slew_grid_clear_false_passes'])), flush=True)


if __name__ == '__main__': main()
