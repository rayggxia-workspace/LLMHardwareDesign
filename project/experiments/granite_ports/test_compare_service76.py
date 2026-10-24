"""Synthetic JSON/byte fixtures only; no tensors or production calendars."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

S = importlib.util.spec_from_file_location('comparison76', Path(__file__).with_name('compare_service76.py'))
C = importlib.util.module_from_spec(S); S.loader.exec_module(C)


def h(value): return hashlib.sha256(str(value).encode()).hexdigest()
def write(path, value): Path(path).write_text(json.dumps(value, sort_keys=True, indent=2)+'\n', encoding='utf-8')
def artifacts(folder): return {p.name: C.desc(p) for p in folder.iterdir() if p.is_file() and p.name != 'manifest.json'}
def seal(folder, schema, status, source):
    a = artifacts(folder)
    write(folder/'manifest.json', {'schema': schema, 'status': status, 'source': source,
                                  'producer_sha256': source.get('service_sha256', h('micro')),
                                  'artifacts': [{'path': name, **record} for name, record in sorted(a.items())]})
    return a


def calibration(root):
    folder, audit = root/'micro-formal', root/'audit-micro-formal'; folder.mkdir(); audit.mkdir()
    source = {'commit': '1'*40, 'micro_sha256': h('micro source')}
    ops = {}
    for op in C.OPS:
        hist = {key: 0 for key in C.INSTRUCTIONS}
        hist['MULS8' if op.startswith('mul_') else 'COPY'] = {'mul_s32_s32': 25, 'mul_s64_s32': 45, 'mul_s32_u16': 15}.get(op, 1)
        steps = sum(hist.values())
        domain = list(range(64 if op == 'align_s32_i64' else 128 if op.startswith('shl_') else 129)) if op.startswith(('rne_', 'shl_')) or op == 'align_s32_i64' else [0]
        ops[op] = {'costs': {'primitive_counts': hist, 'scalar_ALU_dependency_cycles': steps,
                             'software_controller_dispatches': steps, 'conservative_scalar_cycles_ALU_plus_dispatch': 2*steps,
                             'byte_store_reads': 3, 'byte_store_writes': 2, 'input_load_bytes': 1, 'result_read_bytes': 1,
                             'scratch_peak_bytes': 32, 'frame_capacity_bytes': 512, 'SIMD8_qualified': False},
                   'domain_bound_status': 'FIXED_DATA_INDEPENDENT_TOPOLOGY_EXHAUSTIVE_SHIFT',
                   'proof': {'kind': 'fixed_loops_exhaustive_shift_domain', 'domain': domain, 'source_sha256': source['micro_sha256']}}
    inv = {'VR8_lanes': 8, 'SFU_count': 1, 'SFU_uses_VR8_lane0': True, 'scalar_frame_bytes': 512,
           'operand_register_bytes_per_active_lane': 5, 'ROM': {'word_bits': 32, 'latency_cycles': 2,
           'II_cycles': 1, 'ports': 1, 'depth_words': 32768, 'capacity_bytes': 131072}}
    table = {'schema': 'micro-cost-table76-v1', 'level': 'BYTE_ALU_RTL_REPLAY_WITH_SOFTWARE_CONTROLLER', 'source': source, 'inventory': inv, 'ops': ops}
    (folder/'rom.hex').write_bytes(b'synthetic tiny ROM bytes, not a real LUT')
    (folder/'rom.requests').write_bytes(b'synthetic tiny request bytes')
    rtl = {'status': 'PASS_BYTE_CORE_RTL_REPLAY', 'ALU_latency_edges': 1, 'ROM_word_bits': 32, 'ROM_ports': 1,
           'ROM_latency_cycles': 2, 'ROM_II_cycles': 1, 'actions': 1234, 'cases': 123}
    report = {'source': source, 'full_wide_RTL_FSM': False, 'RTL': rtl,
              'ROM': {'used_bytes': 73736, 'reserved_bytes': 131072,
                      'ROM_file_sha256': C.sha(folder/'rom.hex'), 'requests_sha256': C.sha(folder/'rom.requests')}}
    write(folder/'report.json', report); write(folder/'cost_table.json', table); write(folder/'rtl_report.json', rtl)
    a = seal(folder, 'micro-calibration-run76-v1', 'PASS_BYTE_CORE_AND_WIDE_MICROPROGRAM', source)
    receipt = {'schema': 'micro-independent-receipt76-v1', 'status': 'PASS_MICRO_CAUSAL_BYTE_AND_ROM',
               'service_all_keys_qualified': True, 'typed_keys': 18, 'producer_manifest': C.desc(folder/'manifest.json'),
               'artifacts': a, 'cost_table': C.desc(folder/'cost_table.json'), 'actions': 1234, 'cases': 123}
    write(audit/'receipt.json', receipt)
    return {'calibration_manifest_sha256': C.sha(folder/'manifest.json'), 'calibration_receipt_sha256': C.sha(audit/'receipt.json'),
            'calibration_cost_table_sha256': C.sha(folder/'cost_table.json')}, table


def inventory():
    caps = {'M': 32768, 'V': 16384, 'R': 32768, 'EXT': 134217728, 'ROM': 4260100, **{'S'+str(i): 32768 for i in range(8)}}
    return {'capacities': caps, 'banks': {b: {'bits': 128, 'kind': '1RW', 'partial_write': '128bit endpoint RMW, no assumed byte mask'} for b in caps if b != 'ROM'},
            'matrix': {'S8_PEs': 256, 'shape': [16, 16], 'effective_B1_PEs': 16, 'Ktile': 512, 'weight_bytes': 8192},
            'vector': {'byte_lanes': 8}, 'SFU': {'count': 1, 'borrows': 'VR8 lane0', 'extra_byte_ALU': False},
            'ROM': {'capacity': 4260100, 'return_bits': 32, 'ports': 1, 'latency': 2, 'II': 1, 'synchronous_candidate': True},
            'packet': {'BUS_count': 1, 'BUS_bits': 128, 'beat_bytes': 16, 'header_bytes': 32, 'max_payload_bytes': 1984, 'FIFO_bytes': 2048}}


def allocation(tile, placement):
    owner = 'M' if placement == 'near_m' else 'V'
    rows = []
    def add(name, bank, offset, n, phase=None):
        life = ['task_start', 'task_end'] if phase is None else {'kind': 'token_phase', 'phases': [phase], 'every_token': True, 'barriers': 'front -> down -> norm -> next_token'}
        rows.append({'object': name, 'bank': bank, 'offset': offset, 'bytes': n, 'lifetime': life})
    add('M.base', 'M', 0, 1024); add('V.microframe', 'V', 0, 512); add('V.byte_regs', 'V', 512, 5)
    add('ROM.silu_and_route', 'ROM', 0, 73736); add('ROM.padding', 'ROM', 73736, 131072-73736)
    add('EXT.weights', 'EXT', 0, 94371840); add('S0.mid', 'S0', 0, 4096)
    add('front.temporary', 'V', 528, 2000, 'front')
    add('down.merge64', owner, 1024 if owner == 'M' else 528, tile*8, 'down')
    high = {}; phase = {b: {p: 0 for p in C.PHASES} for b in ('M', 'V')}
    for a in rows:
        high[a['bank']] = max(high.get(a['bank'], 0), a['offset']+a['bytes'])
        if a['bank'] in phase:
            phases = C.PHASES if isinstance(a['lifetime'], list) else a['lifetime']['phases']
            for p in phases: phase[a['bank']][p] = max(phase[a['bank']][p], a['offset']+a['bytes'])
    return rows, high, phase


def fixture(root):
    cal, table = calibration(root)
    source = {'commit': '2'*40, 'service_sha256': h('service')}; receiver = {'commit': '3'*40, 'receiver_sha256': h('receiver')}
    for layer in C.LAYERS:
        for tile in C.TILES:
            for p in C.PLACEMENTS:
                for label in C.LABELS:
                    name = f'service-l{layer}-t{tile}-{p}-{label}01'; folder, audit = root/name, root/('audit-'+name)
                    folder.mkdir(); audit.mkdir()
                    task = {'layer': layer, 'tokens': 72, 'router_bits': 16, 'split': 'evaluation', 'model_revision': C.REVISION,
                            'source_bound_numeric_status': 'PASS', 'source_bound_micro_status': 'PASS', 'numeric_trajectory_sha256': h(('trajectory', layer)), **cal}
                    for field in ('numeric_manifest', 'numeric_receipt', 'packed_manifest', 'packed_receipt'): task[field+'_sha256'] = h((field, layer))
                    task['compiled_manifest_sha256'] = h('compiled')
                    essential = {'router.ids', 'router.gate_q15', 'norm_q12', 'expert_input_a8', 'expert_input_delta', 'gate_up_acc32', 'gate_up_RQ_product64', 'gate_up_q12', 'expert_silu_q12', 'mid_product64', 'expert_mid_q12', 'mid_a8', 'mid_delta', 'down_acc32', 'down_RQ_product64', 'down_q12', 'merge_product64', 'merge_prefix64', 'moe_q12', 'scaled_moe_q12', 'layer_output_q12', 'next_norm_q12'}
                    shapes = {'router.ids': [72, 8], 'router.gate_q15': [72, 8], 'norm_q12': [72, 1536], 'expert_mid_q12': [72, 8, 512], 'down_q12': [72, 8, 1536], 'merge_prefix64': [72, 8, 1536], 'layer_output_q12': [72, 1536], 'next_norm_q12': [72, 1536]}
                    stages = {k: {'dtype': 'int32', 'shape': shapes.get(k, [72]), 'array_sha256': h((layer, k)), 'token_axis': 0, 'token_rows_sha256': [h((layer, k, t)) for t in range(72)]} for k in sorted(essential | {'synthetic'+str(i) for i in range(43-len(essential))})}
                    rows = {'schema': 'granite-service-rowhashes76-v1', 'layer': layer, 'source_manifest_sha256': task['numeric_manifest_sha256'], 'stages': stages}
                    task['numeric_trajectory_sha256'] = C.canonical(rows); write(folder/'row_hashes.json', rows)
                    task['row_hashes_sha256'] = C.sha(folder/'row_hashes.json')
                    (folder/'witness.jsonl.gz').write_bytes(f'synthetic calendar l{layer}/t{tile}/{p}'.encode())
                    a, high, phase = allocation(tile, p)
                    c = {'matrix_S8_MACs': 72*8*(1024*1536+1536*512), 'matrix_issued_cycles': 72*8*(1024*1536+1536*512)//16,
                         'matrix_resets': 72*8*(1024+1536)//16, 'ROM_word32_reads': 72*8*512, **{'op.'+op: 1 for op in C.OPS}}
                    c.update(micro_alu_cycles=sum(v['costs']['scalar_ALU_dependency_cycles'] for v in table['ops'].values()),
                             micro_dispatch_cycles=sum(v['costs']['software_controller_dispatches'] for v in table['ops'].values()),
                             micro_frame_read_bytes=sum(v['costs']['byte_store_reads']+v['costs']['result_read_bytes'] for v in table['ops'].values()),
                             micro_frame_write_bytes=sum(v['costs']['byte_store_writes']+v['costs']['input_load_bytes'] for v in table['ops'].values()))
                    wire = 1000000000+tile*16+(10000 if p == 'shared_v' else 0)
                    c.update(wire_bytes=wire, wire_beats=wire//16, bank_beats=999, micro_frame_write_RMW_read_beats=c['micro_frame_write_bytes'])
                    capacity = {'full8S32_return_bytes': 49152, 'full_H_merge64_bytes': 12288, 'no_full_Q12_return_co_resident': True, 'owner_physical_RQ_elements': 16}
                    s = {'schema': 'granite-service76-v1', 'task': task, 'config': {'tile': tile, 'placement': p, 'label': label, 'policy': 'synthetic serial'},
                         'inventory': inventory(), 'allocations': a, 'used_bytes': high, 'phase_peak_bytes': phase, 'capacity': capacity,
                         'counts': c, 'end_slot': 2000000000+layer*100000+tile*100+(1000 if p == 'shared_v' else 0),
                         'events': 123, 'unknown_fees': [], 'qualification': C.QUALIFICATION,
                         'elapsed_seconds': 1 if label == 'split' else 2, 'environment': {'fixture_only': label}}
                    write(folder/'summary.json', s); aa = seal(folder, 'granite-service-run76-v1', 'EXECUTED_CONDITIONAL_SERVICE', source)
                    r = {'schema': 'granite-service-independent76-v1', 'status': 'PASS_FINITE_SERVICE',
                         'producer_manifest': C.desc(folder/'manifest.json'), 'artifacts': aa,
                         'config': {'layer': layer, 'tile': tile, 'placement': p, 'label': label}, 'counts': c, 'end_time': s['end_slot'],
                         'numeric_row_hashes_sha256': C.canonical(rows), 'integer_profile_sha256': C.canonical(C.integer_profile(c)),
                         'inventory_sha256': C.canonical(s['inventory']), 'allocations_sha256': C.canonical(a), 'peak_bytes': high,
                         'phase_lifetime_checked': True, 'fullH_s64_merge_bytes': 12288, 'source': receiver,
                         'packet_retiming_checked': True, 'packet_retiming_policy': 'serial_one_packet_source_BUS_destination_RMW', 'max_FIFO_bytes': 2048,
                         'full8S32_V_rejection': {'bytes': 49152, 'capacity': 16384, 'status': 'REJECTED'},
                         'negative_status': 'PASS_ACTUAL_SHA_REWRITE', 'negative_tests': [{'name': n, 'status': 'REJECTED_AFTER_SHA_REWRITE'} for n in sorted(C.NEGATIVES)]}
                    for field in ('numeric_manifest', 'compiled_manifest', 'packed_manifest', 'calibration_manifest', 'numeric_receipt', 'packed_receipt', 'calibration_receipt'):
                        r[field] = {'bytes': 12, 'sha256': task[field+'_sha256']}
                    write(audit/'receipt.json', r)


def rewrite(root, name, mutate, witness=None):
    folder, rp = root/name, root/('audit-'+name)/'receipt.json'; s = C.load(folder/'summary.json'); mutate(s)
    write(folder/'summary.json', s)
    if witness is not None: (folder/'witness.jsonl.gz').write_bytes(witness)
    old = C.load(folder/'manifest.json'); aa = seal(folder, old['schema'], old['status'], old['source']); r = C.load(rp)
    r.update(producer_manifest=C.desc(folder/'manifest.json'), artifacts=aa, counts=s['counts'], end_time=s['end_slot'], peak_bytes=s['used_bytes'],
             integer_profile_sha256=C.canonical(C.integer_profile(s['counts'])), inventory_sha256=C.canonical(s['inventory']), allocations_sha256=C.canonical(s['allocations']))
    write(rp, r)


class CompareServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='service76-compare-tiny-'); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); fixture(self.root)

    def test_all24_and_fullH_alias_feasible(self):
        r = C.compare(self.root)
        self.assertEqual(r['independent_receipts_pass'], 24); self.assertEqual(len(r['paired_placements']), 6)
        self.assertEqual(len(r['label_controls']), 12); self.assertEqual(len(r['full1536_merge']), 8)
        self.assertTrue(all(x['allocation_proof']['merge_window_bytes'] == 12288 for x in r['full1536_merge']))
        self.assertEqual(r['old_full8S32_in_V']['status'], 'REJECTED')

    def test_label_payload_change_after_SHA_rewrite(self):
        rewrite(self.root, 'service-l0-t128-near_m-shared01', lambda s: s.update(end_slot=s['end_slot']+1))
        with self.assertRaisesRegex(ValueError, 'label cannot change'): C.compare(self.root)

    def test_label_witness_change_after_SHA_rewrite(self):
        rewrite(self.root, 'service-l13-t1536-shared_v-shared01', lambda s: None, witness=b'changed')
        with self.assertRaisesRegex(ValueError, 'label cannot change'): C.compare(self.root)

    def test_unknown_width_fee_rejects_ranking(self):
        rewrite(self.root, 'service-l0-t128-near_m-split01', lambda s: s.update(unknown_fees=['not_qualified']))
        with self.assertRaisesRegex(ValueError, 'unknown/unqualified'): C.compare(self.root)

    def test_capacity_gift_rejected_after_SHA_rewrite(self):
        rewrite(self.root, 'service-l0-t128-near_m-split01', lambda s: s['inventory']['capacities'].update(V=32768))
        with self.assertRaisesRegex(ValueError, 'fixed macro capacities'): C.compare(self.root)

    def test_overlap_cannot_be_disguised_as_phase_reuse(self):
        def mutate(s):
            row = next(a for a in s['allocations'] if a['object'] == 'down.merge64'); row['lifetime']['phases'] = ['front']
        rewrite(self.root, 'service-l0-t1536-shared_v-split01', mutate)
        with self.assertRaisesRegex(ValueError, 'overlapping live phase'): C.compare(self.root)

    def test_full8S32_counterexample_must_remain_rejected(self):
        rp = self.root/'audit-service-l0-t128-near_m-split01/receipt.json'; r = C.load(rp); r['full8S32_V_rejection']['status'] = 'PASS'; write(rp, r)
        with self.assertRaisesRegex(ValueError, 'capacity negative'): C.compare(self.root)

    def test_old_same_counts_without_packet_proof_cannot_rank(self):
        rp = self.root/'audit-service-l0-t128-near_m-split01/receipt.json'; r = C.load(rp)
        r['packet_retiming_checked'] = False; write(rp, r)
        with self.assertRaisesRegex(ValueError, 'per-packet FIFO/retiming'): C.compare(self.root)

    def test_missing_formal_negative_rejects(self):
        rp = self.root/'audit-service-l0-t128-near_m-split01/receipt.json'; r = C.load(rp); r['negative_tests'].pop(); write(rp, r)
        with self.assertRaisesRegex(ValueError, 'five real semantic'): C.compare(self.root)

    def test_missing_case_and_stale_raw_artifact_fail(self):
        p = self.root/'service-l0-t128-near_m-split01/witness.jsonl.gz'; p.write_bytes(b'stale')
        with self.assertRaisesRegex(ValueError, 'actual artifact SHA'): C.compare(self.root)
        p.unlink()
        with self.assertRaises(FileNotFoundError): C.compare(self.root)

    def test_missing_micro_initialization_fee_rejected(self):
        for label in C.LABELS:
            rewrite(self.root, f'service-l0-t128-near_m-{label}01', lambda s: s['counts'].update(micro_frame_write_bytes=s['counts']['micro_frame_write_bytes']-1, micro_frame_write_RMW_read_beats=s['counts']['micro_frame_write_RMW_read_beats']-1))
        with self.assertRaisesRegex(ValueError, 'complete eighteen-key weighted'): C.compare(self.root)

    def test_partial_frame_write_cannot_assume_free_mask(self):
        rewrite(self.root, 'service-l0-t128-near_m-split01', lambda s: s['counts'].update(micro_frame_write_RMW_read_beats=0))
        with self.assertRaisesRegex(ValueError, 'endpoint RMW'): C.compare(self.root)

    def test_MV_math_change_cannot_be_called_placement(self):
        for label in C.LABELS:
            def mutate(s): s['counts']['op.max_s64'] += 1
            rewrite(self.root, f'service-l13-t256-shared_v-{label}01', mutate)
        with self.assertRaisesRegex(ValueError, 'complete eighteen-key weighted|wide arithmetic'): C.compare(self.root)

    def resign_calibration(self, table_mutation=None, report_mutation=None):
        folder = self.root/'micro-formal'; rp = self.root/'audit-micro-formal/receipt.json'
        if table_mutation:
            table = C.load(folder/'cost_table.json'); table_mutation(table); write(folder/'cost_table.json', table)
        if report_mutation:
            report = C.load(folder/'report.json'); report_mutation(report); write(folder/'report.json', report)
        old = C.load(folder/'manifest.json'); a = seal(folder, old['schema'], old['status'], old['source'])
        r = C.load(rp); r.update(producer_manifest=C.desc(folder/'manifest.json'), artifacts=a, cost_table=C.desc(folder/'cost_table.json')); write(rp, r)
        return {'calibration_manifest_sha256': C.sha(folder/'manifest.json'), 'calibration_receipt_sha256': C.sha(rp),
                'calibration_cost_table_sha256': C.sha(folder/'cost_table.json')}

    def test_seventeen_key_pilot_rejects_after_full_SHA_rewrite(self):
        task = self.resign_calibration(table_mutation=lambda t: t['ops'].pop('signextend_s16_i64'))
        with self.assertRaisesRegex(ValueError, 'all required typed widths'): C.calibration_proof(self.root, task)

    def test_SIMD_discount_rejects_after_full_SHA_rewrite(self):
        task = self.resign_calibration(table_mutation=lambda t: t['ops']['mul_s32_u16']['costs'].update(SIMD8_qualified=True))
        with self.assertRaisesRegex(ValueError, 'free SIMD'): C.calibration_proof(self.root, task)

    def test_ROM_padding_not_free_after_full_SHA_rewrite(self):
        task = self.resign_calibration(report_mutation=lambda r: r['ROM'].update(reserved_bytes=73736))
        with self.assertRaisesRegex(ValueError, 'original LUT words, padding'): C.calibration_proof(self.root, task)

    def test_compare_output_exclusive_and_manifest_bound(self):
        out = self.root/'result'; C.run(self.root, out, '4'*40)
        m = C.load(out/'manifest.json'); self.assertEqual(m['artifacts'][0]['sha256'], C.sha(out/'report.json'))
        with self.assertRaisesRegex(ValueError, 'must be new'): C.run(self.root, out)


if __name__ == '__main__': unittest.main()
