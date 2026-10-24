"""Independent, metadata-only comparison of twelve received Issue74 service runs.

No producer, receiver, closure helper or tensor library is imported. Calendar and
numeric validity are inherited from explicitly bound independent PASS receipts;
this tool rehashes their result files and checks controlled-comparison invariants.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

GROUPS = {0: 1, 512: 8, 256: 16}
PLACEMENTS = ('near_m', 'shared_v')
LABELS = ('split', 'shared')
ARTIFACTS = {'summary.json', 'splice.json', 'witness.jsonl.gz'}
# These are physical movement/copy costs, not a licence to change arithmetic.
PLACEMENT_COSTS = {'copy_byte', 'dst_beats', 'src_beats', 'local_beats',
                   'packets', 'payload_bytes', 'wire_beats', 'wire_bytes'}
COMMON_TASK = ('base_service_manifest_sha256', 'base_service_receipt_sha256',
               'baseline_manifest_sha256', 'compiled_manifest_sha256',
               'frozen_input_array_sha256', 'frozen_weight_array_sha256',
               'fixed_w_scale_array_sha256', 'fixed_w_exp_array_sha256',
               'numeric_function', 'state_bits', 'tokens', 'cuts')
LIMITS = [
    'PASS means twelve source-bound receipts and comparison invariants passed; this tool does not reexecute numeric or calendar receivers.',
    'Only within each group size do M/V placements implement the same quantized function; group sizes are different functions.',
    'Shared bank-select VR8 and serialized bytewise service are conditional candidate contracts, not physical locality, RTL timing, PPA, model speed or quality acceptance.',
    'Inherited complete R path and consumers retain external attention/residual cuts; no full-model all-integer claim.',
    'Engine wire is a subset of total wire and must never be added to it again.',
    'The 34-byte token descriptor is the actual padded g<=16 policy (including unused bytes); useful metadata and transferred bytes are reported separately.',
    'Full-domain S32*C32,N256 readout requires72 signed bits; inherited guarded-I64 qualification remains unchanged.'
]


def need(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    with Path(path).open(encoding='utf-8') as stream:
        return json.load(stream)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def descriptor(path):
    path = Path(path)
    return {'bytes': path.stat().st_size, 'sha256': sha(path)}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def put(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def integer(value, name):
    need(type(value) is int and value >= 0, 'nonnegative integer '+name)
    return value


def hash_string(value, name):
    need(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'SHA-256 '+name)


def verify_inventory(summary):
    inv = summary['inventory']
    capacities = inv['capacities']
    need(inv['matrix']['S8_PEs'] == 256 and inv['matrix']['shape'] == [16, 16]
         and inv['matrix']['effective_PEs_single_row'] == 16, 'fixed M256/B1 effective16PE inventory')
    need(inv['lanes']['S8_lanes'] == 8 and inv['lanes']['resource'] == 'VR8'
         and inv['wide_factor'] == 1, 'fixed shared eight lane engine')
    packet = inv['packet']
    need(packet == {'BUS_bits': 128, 'BUS_count': 1, 'FIFO_bytes': 2048,
                    'beat_bytes': 16, 'header_bytes': 32, 'max_payload': 1984}, 'fixed BUS/FIFO packet inventory')
    need(capacities['M'] == 32768 and capacities['V'] == 16384 and capacities['R'] == 32768
         and capacities['EXT'] == 134217728, 'fixed local/backing capacities')
    need(set(inv['ports']) == set(capacities)
         and all(p == {'bits': 128, 'kind': '1RW'} for p in inv['ports'].values()), 'fixed bank1RW128 ports')
    kernel = inv['grouped_kernel']
    need(kernel['VR8_count'] == 8 and kernel['new_private_M_ALU'] is False
         and kernel['Otile'] == 16 and kernel['physical_Ktile'] == 256, 'no donated M ALU or tile change')
    expected = {'64': (25, 24, [5, 5], 106), '128': (45, 44, [9, 5], 182)}
    for width, (products, adds, digits, rne) in expected.items():
        recipe = kernel['rq_recipes'][width]
        need((recipe['products'], recipe['wide_adds'], recipe['operand_digits'], recipe['RNE_byte_ops'])
             == (products, adds, digits, rne)
             and sum(recipe['RNE_breakdown'].values()) == rne, 'explicit full-width lowering/RNE recipe')
    high = {}
    names = set()
    regions = {}
    for a in summary['allocations']:
        name, bank = a['object'], a['bank']
        need(name not in names and bank in capacities, 'unique allocated object and existing bank')
        names.add(name)
        start, length = integer(a['offset'], name+' offset'), integer(a['bytes'], name+' bytes')
        need(a['lifetime'] == ['task_start', 'task_end'], 'fixed actual retained lifetime')
        need(start+length <= capacities[bank], 'allocation exceeds fixed capacity')
        for left, right in regions.setdefault(bank, []):
            need(start+length <= left or start >= right, 'overlapping retained allocations')
        regions[bank].append((start, start+length))
        high[bank] = max(high.get(bank, 0), start+length)
    need(high == summary['used_bytes'], 'actual retained allocations and bank high water agree')
    return high


def scientific_summary(summary):
    result = copy.deepcopy(summary)
    result['config'].pop('label')
    # Observer versions/time are provenance, not scientific payload; still retained in input evidence.
    result.pop('elapsed_seconds', None)
    result.pop('environment', None)
    return result


def read_case(root, receipt_root, group_k, placement, label, suffix):
    name = f'group-g{group_k}-{placement}-{label}{suffix}'
    folder, receipt_path = Path(root)/name, Path(receipt_root)/('audit-'+name)/'receipt.json'
    manifest_path = folder/'manifest.json'
    manifest, receipt = load(manifest_path), load(receipt_path)
    need(manifest['schema'] == 'grouped-service-run-v1' and manifest['status'] == 'EXECUTED_CONDITIONAL_SERVICE', name+' producer execution status')
    need(receipt['schema'] == 'grouped-service-independent-receipt74-v1' and receipt['status'] == 'PASS', name+' independent PASS receipt')
    need(receipt['producer_manifest'] == descriptor(manifest_path), name+' receipt manifest binding')
    records = manifest['artifacts']
    need(len(records) == len(ARTIFACTS) and {r['path'] for r in records} == ARTIFACTS, name+' exact result artifact set')
    artifacts = {}
    for record in records:
        # Exact known basenames exclude traversal and links escaping the result root.
        path = folder/record['path']
        need(path.resolve().parent == folder.resolve(), name+' artifact containment')
        value = descriptor(path)
        need(value == {'bytes': record['bytes'], 'sha256': record['sha256']}, name+' actual artifact SHA/size '+record['path'])
        artifacts[record['path']] = value
    need(artifacts == receipt['artifacts'], name+' independently received artifacts')
    source = manifest['source']
    for key in ('producer_sha256', 'dependency_sha256'):
        hash_string(manifest[key], name+' '+key)
    need(source['grouped_service_sha256'] == manifest['producer_sha256']
         and source['closure_service_sha256'] == manifest['dependency_sha256']
         and source['sources']['project/experiments/moe_grouped/grouped_service.py'] == manifest['producer_sha256']
         and source['sources']['project/experiments/closure/service.py'] == manifest['dependency_sha256']
         and re.fullmatch('[0-9a-f]{40}', source['commit']), name+' frozen producer/helper source binding')
    audit = receipt['source']
    need(re.fullmatch('[0-9a-f]{40}', audit['commit'])
         and audit['sources']['project/experiments/moe_grouped/receive_grouped_service.py'] == audit['receive_grouped_service_sha256']
         and audit['sources']['project/experiments/moe_grouped/audit_io74.py'] == audit['audit_io74_sha256'], name+' independent receiver source binding')
    for key in ('receive_grouped_service_sha256', 'audit_io74_sha256'):
        hash_string(audit[key], name+' '+key)
    need(receipt['wide_lowering_status'] == 'PASS_ALL_ACTUAL_PRODUCTS'
         and receipt['integer_wide_products_lowered'] == 72*2560, name+' all actual final products received')
    need(receipt['negative_status'] == 'PASS_ACTUAL_SHA_REWRITE'
         and {n['name'] for n in receipt['negative_tests']} == {'port', 'RAM', 'numeric_binding', 'engine_operand'}
         and all(n['status'] == 'REJECTED_AFTER_SHA_REWRITE' for n in receipt['negative_tests']), name+' meaningful independent semantic negatives')
    summary, splice = load(folder/'summary.json'), load(folder/'splice.json')
    task, cfg, counts = summary['task'], summary['config'], summary['counts']
    need(summary['schema'] == 'grouped-service-v1' and task['group_k'] == group_k
         and task['groups'] == GROUPS[group_k] and task['state_bits'] == 32 and task['tokens'] == 72, name+' fixed numeric scope')
    need(cfg['placement'] == placement and cfg['label'] == label
         and cfg['Otile'] == 16 and cfg['physical_Ktile'] == 256
         and receipt['config'] == cfg and receipt['group_k'] == group_k
         and receipt['groups'] == GROUPS[group_k], name+' declared condition matches path/receipt')
    need(counts == receipt['counts'] and summary['end_slot'] == receipt['end_slot']
         and summary['events'] == receipt['events_checked'], name+' received totals')
    for key, value in counts.items():
        integer(value, name+' counts.'+key)
    need(integer(summary['end_slot'], name+' end_slot') > 0, name+' nonempty calendar')
    need(counts['wire_bytes'] == 16*counts['wire_beats']
         and counts['engine_wire_bytes'] == 16*counts['engine_wire_beats']
         and counts['engine_wire_bytes'] <= counts['wire_bytes']
         and counts['engine_packets'] <= counts['packets']
         and counts['engine_local_beats'] <= counts['src_beats']+counts['dst_beats'], name+' engine traffic is included subset')
    high = verify_inventory(summary)
    need(high == receipt['high_water_bytes'], name+' independently received high water')
    need(splice['common_R_trajectory_and_epochs_unchanged'] is True
         and splice['inserted_tokens'] == list(range(72)) and len(splice['removed']) == 288
         and len(splice['inherited']) == receipt['inherited_events_checked']
         and receipt['complete_replacement_tokens'] == 72, name+' complete bounded splice')
    need(receipt['source_receipts']['base_service']['sha256'] == task['base_service_receipt_sha256']
         and receipt['source_receipts']['grouped_math']['sha256'] == task['grouped_receipt_sha256'], name+' numeric/base receipt bindings')
    for key in COMMON_TASK:
        if key.endswith('_sha256'):
            hash_string(task[key], name+' task.'+key)
    # Final output RQ is the only new 32x32 / 64x32 microprogram. No early group RQ.
    n = 72*2560
    if group_k == 0:
        need(counts['wide_s8_product'] == n*25 and counts['wide_add64'] == n*24
             and counts['rq_rne64_complete'] == n and counts.get('rq_rne128_complete', 0) == 0
             and counts['constant_shift64'] == n*25 and counts['digit_byte_op'] == n*18, name+' complete g0 I64 product/RNE')
    else:
        need(counts['wide_s8_product'] == n*45 and counts['wide_add128'] == n*44
             and counts['rq_rne128_complete'] == n and counts.get('rq_rne64_complete', 0) == 0
             and counts['constant_shift128'] == n*45 and counts['digit_byte_op'] == n*26
             and counts['signextend_i32_i64'] == n*GROUPS[group_k], name+' complete grouped I128 product/RNE')
    evidence = {'name': name, 'result': str(folder), 'receipt': str(receipt_path),
                'manifest': descriptor(manifest_path), 'receipt_descriptor': descriptor(receipt_path),
                'artifacts': artifacts, 'producer_source': source, 'receiver_source': audit}
    return {'name': name, 'summary': summary, 'receipt': receipt, 'manifest': manifest,
            'splice': splice, 'evidence': evidence, 'artifacts': artifacts}


def case_metrics(case):
    s = case['summary']
    counts, inv = s['counts'], s['inventory']
    objects = {a['object']: {'bank': a['bank'], 'bytes': a['bytes'], 'offset': a['offset'],
                             'lifetime': a['lifetime']} for a in s['allocations'] if a['object'].startswith('gs.')}
    return {'name': case['name'], 'end_slots': s['end_slot'], 'events': s['events'],
            'wire_bytes_total_including_engine': counts['wire_bytes'],
            'engine_wire_bytes_subset_already_in_total': counts['engine_wire_bytes'],
            'non_engine_wire_bytes': counts['wire_bytes']-counts['engine_wire_bytes'],
            'wire_beats': counts['wire_beats'], 'packets': counts['packets'],
            'engine_operand_read_bytes': counts['engine_operand_read_bytes'],
            'engine_operand_write_bytes': counts['engine_operand_write_bytes'],
            'engine_local_beats': counts['engine_local_beats'],
            'counts': counts, 'bank_high_water_bytes': s['used_bytes'],
            'bank_capacities_bytes': inv['capacities'], 'grouped_retained_objects': objects,
            'endpoint_FIFO_inventory_bytes': inv['packet']['FIFO_bytes'],
            'VR8_declared_operand_staging_max_bytes': 1024,
            'full_RQ_operand_bundle_peak_bytes': 320 if s['task']['groups'] == 1 else 576,
            'error_reference_only_no_quality_acceptance': s['task']['reference_errors']}


def compare(root, receipt_root=None, suffix='02'):
    need(isinstance(suffix, str) and re.fullmatch('[0-9]+', suffix), 'numeric case suffix')
    receipt_root = root if receipt_root is None else receipt_root
    cases = {(g, p, l): read_case(root, receipt_root, g, p, l, suffix)
             for g in GROUPS for p in PLACEMENTS for l in LABELS}
    exemplar = cases[(0, 'near_m', 'split')]
    for case in cases.values():
        need(case['manifest']['source'] == exemplar['manifest']['source']
             and case['receipt']['source'] == exemplar['receipt']['source'], 'one frozen producer/helper/receiver source batch')
        need(case['summary']['inventory'] == exemplar['summary']['inventory']
             and case['summary']['allocations'] == exemplar['summary']['allocations']
             and case['summary']['used_bytes'] == exemplar['summary']['used_bytes'], 'all twelve conserve exact resource inventory and retained storage')
        need(all(case['summary']['task'][k] == exemplar['summary']['task'][k] for k in COMMON_TASK), 'shared frozen prefix/weights/compiler/cuts across groups')
        for key in ('base_service_artifacts', 'baseline_artifacts', 'compiled_artifacts'):
            need(case['receipt'][key] == exemplar['receipt'][key], 'common independently received '+key)
        need(case['artifacts']['splice.json'] == exemplar['artifacts']['splice.json'], 'one immutable inherited R/consumer splice')
    labels = []
    paired = []
    for group_k, group_count in GROUPS.items():
        for placement in PLACEMENTS:
            a, b = (cases[(group_k, placement, label)] for label in LABELS)
            need(scientific_summary(a['summary']) == scientific_summary(b['summary'])
                 and a['artifacts']['witness.jsonl.gz'] == b['artifacts']['witness.jsonl.gz']
                 and a['artifacts']['splice.json'] == b['artifacts']['splice.json'], 'split/shared label must not change scientific payload or calendar')
            labels.append({'group_k': group_k, 'placement': placement, 'status': 'BYTE_IDENTICAL_WITNESS_AND_SPLICE',
                           'end_slot_delta': b['summary']['end_slot']-a['summary']['end_slot'],
                           'scientific_summary_sha256': digest(scientific_summary(a['summary']))})
        a, b = (cases[(group_k, placement, 'split')] for placement in PLACEMENTS)
        sa, sb = a['summary'], b['summary']
        need(sa['task'] == sb['task'] and a['receipt']['grouped_artifacts'] == b['receipt']['grouped_artifacts'], 'same-g same exact numerical function/trajectory and independent numeric artifacts')
        ca, cb = sa['counts'], sb['counts']
        math_a = {k: v for k, v in ca.items() if k not in PLACEMENT_COSTS}
        math_b = {k: v for k, v in cb.items() if k not in PLACEMENT_COSTS}
        need(math_a == math_b, 'placement must preserve every arithmetic/wide/engine operand count')
        need(cb['copy_byte']-ca['copy_byte'] == 72*34, 'only documented V local descriptor copy is extra')
        # Every grouped partial is Otile16*I32=64B. V receives one 96B packet;
        # near-M instead receives one padded34B descriptor (80B wire) per token.
        expected_wire_delta = 72*160*group_count*96-72*80
        need(cb['wire_bytes']-ca['wire_bytes'] == expected_wire_delta, 'actual residency transfer delta matches partials minus descriptor packets')
        need(cb['payload_bytes']-ca['payload_bytes'] == 72*160*group_count*64-72*34,
             'physical partial/descriptor payload conservation')
        slots = sb['end_slot']-sa['end_slot']
        wire = cb['wire_bytes']-ca['wire_bytes']
        metadata = {'dynamic_group_delta_I16_useful_bytes': 72*group_count*2,
                    'common_delta_I16_bytes': 72*2,
                    'padded_descriptor_retained_bytes_per_endpoint': 64,
                    'actual_owner_descriptor_bytes_per_token': 34,
                    'near_M_descriptor_transfer_payload_bytes': 72*34,
                    'near_M_descriptor_transfer_wire_bytes': 72*80,
                    'shared_V_descriptor_local_copy_byte_ops': 72*34,
                    'static_Wscale_Q31_I16_per_output_unique_bytes': 2560*6,
                    'static_Wscale_Q31_I16_read_payload_bytes': 72*2560*6,
                    'static_Wscale_group_duplication_factor': 1,
                    'per_endpoint_RQ_meta_retained_bytes': 256,
                    'shared_V_complete_group_partial_payload_bytes': 72*160*group_count*64,
                    'shared_V_complete_group_partial_wire_bytes': 72*160*group_count*96}
        paired.append({'group_k': group_k, 'groups': group_count, 'status': 'SAME_FUNCTION_SAME_RESOURCES',
                       'near_m': case_metrics(a), 'shared_v': case_metrics(b),
                       'near_m_savings_vs_shared_v': {'end_slots': slots, 'end_slots_percent': 100*slots/sb['end_slot'],
                                                     'wire_bytes': wire, 'wire_bytes_percent': 100*wire/cb['wire_bytes'],
                                                     'denominator': 'shared_v full inherited-chain end slots / total wire'},
                       'metadata_and_partial_protocol': metadata,
                       'arithmetic_counts_sha256': digest(math_a),
                       'movement_count_deltas_shared_v_minus_near_m': {k: cb.get(k, 0)-ca.get(k, 0) for k in sorted(PLACEMENT_COSTS)}})
    return {'schema': 'grouped-service-comparison74-v1', 'status': 'PASS_BOUND_COMPARISON',
            'conditions_expected': 12, 'independent_receipts_pass': len(cases), 'case_suffix': suffix,
            'label_controls': labels, 'paired_comparisons': paired,
            'case_metrics': [case_metrics(case) for case in cases.values()],
            'input_evidence': [case['evidence'] for case in cases.values()], 'limits': LIMITS}


def run(root, out, receipt_root=None, suffix='02', source_commit=None):
    out = Path(out)
    # Validate before making an output directory; never reuse/overwrite one.
    need(not out.exists(), 'comparison output must be new')
    report = compare(root, receipt_root, suffix)
    out.mkdir(parents=True, exist_ok=False)
    source = {'compare_grouped_service_sha256': sha(__file__), 'commit': source_commit or 'UNSPECIFIED'}
    report['source'] = source
    put(out/'report.json', report)
    put(out/'manifest.json', {'schema': 'grouped-service-comparison-run74-v1', 'status': report['status'],
                              'source': source, 'artifacts': [{'path': 'report.json', **descriptor(out/'report.json')}]})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--receipt-root', type=Path, help='Defaults to root; contains audit-CASE/receipt.json')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--suffix', default='02')
    parser.add_argument('--source-commit', help='Commit containing this exact comparison source; no git or network subprocess is run')
    args = parser.parse_args()
    if args.source_commit:
        need(re.fullmatch('[0-9a-f]{40}', args.source_commit), 'source commit must be full SHA')
    report = run(args.root, args.out, args.receipt_root, args.suffix, args.source_commit)
    print(json.dumps({'status': report['status'], 'receipts': report['independent_receipts_pass'], 'out': str(args.out)}))


if __name__ == '__main__':
    main()
