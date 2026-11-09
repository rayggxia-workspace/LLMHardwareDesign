"""Classify actual selected scalar-record traffic; no ideal tiling speedup.

The same native command/ACK cost, layout and selected cache state are retained.
The unique-data comparison deliberately ignores capacity and is NOT an
executable plan, an attainable traffic bound for this loop order, or HBM bytes.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from column_shards import expand_selected
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost


def cached_reads(cache, row, *, immutable_weight=False):
    r, n, k = cache['rows'], cache['columns'], cache['K']
    ca, cb = cache['components']
    t = cache['stripe']
    e = row.get('evaluation', {})
    if cache.get('cost_model') == 'dot-prefix-state-v2':
        hit = e['reused_prefix']
    else:
        hit = t if row['cache_hit'] else 0
    if not 0 <= hit <= t <= k:
        raise ValueError('invalid selected cache interval')
    reads = {'A_prefix_fill': r*ca*(t-hit),
             'A_streamed_reloads': r*n*ca*cb*(k-t),
             'B_immutable_weights' if immutable_weight else 'B_dynamic': r*n*cb*k,
             'zero_packet': 1}
    comparison = {'unique_A_component_words_per_service_ignoring_capacity': r*ca*k,
                  'required_A_bytes_to_hold_complete_input_per_service': r*ca*k*16}
    if immutable_weight:
        # Only static 2D weight tensors have the proved cross-row sharing
        # counted here. General broadcasted dynamic matrices are excluded.
        comparison['unique_static_B_component_words_per_service_ignoring_capacity'] = n*cb*k
    return reads, comparison


def account(ir, plan):
    verify_cost(ir)
    source_tasks = ir['tasks']
    cover_audit = None
    if plan.get('kind') == 'convex-cover-frontier-v1':
        from verify_cover_frontier import project, verify as verify_cover
        from verify_resident_bindings import verify as verify_resident
        # Keep the registered native-source proof and the complete schedule
        # checks before diagnostic flattening. A cover is not an atomic task.
        verify_resident(ir, numeric=False)
        cover_audit = verify_cover(source_tasks, ir['hardware'], ir.get('resident_actions', []), plan)
        source_tasks, projected = project(source_tasks, ir.get('resident_actions', []), plan)
    else:
        verify(source_tasks, ir['hardware'], plan)
        projected = plan
    tasks, flat = expand_selected(source_tasks, projected)
    tasks = {t['id']:t for t in tasks}
    nodes = {n['id']:n for n in ir['primitive_program']['instructions']}
    weights = ir['model'].get('weights', {})
    totals = Counter()
    services = []
    for row in flat['tasks']:
        task = tasks[row['id']]
        binding = task['bindings'][0]
        evaluation = row.get('evaluation', {})
        reads = evaluation.get('external_read_words', binding['external_read_words'])
        if row.get('cache_hit') and 'external_read_words' not in evaluation:
            reads = binding['warm_read_words']
        writes = binding['external_write_words']
        c = binding.get('read_cache')
        if 'dot_tile' in binding:
            from tile_accounting import traffic
            read_classes,write_classes=traffic(binding)
            totals.update(read_classes);totals.update(write_classes)
        elif c:
            node = nodes[c['primitive']]
            weight = node['inputs'][1] in weights
            meta = ir['model'].get('values', {}).get(node['inputs'][1], {})
            shape = meta.get('shape', []) if weight else []
            classified, comparison = cached_reads(c, row, immutable_weight=weight)
            other = reads - sum(classified.values())
            if other < 0:
                raise ValueError('classified reads exceed independently checked selected traffic')
            classified['other_native_reads_within_cached_Dot'] = other
            # Do not report the 2D sharing comparison for batched weights.
            if weight and len(shape) != 2:
                comparison.pop('unique_static_B_component_words_per_service_ignoring_capacity', None)
            services.append({'id':row['id'], 'primitive':node['id'], 'site':c['site'],
                'input':node['inputs'][0], 'B':node['inputs'][1], 'static_B':weight,
                'rows':c['rows'], 'columns':c['columns'], 'K':c['K'],
                'capacity_words':ir['hardware']['sites'][c['site']]['words'],
                'selected_prefix':c['stripe'],
                'reused_prefix':evaluation.get('reused_prefix', c['stripe'] if row.get('cache_hit') else 0),
                'reads':classified, 'comparison_only':comparison})
            totals.update(classified)
            totals['cached_Dot_writes'] += writes
        elif binding.get('resident_region'):
            totals['resident_region_reads'] += reads
            totals['resident_region_writes'] += writes
        else:
            totals['other_service_reads'] += reads
            totals['other_service_writes'] += writes
    if sum(totals.values()) != plan['external_words']:
        raise ValueError('traffic classification does not conserve selected total')
    return {'passed':True, 'logical_scalar_record_words':dict(totals),
            'total_logical_words':sum(totals.values()),
            'logical_record_bytes':16, 'nominal_record_bytes':sum(totals.values())*16,
            'cached_Dot_services':len(services), 'services':services,
            'cover_audit':cover_audit,
            'scope':'selected conservative scalar-record descriptors, B1/S2 no-KV qualified scope unchanged',
            'not_proven':'physical DRAM transfers, complete controller/DMA tile integration, arbitrary dirty residency or token/s',
            'comparison_warning':'unique-data counts ignore finite S and live M contexts; never subtract them from cost',
            'unchanged':'actual selected kernels, arithmetic, SSA identity, S capacity, every final STORE/ACK and wire budget'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('ir', type=Path)
    p.add_argument('plan', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    result = account(json.loads(a.ir.read_text()), json.loads(a.plan.read_text()))
    result['inputs_sha256'] = {str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in (a.ir,a.plan)}
    result['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'services'}))


if __name__ == '__main__':
    main()
