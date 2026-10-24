"""Independent metadata/byte comparison of the complete Issue76 service batch.

No producer, receiver, microprogram, tensor library or old closure import.
Numeric/physical validity is inherited from exact, source-bound independent
receipts; this tool rehashes artifacts and checks controlled comparisons.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

LAYERS = (0, 13)
TILES = (128, 256, 1536)
PLACEMENTS = ('near_m', 'shared_v')
LABELS = ('split', 'shared')
PHASES = ('front', 'down', 'norm')
REVISION = 'a02780686e08a03fe0d2679a293b5c74a90efa89'
OPS = {'mul_s32_s32', 'mul_s64_s32', 'mul_s32_u16', 'add_s64', 'sub_s64', 'add_u128',
       'abs_s64', 'cmp_s64', 'max_s64', 'align_s32_i64', 'signextend_s16_i64',
       'shl_s64_s128', 'shl_u128', 'rne_s64_i32', 'rne_s128_i32',
       'udiv_u128', 'isqrt_u128', 'div_rne_s128_u64_i32'}
INSTRUCTIONS = {'COPY', 'ADD', 'SUB', 'MULS8', 'SHL', 'SHR', 'OR', 'AND', 'XOR', 'CMP', 'MUX', 'CTRL'}
PROFILE_COUNTS = {'matrix_S8_MACs', 'matrix_issued_cycles', 'matrix_resets', 'ROM_word32_reads'}
QUALIFICATION = 'CONDITIONAL_MICROPROGRAM_SERVICE_NOT_FULL_RTL_OR_PPA'
NEGATIVES = {'port', 'capacity', 'numeric', 'widthfee', 'ROM'}
LIMITS = [
    'Comparison PASS inherits the exact independent numeric/physical/micro receipts; this tool does not rerun tensor or calendar arithmetic.',
    'All denominators are the frozen norm/router-cut to complete nextnorm service, not an entire model or real cached-decode schedule.',
    'RTL byte-core one-edge actions and synchronous ROM32 latency2/II1 are functional calibration; one dispatch/action remains a candidate controller surcharge.',
    'Full wide FSM, RF/backing implementation, macro timing, physical locality, STA/PPA and model quality are not accepted here.',
    'Scalar carry dependencies never divide by8; frame initialization, result extraction, byte-store and caller IO remain in service counts.',
    'Same-function placement and window comparisons keep numeric trajectory/precision/resources fixed; labels are byte-identical controls.',
    'Complete1536 S64 merge may be feasible by phase reuse and streaming O16 output; the old49152B full8xS32-in-V proposal remains capacity rejected.',
    'Byte/micro traffic is already included in total wire; derived subsets must not be added again.'
]


def need(ok, message):
    if not ok: raise ValueError(message)


def load(path):
    with Path(path).open(encoding='utf-8') as stream: return json.load(stream)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): h.update(block)
    return h.hexdigest()


def desc(path):
    return {'bytes': Path(path).stat().st_size, 'sha256': sha(path)}


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def put(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False); stream.write('\n')


def integer(value, label):
    need(type(value) is int and value >= 0, 'nonnegative integer '+label)
    return value


def hash_string(value, label):
    need(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'SHA-256 '+label)


def verify_manifest(folder, schema, status):
    folder = Path(folder); m = load(folder/'manifest.json')
    need(m['schema'] == schema and m['status'] == status, 'typed manifest execution '+str(folder))
    artifacts = {}
    for record in m['artifacts']:
        name = record['path']
        need(isinstance(name, str) and Path(name).name == name and name not in artifacts, 'unique artifact basename')
        path = folder/name
        need(path.resolve().parent == folder.resolve(), 'artifact containment')
        actual = desc(path)
        need(actual == {'bytes': record['bytes'], 'sha256': record['sha256']}, 'actual artifact SHA/size '+str(path))
        artifacts[name] = actual
    return m, artifacts


def integer_profile(counts):
    return {k: v for k, v in counts.items() if k.startswith('op.') or k in PROFILE_COUNTS}


def active_phases(a):
    life = a['lifetime']
    if life == ['task_start', 'task_end']: return set(PHASES)
    need(isinstance(life, dict) and life['kind'] == 'token_phase' and life['every_token'] is True
         and life['barriers'] == 'front -> down -> norm -> next_token'
         and set(life['phases']) <= set(PHASES) and life['phases'], 'explicit legal phase lifetime')
    return set(life['phases'])


def allocation_proof(summary):
    caps = summary['inventory']['capacities']; regions = {}; highs = {}; phase = {}
    names = set()
    for a in summary['allocations']:
        name, bank = a['object'], a['bank']; start = integer(a['offset'], name+' offset'); n = integer(a['bytes'], name+' bytes')
        need(name not in names and bank in caps and start+n <= caps[bank], 'unique bounded allocation '+name); names.add(name)
        phases = active_phases(a)
        for lo, hi, lifetime in regions.setdefault(bank, []):
            need(not (phases & lifetime) or start+n <= lo or start >= hi, 'overlapping live phase allocation')
        regions[bank].append((start, start+n, phases)); highs[bank] = max(highs.get(bank, 0), start+n)
        for p in phases: phase.setdefault(bank, {})[p] = max(phase.get(bank, {}).get(p, 0), start+n)
    need(highs == summary['used_bytes'], 'actual all-phase bank high water')
    expected_phase = {bank: {p: phase.get(bank, {}).get(p, 0) for p in PHASES} for bank in ('M', 'V')}
    need(summary['phase_peak_bytes'] == expected_phase, 'actual phase high water and reuse')
    merge = next(a for a in summary['allocations'] if a['object'] == 'down.merge64')
    owner = 'M' if summary['config']['placement'] == 'near_m' else 'V'
    need(merge['bank'] == owner and merge['bytes'] == summary['config']['tile']*8
         and active_phases(merge) == {'down'}, 'real finite S64 merge window')
    objects = {a['object']: a for a in summary['allocations']}
    need(objects['V.microframe']['bytes'] == 512 and objects['V.byte_regs']['bytes'] >= 5, 'finite micro frame/register storage')
    rom_reserve = sum(a['bytes'] for a in summary['allocations'] if a['bank'] == 'ROM')
    need(rom_reserve == 131072, 'actual ROM128KiB including unused word padding')
    return {'high_water_bytes': highs, 'phase_peak_bytes': expected_phase, 'ROM_reserved_bytes': rom_reserve,
            'merge_window_bytes': merge['bytes'], 'merge_owner': owner}


def inventory_proof(inv):
    caps = inv['capacities']; expected = {'M': 32768, 'V': 16384, 'R': 32768, 'EXT': 134217728, 'ROM': 4260100,
                                        **{'S'+str(i): 32768 for i in range(8)}}
    need(caps == expected, 'fixed macro capacities')
    need(set(inv['banks']) == set(caps)-{'ROM'} and all(p == {'bits': 128, 'kind': '1RW'} for p in inv['banks'].values()), 'fixed128bit1RW banks')
    matrix = inv['matrix']
    need(matrix['S8_PEs'] == 256 and matrix['shape'] == [16, 16] and matrix['effective_B1_PEs'] == 16
         and matrix['Ktile'] == 512 and matrix['weight_bytes'] == 8192, 'fixed M256 physical16x512 service')
    need(inv['vector']['byte_lanes'] == 8 and inv['SFU']['count'] == 1
         and inv['SFU']['borrows'] == 'VR8 lane0' and inv['SFU']['extra_byte_ALU'] is False, 'no donated vector/SFU ALU')
    rom = inv['ROM']; need(rom['capacity'] == caps['ROM'] and rom['return_bits'] == 32 and rom['ports'] == 1
                           and rom['latency'] == 2 and rom['II'] == 1 and rom['synchronous_candidate'] is True, 'bound synchronous ROM candidate')
    need(inv['packet'] == {'BUS_count': 1, 'BUS_bits': 128, 'beat_bytes': 16, 'header_bytes': 32,
                          'max_payload_bytes': 1984, 'FIFO_bytes': 2048}, 'fixed BUS/FIFO inventory')


def scientific(summary):
    result = copy.deepcopy(summary); result['config'].pop('label')
    for key in ('environment', 'elapsed_seconds', 'observer'): result.pop(key, None)
    return result


def read_case(root, layer, tile, placement, label, suffix):
    name = f'service-l{layer}-t{tile}-{placement}-{label}{suffix}'
    folder = Path(root)/name; receipt_path = Path(root)/('audit-'+name)/'receipt.json'
    m, artifacts = verify_manifest(folder, 'granite-service-run76-v1', 'EXECUTED_CONDITIONAL_SERVICE')
    need({'summary.json', 'row_hashes.json', 'witness.jsonl.gz'} <= set(artifacts), 'complete service artifacts')
    r = load(receipt_path); s = load(folder/'summary.json'); t = s['task']; cfg = s['config']; c = s['counts']
    need(r['schema'] == 'granite-service-independent76-v1' and r['status'] == 'PASS_FINITE_SERVICE', 'independent finite-service PASS '+name)
    need(r['producer_manifest'] == desc(folder/'manifest.json') and r['artifacts'] == artifacts, 'exact independent receipt/artifact binding')
    need(s['schema'] == 'granite-service76-v1' and t['layer'] == layer and cfg['tile'] == tile
         and cfg['placement'] == placement and cfg['label'] == label, 'declared condition/path scope')
    need(r['config'] == {'layer': layer, 'tile': tile, 'placement': placement, 'label': label}, 'received condition identity')
    need(t['router_bits'] == 16 and t['split'] == 'evaluation' and t['tokens'] == 72
         and t['model_revision'] == REVISION and t['source_bound_numeric_status'] == 'PASS'
         and t['source_bound_micro_status'] == 'PASS', 'frozen real complete integer cut')
    need(s['unknown_fees'] == [] and s['qualification'] == QUALIFICATION, 'unknown/unqualified costs cannot rank')
    for k, v in c.items(): integer(v, 'counts.'+k)
    need(c == r['counts'] and s['end_slot'] == r['end_time'] and integer(s['end_slot'], 'end_slot') > 0, 'received service totals')
    need(c['wire_bytes'] == 16*c['wire_beats'] and c['micro_dispatch_cycles'] == c['micro_alu_cycles'], 'wire units and separate candidate dispatch')
    need(c['matrix_S8_MACs'] == 72*8*(1024*1536+1536*512), 'all actual selected complete-K matrix MACs')
    need(all(k[3:] in OPS for k in c if k.startswith('op.')), 'no unpriced typed arithmetic')
    frame_bytes = c['micro_frame_read_bytes']+c['micro_frame_write_bytes']
    need(48*frame_bytes <= c['wire_bytes'], 'micro traffic already included in total wire')
    row_hashes = load(folder/'row_hashes.json')
    need(t['row_hashes_sha256'] == sha(folder/'row_hashes.json')
         and r['numeric_row_hashes_sha256'] == canonical(row_hashes)
         and r['integer_profile_sha256'] == canonical(integer_profile(c))
         and r['inventory_sha256'] == canonical(s['inventory'])
         and r['allocations_sha256'] == canonical(s['allocations']), 'canonical numeric/math/resource receipt proofs')
    inventory_proof(s['inventory']); allocation = allocation_proof(s)
    need(r['peak_bytes'] == s['used_bytes'] and r['phase_lifetime_checked'] is True
         and r['fullH_s64_merge_bytes'] == 12288, 'independent phase/complete-merge qualification')
    capacity = s['capacity']
    need(capacity['full8S32_return_bytes'] == 49152 and capacity['full_H_merge64_bytes'] == 12288
         and capacity['no_full_Q12_return_co_resident'] is True and capacity['owner_physical_RQ_elements'] == 16, 'streamed physical O16 return versus logical merge')
    need(r['full8S32_V_rejection'] == {'bytes': 49152, 'capacity': 16384, 'status': 'REJECTED'}, 'old full8S32 capacity negative')
    need(r['negative_status'] == 'PASS_ACTUAL_SHA_REWRITE' and len(r['negative_tests']) == 5
         and {v['name'] for v in r['negative_tests']} == NEGATIVES
         and all(v['status'] == 'REJECTED_AFTER_SHA_REWRITE' for v in r['negative_tests']), 'five real semantic negatives required')
    for field in ('numeric_manifest', 'compiled_manifest', 'packed_manifest', 'calibration_manifest',
                  'numeric_receipt', 'packed_receipt', 'calibration_receipt'):
        hash_string(t[field+'_sha256'], 'task.'+field)
        need(r[field]['sha256'] == t[field+'_sha256'], 'source descriptor '+field)
    hash_string(t['numeric_trajectory_sha256'], 'numeric trajectory')
    source = m['source']; need(re.fullmatch('[0-9a-f]{40}', source['commit']) and source['service_sha256'] == m['producer_sha256'], 'frozen service source')
    evidence = {'case': name, 'manifest': desc(folder/'manifest.json'), 'receipt': desc(receipt_path),
                'artifacts': artifacts, 'producer_source': source, 'receiver_source': r['source']}
    return {'name': name, 'folder': folder, 'summary': s, 'receipt': r, 'manifest': m, 'artifacts': artifacts,
            'row_hashes': row_hashes, 'allocation': allocation, 'evidence': evidence}


def find_bound(root, basename, wanted_sha):
    matches = [p for p in Path(root).glob('*/'+basename) if sha(p) == wanted_sha]
    need(len(matches) == 1, 'unique current-root byte-bound '+basename)
    return matches[0]


def calibration_proof(root, task):
    path = find_bound(root, 'manifest.json', task['calibration_manifest_sha256']); folder = path.parent
    manifest, artifacts = verify_manifest(folder, 'micro-calibration-run76-v1', 'PASS_BYTE_CORE_AND_WIDE_MICROPROGRAM')
    receipt_path = find_bound(root, 'receipt.json', task['calibration_receipt_sha256']); receipt = load(receipt_path)
    need(receipt['schema'] == 'micro-independent-receipt76-v1' and receipt['status'] == 'PASS_MICRO_CAUSAL_BYTE_AND_ROM'
         and receipt['service_all_keys_qualified'] is True and receipt['typed_keys'] == 18
         and receipt['producer_manifest'] == desc(path) and receipt['artifacts'] == artifacts, 'formal eighteen-key micro receipt')
    table = load(folder/'cost_table.json'); report = load(folder/'report.json'); rtl = load(folder/'rtl_report.json')
    need(task['calibration_cost_table_sha256'] == sha(folder/'cost_table.json')
         and receipt['cost_table'] == desc(folder/'cost_table.json') and table['schema'] == 'micro-cost-table76-v1'
         and table['level'] == 'BYTE_ALU_RTL_REPLAY_WITH_SOFTWARE_CONTROLLER'
         and table['source'] == manifest['source'] == report['source'], 'full actual cost table source binding')
    need(set(table['ops']) == OPS, 'all required typed widths, including S16 conversion')
    inv = table['inventory']; rom = inv['ROM']
    need(inv['VR8_lanes'] == 8 and inv['SFU_count'] == 1 and inv['SFU_uses_VR8_lane0'] is True
         and inv['scalar_frame_bytes'] == 512 and inv['operand_register_bytes_per_active_lane'] == 5, 'same finite micro resources')
    need(rom == {'word_bits': 32, 'latency_cycles': 2, 'II_cycles': 1, 'ports': 1, 'depth_words': 32768, 'capacity_bytes': 131072}, 'actual single ROM candidate inventory')
    for op, item in table['ops'].items():
        costs, proof = item['costs'], item['proof']
        for key in ('scalar_ALU_dependency_cycles', 'software_controller_dispatches', 'conservative_scalar_cycles_ALU_plus_dispatch', 'scratch_peak_bytes'):
            integer(costs[key], 'micro '+op+' '+key)
        for key, value in costs['primitive_counts'].items(): integer(value, 'byte opcode '+key)
        need(item['domain_bound_status'] == 'FIXED_DATA_INDEPENDENT_TOPOLOGY_EXHAUSTIVE_SHIFT'
             and proof['kind'] == 'fixed_loops_exhaustive_shift_domain' and proof['source_sha256'] == table['source']['micro_sha256'], 'qualified complete control-domain bound '+op)
        domain = list(range(64 if op == 'align_s32_i64' else 128 if op.startswith('shl_') else 129)) if op.startswith(('rne_', 'shl_')) or op == 'align_s32_i64' else [0]
        need(proof['domain'] == domain and costs['SIMD8_qualified'] is False and costs['frame_capacity_bytes'] == 512
             and costs['scratch_peak_bytes'] <= 512, 'no sampled bound or free SIMD '+op)
        need(set(costs['primitive_counts']) == INSTRUCTIONS and sum(costs['primitive_counts'].values()) == costs['scalar_ALU_dependency_cycles']
             and costs['software_controller_dispatches'] == costs['scalar_ALU_dependency_cycles']
             and costs['conservative_scalar_cycles_ALU_plus_dispatch'] == costs['scalar_ALU_dependency_cycles']+costs['software_controller_dispatches'], 'separate ALU and candidate controller costs')
        for k in ('input_load_bytes', 'result_read_bytes', 'byte_store_reads', 'byte_store_writes'):
            integer(costs[k], 'micro '+op+' '+k)
        if op.startswith('mul_'):
            need(costs['primitive_counts']['MULS8'] == {'mul_s32_s32': 25, 'mul_s64_s32': 45, 'mul_s32_u16': 15}[op], 'full S8 digit products')
    need(report['full_wide_RTL_FSM'] is False and rtl == report['RTL']
         and rtl['status'] == 'PASS_BYTE_CORE_RTL_REPLAY' and rtl['ALU_latency_edges'] == 1
         and rtl['ROM_word_bits'] == 32 and rtl['ROM_ports'] == 1
         and rtl['ROM_latency_cycles'] == 2 and rtl['ROM_II_cycles'] == 1
         and rtl['actions'] == receipt['actions'] and rtl['cases'] == receipt['cases'], 'actual byte RTL evidence separated from wide software control')
    rom_actual = report['ROM']
    need(rom_actual['used_bytes'] == 73736 and rom_actual['reserved_bytes'] == 131072
         and rom_actual['ROM_file_sha256'] == artifacts['rom.hex']['sha256']
         and rom_actual['requests_sha256'] == artifacts['rom.requests']['sha256'], 'actual original LUT words, padding and request file binding')
    return {'directory': str(folder), 'manifest': desc(path), 'receipt': desc(receipt_path),
            'cost_table': desc(folder/'cost_table.json'), 'typed_keys': 18, 'ROM_used_bytes': 73736,
            'ROM_reserved_bytes': 131072, 'ROM_global_pool_bytes': 4260100, 'RTL': rtl,
            'controller_dispatch_level': 'candidate one/action; not full-FSM RTL',
            'SIMD8_qualified': False, 'source': table['source'],
            'typed_costs': {op: item['costs'] for op, item in table['ops'].items()}}


def metrics(case):
    s, r = case['summary'], case['receipt']; c = s['counts']; frame = c['micro_frame_read_bytes']+c['micro_frame_write_bytes']
    return {'case': case['name'], 'layer': s['task']['layer'], 'config': s['config'], 'end_slots': s['end_slot'],
            'wire_bytes_total': c['wire_bytes'], 'micro_wire_bytes_subset_already_in_total': 48*frame,
            'non_micro_wire_bytes': c['wire_bytes']-48*frame, 'counts': c, 'capacity': s['capacity'],
            'allocation_proof': case['allocation'], 'integer_profile_sha256': r['integer_profile_sha256'],
            'numeric_trajectory_sha256': s['task']['numeric_trajectory_sha256'],
            'numeric_row_hashes_sha256': r['numeric_row_hashes_sha256']}


def compare(root, suffix='01'):
    need(re.fullmatch('[0-9]+', suffix), 'numeric complete-batch suffix')
    cases = {(layer, tile, p, label): read_case(root, layer, tile, p, label, suffix)
             for layer in LAYERS for tile in TILES for p in PLACEMENTS for label in LABELS}
    exemplar = cases[(0, 128, 'near_m', 'split')]
    calibration = calibration_proof(root, exemplar['summary']['task'])
    common = ('compiled_manifest_sha256', 'calibration_manifest_sha256', 'calibration_cost_table_sha256', 'calibration_receipt_sha256', 'model_revision')
    for case in cases.values():
        s = case['summary']; counts = s['counts']; costs = calibration['typed_costs']
        expected = {
            'micro_alu_cycles': sum(counts.get('op.'+op, 0)*value['scalar_ALU_dependency_cycles'] for op, value in costs.items()),
            'micro_dispatch_cycles': sum(counts.get('op.'+op, 0)*value['software_controller_dispatches'] for op, value in costs.items()),
            'micro_frame_read_bytes': sum(counts.get('op.'+op, 0)*(value['byte_store_reads']+value['result_read_bytes']) for op, value in costs.items()),
            'micro_frame_write_bytes': sum(counts.get('op.'+op, 0)*(value['byte_store_writes']+value['input_load_bytes']) for op, value in costs.items())}
        need(all(counts[k] == value for k, value in expected.items()), 'complete eighteen-key weighted micro fees, including initialization/extract')
        need(case['manifest']['source'] == exemplar['manifest']['source'] and case['receipt']['source'] == exemplar['receipt']['source'], 'one frozen service/receiver source batch')
        need(s['inventory'] == exemplar['summary']['inventory'] and all(s['task'][k] == exemplar['summary']['task'][k] for k in common), 'same exact inventory/compiler/micro calibration batch')
    pairs, labels, windows = [], [], []
    for layer in LAYERS:
        ref = cases[(layer, 128, 'near_m', 'split')]
        for tile in TILES:
            for p in PLACEMENTS:
                a, b = (cases[(layer, tile, p, label)] for label in LABELS)
                need(scientific(a['summary']) == scientific(b['summary'])
                     and all(a['artifacts'][k] == b['artifacts'][k] for k in ('witness.jsonl.gz', 'row_hashes.json')), 'label cannot change scientific payload/calendar')
                labels.append({'layer': layer, 'tile': tile, 'placement': p, 'status': 'BYTE_IDENTICAL_WITNESS_AND_NUMERIC_ROWS',
                               'end_slot_delta': b['summary']['end_slot']-a['summary']['end_slot'],
                               'scientific_summary_sha256': canonical(scientific(a['summary']))})
            a, b = (cases[(layer, tile, p, 'split')] for p in PLACEMENTS)
            sa, sb = a['summary'], b['summary']
            need(sa['task'] == sb['task'] == ref['summary']['task']
                 and a['row_hashes'] == b['row_hashes'] == ref['row_hashes'], 'same-layer complete consumers and exact same numerical function across windows/placements')
            need(integer_profile(sa['counts']) == integer_profile(sb['counts']) == integer_profile(ref['summary']['counts']), 'all typed wide arithmetic/MAC/ROM operations conserved')
            ca, cb = sa['counts'], sb['counts']
            for k in ('micro_alu_cycles', 'micro_dispatch_cycles', 'micro_frame_read_bytes', 'micro_frame_write_bytes'):
                need(ca[k] == cb[k] == ref['summary']['counts'][k], 'same full microprogram workload '+k)
            slot_delta, wire_delta = sb['end_slot']-sa['end_slot'], cb['wire_bytes']-ca['wire_bytes']
            pairs.append({'layer': layer, 'tile': tile, 'status': 'SAME_FUNCTION_SAME_INVENTORY', 'near_m': metrics(a), 'shared_v': metrics(b),
                          'near_m_savings_vs_shared_v': {'end_slots': slot_delta, 'end_slots_percent': 100*slot_delta/sb['end_slot'],
                                                        'wire_bytes': wire_delta, 'wire_bytes_percent': 100*wire_delta/cb['wire_bytes'],
                                                        'denominator': 'same layer/window shared_V complete cut-to-nextnorm service, not whole model'}})
        for p in PLACEMENTS:
            base = cases[(layer, 128, p, 'split')]['summary']
            windows.append({'layer': layer, 'placement': p, 'comparison': 'same numeric function; logical merge window with physical O16/K512 fixed',
                            'relative_to_tile128': [{'tile': tile, 'end_slot_delta': cases[(layer, tile, p, 'split')]['summary']['end_slot']-base['end_slot'],
                                                    'end_slot_percent': 100*(cases[(layer, tile, p, 'split')]['summary']['end_slot']-base['end_slot'])/base['end_slot']} for tile in TILES]})
    return {'schema': 'granite-service-comparison76-v1', 'status': 'PASS_BOUND_FINITE_SERVICE_COMPARISON',
            'case_suffix': suffix, 'conditions_expected': 24, 'independent_receipts_pass': 24,
            'calibration': calibration, 'label_controls': labels, 'paired_placements': pairs, 'window_comparisons': windows,
            'full1536_merge': [metrics(cases[(layer, 1536, p, label)]) for layer in LAYERS for p in PLACEMENTS for label in LABELS],
            'old_full8S32_in_V': {'status': 'REJECTED', 'bytes': 49152, 'capacity': 16384},
            'case_metrics': [metrics(v) for v in cases.values()], 'input_evidence': [v['evidence'] for v in cases.values()], 'limits': LIMITS}


def run(root, out, source_commit=None, suffix='01'):
    out = Path(out); need(not out.exists(), 'output directory must be new')
    report = compare(root, suffix); out.mkdir(parents=True, exist_ok=False)
    source = {'commit': source_commit or 'UNSPECIFIED', 'compare_service76_sha256': sha(__file__)}
    report['source'] = source; put(out/'report.json', report)
    put(out/'manifest.json', {'schema': 'granite-service-comparison-run76-v1', 'status': report['status'], 'source': source,
                              'artifacts': [{'path': 'report.json', **desc(out/'report.json')}]})
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--source-commit'); p.add_argument('--suffix', default='01'); args = p.parse_args()
    if args.source_commit: need(re.fullmatch('[0-9a-f]{40}', args.source_commit), 'full comparison commit SHA')
    report = run(args.root, args.out, args.source_commit, args.suffix)
    print(json.dumps({'status': report['status'], 'receipts': report['independent_receipts_pass'], 'out': str(args.out)}))


if __name__ == '__main__': main()
