"""Summarize only closed, hash-bound full-bus repair evidence."""
import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(folder, function_run, patched_s_run):
    evidence = folder / 'evidence'
    baseline = json.loads((folder / 'baseline-area.json').read_text())
    assert baseline['passed']

    def load(number, task, report):
        run = evidence / ('closure-run%d' % number)
        index = json.loads((run / 'index.json').read_text())
        base = run / 'tasks' / task
        receipt_path = base / 'receipt.json'
        relative = receipt_path.relative_to(run).as_posix()
        assert sha(receipt_path) == index['files'][relative]['sha256']
        receipt = json.loads(receipt_path.read_text())
        assert receipt['passed'] and receipt['mode'] == task
        path = base / report
        row = index['files'][path.relative_to(run).as_posix()]
        assert sha(path) == row['sha256']
        if row.get('receipt_bound'):
            assert sha(path) == receipt['outputs'][report]
        else:
            origin = row['derived_from']
            assert origin['original_receipt_bound']
            assert origin['sha256'] == receipt['outputs']['linkclose-result.json']
        return json.loads(path.read_text()), dict(
            path=path.relative_to(folder).as_posix(), sha256=sha(path),
            receipt_sha256=sha(receipt_path))

    native = {}
    for kind, number, count in [('m', 930, 132), ('t', 932, 140), ('s', patched_s_run, 1)]:
        accepted, binding = load(number, 'linkfix-s-combine' if kind=='s' else 'linkfix-accept-' + kind, 'linkfix-accept.json')
        physical = accepted['physical']
        timing = physical['timing']['timed_endpoints']
        assert accepted['passed'] and physical['passed'] and timing['passed']
        assert accepted['drc']['passed'] and accepted['drc']['full_deck']['total_items'] == 0
        assert accepted['strict_final_lec']['passed']
        source, source_binding = load(patched_s_run if kind=='s' else 928, 'linkfix-s-finish' if kind=='s' else 'linkfix-native-' + kind, 'linkfix-native.json')
        assert source['passed'] and len(source['selected_drivers']) == count
        assert source_binding['receipt_sha256'] == accepted['source_receipt_sha256']
        assert physical['source']==accepted['source']==accepted['drc']['source']
        assert physical['source_receipt_sha256']==accepted['source_receipt_sha256']==accepted['drc']['source_receipt_sha256']
        assert accepted['drc']['full_deck']['top_cell']==physical['top']==source['top']
        for name in ('6_final.odb','6_final.v'):
            file=source['files'][name]
            assert accepted['complete_signal_view']['input_sha256'][file['path']]==file['sha256']
        functional, function_binding = load(patched_s_run if kind=='s' else function_run, 'linkfix-s-qa-function' if kind=='s' else 'linkfix-function-' + kind, 'five-macro-final-function.json')
        assert functional['passed'] and len(functional['initial_runs']) == 3
        assert functional['source_receipt_sha256'] == source_binding['receipt_sha256']
        assert functional['full_final_netlist']['full_view_sha256'] == accepted['complete_signal_view']['full_view_sha256']
        if kind=='s':
            old_function, old_function_binding=load(function_run,'linkfix-function-s','five-macro-final-function.json')
            reuse=functional['functional_reuse']
            assert reuse['passed'] and reuse['old_receipt_sha256']==old_function_binding['receipt_sha256']
            assert old_function['initial_runs']==functional['initial_runs']
            assert old_function['full_final_netlist']['full_view_sha256']==functional['full_final_netlist']['full_view_sha256']==reuse['identical_complete_signal_view_sha256']
            patch,patch_binding=load(patched_s_run,'linkfix-s-patch','linkfix-s-patch.json')
            assert patch['passed'] and not patch['native_after'].strip() and patch['native_before'].count('violation type:')==3
            assert source['patch_receipt_sha256']==patch_binding['receipt_sha256']
        native[kind] = dict(binding=binding, source_binding=source_binding,
            function_binding=function_binding, initial_runs=functional['initial_runs'],
            die_um=physical['die_um'], active_area_um2=physical['active_area_um2'],
            baseline_area_binding=baseline['baseline'][kind],
            added_active_area_um2=physical['active_area_um2']-baseline['baseline'][kind]['active_area_um2'],
            physical_only_area_um2=physical['physical_only_area_um2'],
            accepted_sdc=dict(path=physical['sta_sdc_path'], sha256=physical['sta_sdc_sha256']),
            selected_buf_x4_to_x16=count, min_setup_ns=timing['minimum_setup_ns'],
            min_hold_ns=timing['minimum_hold_ns'], strict_lec=accepted['strict_final_lec'],
            function_reuse=functional.get('functional_reuse'),
            final_files=dict(source['files'], **{'6_final.gds': accepted['drc']['gds']}))

    cases = []
    routes = {}
    for pair, number, total in [('mq1', 932, 275), ('tq3', patched_s_run, 281)]:
        route, route_binding = load(number, 'linkclose-route-' + pair, 'linkclose-route.json')
        inputs, _ = load(number, 'linkclose-route-' + pair, 'route-inputs.json')
        prepared, prepare_binding = load(number, 'linkclose-prepare-' + pair, 'linkclose-prepare.json')
        assert route['passed'] and route['links'] == total
        assert not inputs['representative_subset'] and inputs['original_full_bus_links']==total
        assert prepared['passed'] and prepared['geometry']['passed'] and prepared['links'] == total
        assert prepared['route_receipt_sha256'] == route_binding['receipt_sha256']
        for kind in ('mt' if pair == 'mq1' else 'ts'):
            assert route['rebound_native'][kind]['source_receipt_sha256'] == native[kind]['source_binding']['receipt_sha256']
            assert all(digest == native[kind]['final_files'][name]['sha256']
                       for name, digest in inputs['native'][kind]['hashes'].items())
            interface=inputs['lefs'][kind]
            if 'interface_lef' in native[kind]:assert native[kind]['interface_lef']['sha256']==interface['sha256']
            native[kind]['interface_lef']=interface
        inline_acceptance = route.get('complete_native_acceptance_included')
        if inline_acceptance is None:
            # MQ1 predates the explicit flag: its two acceptance report hashes
            # must match the independently loaded complete native gates.
            assert pair == 'mq1'
            assert all(route['rebound_native'][kind]['accepted_report_sha256'] ==
                       native[kind]['binding']['sha256'] for kind in 'mt')
            inline_acceptance = True
        routes[pair] = dict(links=total, route_binding=route_binding,
            signal_legs_by_instance_pair=dict(Counter(link['source'][0]+'->'+link['sink'][0] for link in inputs['links'])),
            prepare_binding=prepare_binding, wire_length_um=prepared['wire_length_um'],
            macro_footprints_um2={k: w*h for k, (w, h) in inputs['size'].items()},
            total_macro_footprint_um2=sum(w*h for w, h in inputs['size'].values()),
            route_die_um=inputs['die_um'],
            route_die_area_um2=inputs['die_um'][0]*inputs['die_um'][1],
            electrical_view_native_acceptance_inline=inline_acceptance)
        for variant in ('grounded', 'opposite', 'guarded'):
            result, binding = load(number, 'linkclose-case-' + pair + '-' + variant,
                                   'linkclose-result-summary.json')
            assert result['experiment_completed'] and result['native_preservation']['passed']
            assert result['connected_parasitics_annotated'] and len(result['observations']) == total
            assert result['source_receipt_sha256'] == prepare_binding['receipt_sha256']
            worst = max(result['observations'], key=lambda row: row['new_wire_cap_ff'])
            cases.append(dict(pair=pair, variant=variant, links=total, binding=binding,
                declared_model_passed=result['declared_model_passed'], counts=result['counts'],
                min_link_setup_ns=result['min_link_setup_ns'], min_link_hold_ns=result['min_link_hold_ns'],
                maximum_new_wire_cap=dict(net=worst['id'], capacitance_ff=worst['new_wire_cap_ff'],
                    length_um=worst['wire_length_um'], via_count=worst['via_count']),
                model=result['model']))
    result = dict(schema='block-v1-full-bus-repair/1', function_run=function_run, patched_s_run=patched_s_run, native=native, routes=routes, cases=cases,
        completed_cases=len(cases), declared_model_passes=sum(row['declared_model_passed'] for row in cases),
        all_declared_models_passed=all(row['declared_model_passed'] for row in cases),
        original_production_replaced=False,
        scope='Repaired prefab copies and two fixed complete-bus arrangements only. '
              'tq3 I/O views are diagnostic, separately joined here to full native acceptance of the exact same source. '
              'No common CTS/top PG/full-controller, dynamic SI, foundry RCX, arbitrary fanout or manufacturing qualification.')
    (folder / 'repair-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('completed_cases', 'declared_model_passes', 'all_declared_models_passed')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--function-run', type=int, required=True)
    parser.add_argument('--patched-s-run', type=int, required=True)
    args = parser.parse_args()
    summarize(args.folder, args.function_run, args.patched_s_run)
