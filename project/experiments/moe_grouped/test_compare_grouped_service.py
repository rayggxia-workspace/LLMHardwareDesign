"""Tiny synthetic metadata tests; no model, numerical tensors or calendar maths."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('grouped_compare_only', Path(__file__).with_name('compare_grouped_service.py'))
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


def h(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2)+'\n', encoding='utf-8')


def inventory():
    caps = {'M': 32768, 'V': 16384, 'R': 32768, 'ROM': 4260100, 'EXT': 134217728,
            **{'S'+str(i): 32768 for i in range(8)}}
    recipes = {}
    for width, products, adds, digits, rne in [('64', 25, 24, [5, 5], 106), ('128', 45, 44, [9, 5], 182)]:
        recipes[width] = {'products': products, 'wide_adds': adds, 'operand_digits': digits,
                          'RNE_byte_ops': rne, 'RNE_breakdown': {'synthetic_explicit_total': rne}}
    return {'capacities': caps, 'matrix': {'S8_PEs': 256, 'shape': [16, 16], 'effective_PEs_single_row': 16},
            'lanes': {'S8_lanes': 8, 'resource': 'VR8'}, 'wide_factor': 1,
            'packet': {'BUS_bits': 128, 'BUS_count': 1, 'FIFO_bytes': 2048, 'beat_bytes': 16, 'header_bytes': 32, 'max_payload': 1984},
            'ports': {b: {'bits': 128, 'kind': '1RW'} for b in caps},
            'grouped_kernel': {'VR8_count': 8, 'new_private_M_ALU': False, 'Otile': 16,
                               'physical_Ktile': 256, 'rq_recipes': recipes}}


def rewrite(root, name, change=None, witness=None):
    folder = root/name
    receipt_path = root/('audit-'+name)/'receipt.json'
    summary = C.load(folder/'summary.json')
    if change:
        change(summary)
    write(folder/'summary.json', summary)
    if witness is not None:
        (folder/'witness.jsonl.gz').write_bytes(witness)
    manifest = C.load(folder/'manifest.json')
    manifest['artifacts'] = [{'path': p, **C.descriptor(folder/p)} for p in sorted(C.ARTIFACTS)]
    write(folder/'manifest.json', manifest)
    receipt = C.load(receipt_path)
    receipt['producer_manifest'] = C.descriptor(folder/'manifest.json')
    receipt['artifacts'] = {p: C.descriptor(folder/p) for p in sorted(C.ARTIFACTS)}
    receipt.update(counts=summary['counts'], config=summary['config'], end_slot=summary['end_slot'],
                   high_water_bytes=summary['used_bytes'], events_checked=summary['events'])
    write(receipt_path, receipt)


def fixtures(root):
    inv = inventory()
    allocations = [{'object': 'synthetic.'+b, 'bank': b, 'bytes': 64, 'offset': 0,
                    'lifetime': ['task_start', 'task_end']} for b in ('M', 'V', 'R', 'ROM', 'EXT')]
    high = {b: 64 for b in ('M', 'V', 'R', 'ROM', 'EXT')}
    source = {'commit': '1'*40, 'grouped_service_sha256': h('producer'), 'closure_service_sha256': h('helper'),
              'sources': {'project/experiments/moe_grouped/grouped_service.py': h('producer'),
                          'project/experiments/closure/service.py': h('helper')}}
    receiver_source = {'commit': '2'*40, 'receive_grouped_service_sha256': h('receiver'), 'audit_io74_sha256': h('audit_io'),
                       'sources': {'project/experiments/moe_grouped/receive_grouped_service.py': h('receiver'),
                                   'project/experiments/moe_grouped/audit_io74.py': h('audit_io')}}
    for g, groups in C.GROUPS.items():
        for p in C.PLACEMENTS:
            for label in C.LABELS:
                name = f'group-g{g}-{p}-{label}02'
                folder, audit = root/name, root/('audit-'+name)
                folder.mkdir(); audit.mkdir()
                task = {k: h(k) for k in C.COMMON_TASK if k.endswith('_sha256')}
                task.update(group_k=g, groups=groups, tokens=72, state_bits=32,
                            numeric_function='frozen synthetic fullK oneRQ', cuts='external A/residual',
                            reference_errors={'diagnostic_only': g}, grouped_manifest_sha256=h(('math', g)),
                            grouped_receipt_sha256=h(('math_receipt', g)))
                n = 72*2560
                counts = {'wide_s8_product': n*(25 if g == 0 else 45),
                          'wide_add64' if g == 0 else 'wide_add128': n*(24 if g == 0 else 44),
                          'rq_rne64_complete' if g == 0 else 'rq_rne128_complete': n,
                          'constant_shift64' if g == 0 else 'constant_shift128': n*(25 if g == 0 else 45),
                          'digit_byte_op': n*(18 if g == 0 else 26), 'matrix_mac': 2365194240,
                          'copy_byte': 10000+(72*34 if p == 'shared_v' else 0),
                          'engine_wire_bytes': 1024, 'engine_wire_beats': 64, 'engine_packets': 16,
                          'engine_local_beats': 512, 'engine_operand_read_bytes': 100, 'engine_operand_write_bytes': 200,
                          'local_beats': 100000, 'src_beats': 100000, 'dst_beats': 100000,
                          'wire_bytes': 1000000000, 'wire_beats': 62500000, 'packets': 1000000, 'payload_bytes': 10000000}
                if g:
                    counts['signextend_i32_i64'] = n*groups
                if p == 'shared_v':
                    delta = 72*160*groups*96-72*80
                    counts['wire_bytes'] += delta
                    counts['wire_beats'] += delta//16
                    counts['payload_bytes'] += 72*160*groups*64-72*34
                summary = {'schema': 'grouped-service-v1', 'task': task,
                           'config': {'placement': p, 'label': label, 'Otile': 16, 'physical_Ktile': 256, 'policy': 'synthetic serialized'},
                           'inventory': inv, 'allocations': allocations, 'used_bytes': high, 'counts': counts,
                           'events': 146, 'end_slot': 1000000000+g+(72*160*groups*14 if p == 'shared_v' else 0),
                           'limits': ['synthetic receipt fixture, no model claim'],
                           'environment': {'observer': label}, 'elapsed_seconds': 1 if label == 'split' else 4}
                write(folder/'summary.json', summary)
                write(folder/'splice.json', {'common_R_trajectory_and_epochs_unchanged': True,
                                             'inserted_tokens': list(range(72)), 'removed': [{}]*288,
                                             'inherited': [{'canonical_sha256': h('synthetic')}]*2})
                (folder/'witness.jsonl.gz').write_bytes(f'synthetic tiny witness g{g}/{p}'.encode())
                manifest = {'schema': 'grouped-service-run-v1', 'status': 'EXECUTED_CONDITIONAL_SERVICE',
                            'source': source, 'producer_sha256': h('producer'), 'dependency_sha256': h('helper'),
                            'artifacts': [{'path': x, **C.descriptor(folder/x)} for x in sorted(C.ARTIFACTS)]}
                write(folder/'manifest.json', manifest)
                receipt = {'schema': 'grouped-service-independent-receipt74-v1', 'status': 'PASS',
                           'producer_manifest': C.descriptor(folder/'manifest.json'),
                           'artifacts': {x: C.descriptor(folder/x) for x in sorted(C.ARTIFACTS)}, 'source': receiver_source,
                           'wide_lowering_status': 'PASS_ALL_ACTUAL_PRODUCTS', 'integer_wide_products_lowered': n,
                           'negative_status': 'PASS_ACTUAL_SHA_REWRITE',
                           'negative_tests': [{'name': k, 'status': 'REJECTED_AFTER_SHA_REWRITE'} for k in ('port', 'RAM', 'numeric_binding', 'engine_operand')],
                           'config': summary['config'], 'counts': counts, 'high_water_bytes': high,
                           'group_k': g, 'groups': groups, 'end_slot': summary['end_slot'], 'events_checked': summary['events'],
                           'inherited_events_checked': 2, 'complete_replacement_tokens': 72,
                           'source_receipts': {'base_service': {'bytes': 20, 'sha256': task['base_service_receipt_sha256']},
                                               'grouped_math': {'bytes': 20, 'sha256': task['grouped_receipt_sha256']}},
                           'grouped_artifacts': {'synthetic': {'bytes': 1, 'sha256': h(('g', g))}},
                           **{k: {'synthetic': {'bytes': 1, 'sha256': h(k)}} for k in ('base_service_artifacts', 'baseline_artifacts', 'compiled_artifacts')}}
                write(audit/'receipt.json', receipt)


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='grouped-compare-tiny-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        fixtures(self.root)

    def test_complete_receipts_allow_observer_changes_and_real_copy_difference(self):
        r = C.compare(self.root)
        self.assertEqual(r['independent_receipts_pass'], 12)
        self.assertTrue(all(x['end_slot_delta'] == 0 for x in r['label_controls']))
        for pair in r['paired_comparisons']:
            self.assertEqual(pair['movement_count_deltas_shared_v_minus_near_m']['copy_byte'], 2448)
            a = pair['near_m']
            self.assertEqual(a['wire_bytes_total_including_engine'], a['non_engine_wire_bytes']+a['engine_wire_bytes_subset_already_in_total'])
            self.assertEqual(pair['metadata_and_partial_protocol']['static_Wscale_group_duplication_factor'], 1)

    def test_label_semantic_mutation_rejected_after_all_sha_rewritten(self):
        rewrite(self.root, 'group-g256-near_m-shared02', lambda s: s.update(end_slot=s['end_slot']+1))
        with self.assertRaisesRegex(ValueError, 'label must not change'):
            C.compare(self.root)

    def test_label_witness_mutation_rejected_after_all_sha_rewritten(self):
        rewrite(self.root, 'group-g512-shared_v-shared02', witness=b'changed synthetic witness')
        with self.assertRaisesRegex(ValueError, 'label must not change'):
            C.compare(self.root)

    def test_port_gift_rejected_after_all_sha_rewritten(self):
        rewrite(self.root, 'group-g0-shared_v-split02', lambda s: s['inventory']['ports']['V'].update(bits=256))
        with self.assertRaisesRegex(ValueError, 'bank1RW128'):
            C.compare(self.root)

    def test_wide_product_omission_rejected_after_all_sha_rewritten(self):
        rewrite(self.root, 'group-g256-near_m-split02', lambda s: s['counts'].update(wide_s8_product=1))
        with self.assertRaisesRegex(ValueError, 'complete grouped I128'):
            C.compare(self.root)

    def test_engine_wire_double_count_guard(self):
        rewrite(self.root, 'group-g0-near_m-split02', lambda s: s['counts'].update(engine_wire_bytes=s['counts']['wire_bytes']+16,
                                                                                engine_wire_beats=s['counts']['wire_beats']+1))
        with self.assertRaisesRegex(ValueError, 'included subset'):
            C.compare(self.root)

    def test_missing_case_and_nonpass_receipt_fail_closed(self):
        path = self.root/'audit-group-g0-near_m-split02'/'receipt.json'
        r = C.load(path); r['status'] = 'FAIL'; write(path, r)
        with self.assertRaisesRegex(ValueError, 'independent PASS'):
            C.compare(self.root)
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            C.compare(self.root)

    def test_raw_artifact_tamper_does_not_inherit_old_pass(self):
        (self.root/'group-g0-near_m-split02'/'witness.jsonl.gz').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'actual artifact SHA'):
            C.compare(self.root)

    def test_cross_placement_math_change_rejected_even_both_labels_rewritten(self):
        for label in C.LABELS:
            rewrite(self.root, f'group-g512-shared_v-{label}02', lambda s: s['counts'].update(matrix_mac=s['counts']['matrix_mac']+1))
        with self.assertRaisesRegex(ValueError, 'preserve every arithmetic'):
            C.compare(self.root)

    def test_factored_metadata_protocol_change_rejected(self):
        for label in C.LABELS:
            rewrite(self.root, f'group-g256-shared_v-{label}02', lambda s: s['counts'].update(copy_byte=s['counts']['copy_byte']+32))
        with self.assertRaisesRegex(ValueError, 'descriptor copy'):
            C.compare(self.root)

    def test_resource_high_water_cannot_be_invented(self):
        rewrite(self.root, 'group-g256-near_m-split02', lambda s: s['used_bytes'].update(M=63))
        with self.assertRaisesRegex(ValueError, 'bank high water'):
            C.compare(self.root)

    def test_exclusive_output_and_bound_report(self):
        out = self.root/'comparison'
        C.run(self.root, out, source_commit='3'*40)
        manifest = C.load(out/'manifest.json')
        self.assertEqual(manifest['artifacts'][0]['sha256'], C.sha(out/'report.json'))
        with self.assertRaisesRegex(ValueError, 'must be new'):
            C.run(self.root, out)


if __name__ == '__main__':
    unittest.main()
