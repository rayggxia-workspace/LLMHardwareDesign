"""Independent Issue64 service receipt; no producer import or scheduling.

These are conditional feasible portable-PV64/O16 service schedules, not B's
PV32 numeric qualification, native FP outputs, an optimum or physical speedup.
"""
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import itertools
import json
from pathlib import Path


GROUPS = {'gemma_local0': (2, 256, 1024), 'gemma_global5': (2, 256, None),
          'qwen25_global0': (8, 128, None), 'qwen35_global3': (4, 256, None)}
ORGS = ('split', 'colocated_control', 'colocated_stream')
POLICIES = ('fifo', 'critical')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def ceil(n, d):
    return (n+d-1)//d


def spans(events, name):
    ordered = sorted(e for e in events if e[1] > e[0])
    require(all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), 'overlap: '+name)


def formula(c):
    H, d, window = GROUPS[c['group']]
    T, q, b = c['keys'], c['queries'], c['kv_bits']//8
    digits = 1 if b == 1 else 3
    return {'heads': H, 'score_elements': H*q*T,
            'valid_elements': H*(q*T-q*(q-1)//2),
            'QK_matrix_calls': H*(T//16)*digits,
            'PV_matrix_calls': H*(d//16)*(T//128)*3*digits,
            'K_backing_bytes': H*T*d*b, 'V_backing_bytes': H*T*d*b,
            'Q_backing_bytes': H*q*d, 'result_bytes': H*q*8,
            'output_elements': H*q*d, 'GQA_KV_reload_factor': H,
            'Psum_guard_bytes_per_active_query': 4, 'exp_passes': 2,
            'PV_S8_products': 3*digits}


def config_check(c):
    require(c['group'] in GROUPS, 'group')
    H, d, window = GROUPS[c['group']]
    require(c['keys'] in (128, 1024) and c['queries'] in (1, 4), 'shape')
    require(c['kv_bits'] in (8, 16) and c['exp_ii'] in (1, 8, 32), 'format/service')
    require(c['organization'] in ORGS, 'organization')
    require((c['heads'], c['dim'], c['window']) == (H, d, window), 'group descriptor')
    require(c['lut_step'] in (128, 256), 'LUT grid')
    require(c['LUT_ROM_bytes'] == (16*c['lut_step']+1)*4, 'LUT closed interval bytes')
    require(c['ROM_capacity_bytes'] >= c['LUT_ROM_bytes'], 'LUT ROM capacity')
    require(c['queries']*c['keys']*4 <= 32768, 'single-head score32 spill capacity')


def case_key(row):
    c = row['config']
    return (c['group'], c['keys'], c['queries'], c['kv_bits'], c['exp_ii'], c['organization'], row['policy'])


def check_manifest(root):
    m = load(root/'manifest.json')
    require(m['status'] == 'PASS' and m['schema'] == 'conditional-attention-service/1', 'manifest status/schema')
    require(m['cases'] == 576 and m['optimized_pairs'] == 96, 'manifest dimensions')
    require(m['hardware_performance_accepted'] is False and m['numeric_quality_accepted'] is False, 'evidence layer')
    require(m['source_verification']['status'] == 'VERIFIED', 'unverified source binding')
    binding = m['binding']
    require(binding['source_commit'] == m['source_commit'], 'source commit binding')
    require(binding.get('service_sha256', binding.get('code_sha256')) == m['code_sha256'] == m['source_verification']['code_sha256'], 'source code SHA binding')
    require(binding['dependency_sha256'] == m['dependency_sha256'] == m['source_verification']['dependency_sha256'], 'dependency SHA binding')
    actual = {p.name for p in root.iterdir() if p.is_file() and p.name != 'manifest.json'}
    require(actual == set(m['files']), 'unindexed or missing files')
    for name, row in m['files'].items():
        p = (root/name).resolve()
        require(p.is_relative_to(root.resolve()), 'artifact path')
        require(p.stat().st_size == row['bytes'] and sha(p) == row['sha256'], 'artifact SHA/size: '+name)
    return m


def check_protocol(p):
    inv = p['inventory']
    require(inv['matrix_private_bytes'] == 32768 and inv['attention_private_bytes'] == 32768, 'private capacities')
    require(sum(inv['matrix_private_banks'].values()) + inv['matrix_PE_register_bytes'] == 32768, 'M total')
    require(inv['S_banks'] == 8 and inv['S_bytes_each'] == 32768 and inv['S_ports_each'] == 'one 128-bit RW', 'S bank inventory')
    require(inv['buses'] == 1 and inv['link_bits'] == 128 and inv['fifo_bytes'] == 2048 and inv['payload_limit'] == 1984, 'fabric inventory')
    require(inv['LUT_read_ports'] == 1 and inv['LUT_ROM_bytes'] == 8196 and inv['ROM_capacity_bytes'] == 20480, 'single ROM/capacity')
    require('64 cycles' in inv['divide_service'], 'U64 divider service missing')
    require('PV64' in p['precision'] and 'O16' in p['precision'] and 'score I32Q12' in p['precision'], 'portable service precision')
    require('not globally optimal' in p['scheduler'], 'optimality boundary missing')
    require([(r['required'], r['capacity']) for r in p['unsupported_old_inventory']] == [(8196, 8192), (16388, 16384)], 'ROM rejection records')
    for phase, objects in p['scratch_allocations'].items():
        spans([(v[0], v[0]+v[1]) for v in objects.values()], 'scratch '+phase)
        require(all(v[0] >= 0 and v[0]+v[1] <= 32768 for v in objects.values()), 'scratch capacity '+phase)
    # Last-q4/1024 is per-head16KiB score32, not a full GQA score fit.
    require(4*1024*4 == 16384, 'score32 assertion')


def check_cases(cases, pairs):
    require(len(cases) == 576 and len(pairs) == 96, 'case/pair count')
    lookup = {}
    for row in cases:
        c = row['config']; config_check(c)
        require(c['lut_step'] == 128 and c['ROM_capacity_bytes'] == 20480, 'frozen case ROM profile')
        key = case_key(row)
        require(key not in lookup and row['policy'] in POLICIES, 'duplicate case')
        lookup[key] = row
        expected = formula(c)
        require(row['expected'] == expected, 'declared expected work differs from independent formula')
        o = row['operations']; H, d, _ = GROUPS[c['group']]
        digits = 1 if c['kv_bits'] == 8 else 3
        require(o['matrix_calls'] == expected['QK_matrix_calls'] + expected['PV_matrix_calls'], 'matrix calls')
        require(o['S8_MACs'] == 4*H*c['queries']*c['keys']*d*digits, 'S8 MAC work')
        require(o['LUT_reads'] == 2*expected['valid_elements'] and o['normalize_divisions'] == expected['valid_elements'], 'exp/div work')
        require(o['score delta33 subtract_elements'] == o['LUT_reads'] and o['exp delta clamp/index_elements'] == o['LUT_reads'], 'exp address cost')
        require(row['hardware_performance_accepted'] is False and row['numeric_quality_accepted'] is False, 'case evidence layer')
    domain = list(itertools.product(GROUPS, (128, 1024), (1, 4), (8, 16), (1, 8, 32)))
    require(set(lookup) == {key+(org, policy) for key in domain for org in ORGS for policy in POLICIES}, 'missing Cartesian cases')
    pairs_lookup = {(r['group'], r['keys'], r['queries'], r['kv_bits'], r['exp_ii']): r for r in pairs}
    require(len(pairs_lookup) == 96 and set(pairs_lookup) == set(domain), 'pair keys')
    for key in domain:
        for policy in POLICIES:
            a, control, stream = [lookup[key+(org, policy)] for org in ORGS]
            require(a['cycles'] == control['cycles'] and a['traffic'] == control['traffic'] and a['busy'] == control['busy'], 'colocation label changed service')
            require(a['expected'] == stream['expected'] and a['operations'] == stream['operations'], 'stream changed work')
            at, st = a['traffic'], stream['traffic']
            require(all(at[k] == st[k] for k in ('memory_logical', 'memory_physical', 'wire_payload')), 'stream changed memory/payload work')
            require(at['wire']-st['wire'] == at['header']-st['header'] >= 0, 'stream reduction beyond headers')
            require(all(st[k] <= at[k] for k in st if k.startswith('wire_')), 'stream added unexplained traffic')
        best = {org: min((lookup[key+(org, p)] for p in POLICIES), key=lambda r: r['cycles']) for org in ORGS}
        old = pairs_lookup[key]
        require(old['optimized_split'] == best['split']['cycles'] and old['optimized_control'] == best['colocated_control']['cycles']
                and old['optimized_stream'] == best['colocated_stream']['cycles'], 'pair optimized cycles')
        require(old['chosen_policies'] == {org: r['policy'] for org, r in best.items()}, 'pair chosen policy/tie order')
        reduction = (best['split']['cycles']-best['colocated_stream']['cycles'])/best['split']['cycles']
        require(abs(old['stream_reduction_fraction']-reduction) < 1e-15, 'pair fraction')
        require(old['stream_wire_bytes_saved'] == best['split']['traffic']['wire']-best['colocated_stream']['traffic']['wire'], 'pair wire')
    return lookup


def check_schedule(w):
    """Independent intervals, address spans, packets, credits and traffic."""
    nodes, sizes, result = w['nodes'], w['sizes'], w['scheduled']
    trace = {int(k): v for k, v in result['trace'].items()}
    require(set(trace) == set(range(len(nodes))), 'schedule node coverage')
    resources, busy, traffic = defaultdict(list), Counter(), Counter()
    operations = Counter()
    for index, n in enumerate(nodes):
        require(n['id'] == index and len(n['resources']) == len(set(n['resources'])), 'node ID/resources')
        start, end = trace[index]
        require(type(start) is int and type(end) is int and start >= 0 and end-start == n['duration'], 'duration/span')
        require(n['duration'] >= 0 and (n['duration'] > 0 or not n['resources']), 'zero resource reservation')
        require(all(type(d) is int and 0 <= d < index and trace[d][1] <= start for d in n['deps']), 'dependency timing')
        for resource in n['resources']:
            resources[resource].append((start, end, index)); busy[resource] += end-start
        if 'port' in n:
            port, off, count = n['port'], n['offset'], n['bytes']
            require(port in sizes and port in n['resources'] and count > 0 and off >= 0 and off+count <= sizes[port], 'memory span/resource')
            require(n['duration'] == ceil(off%16+count, 16), 'physical1RW memory duration')
            require(bool(n['deps']), 'memory lacks producer/dependency')
            traffic['memory_logical'] += count; traffic['memory_physical'] += ceil(off%16+count, 16)*16
        if 'pack_elements' in n:
            e, digits, ops = n['pack_elements'], n['pack_digits'], n['pack_scalar_ops']
            require(set(n['resources']) == {'AC', 'vector', 'control'}, 'pack ports/control')
            require(n['duration'] == e*(1+digits+ops) and digits in (1, 3) and ops == (1 if digits == 1 else 6), 'pack service')
            require(n['pack_destination_offset']+n['pack_destination_bytes'] <= sizes['AC'] and n['pack_source_offset']+n['pack_source_bytes'] <= sizes['AC'], 'pack capacity')
            require(n['pack_destination_bytes'] == e*digits and n['pack_source_bytes'] == e*(1 if digits == 1 else 2), 'pack bytes')
            traffic['memory_logical'] += n['pack_source_bytes']+n['pack_destination_bytes']
            traffic['memory_physical'] += e*(1+digits)*16
            operations[n['label']+'_elements'] += e
        if 'a_port' in n:
            a, b = n['a_port'], n['w_port']
            r, k, col = n['rows'], n['reduction'], n['columns']
            require({'matrix', a, b} == set(n['resources']), 'matrix feed ports')
            require(n['a_offset']+r*k <= sizes[a] and n['w_offset']+col*k <= sizes[b], 'matrix operand capacity')
            require(n['duration'] == k+r+col-2 and n['operand_read_bytes'] == (r+col)*k, 'array feed service')
            operations['matrix_calls'] += 1; operations['S8_MACs'] += r*k*col
            operations['matrix_operand_bytes'] += (r+col)*k
        if 'elements' in n:
            if n['label'] == 'exp LUT one read port':
                require(set(n['resources']) == {'sfu', 'LUT'}, 'ROM/SFU resource')
                require(n['duration'] == n['elements']*w['config']['exp_ii'], 'ROM serial service')
                operations['LUT_reads'] += n['elements']
            elif n['label'] == 'U64 restoring normalize divide':
                require(set(n['resources']) == {'sfu', 'wide'} and n['duration'] == n['elements']*64 and n['iterations'] == 64, 'U64 divider64 cost')
                operations['normalize_divisions'] += n['elements']
            else:
                operations[n['label']+'_elements'] += n['elements']
    for resource, events in resources.items():
        spans(events, resource)
    require(dict(busy) == result['busy'], 'busy counters')
    require(max(t[1] for t in trace.values()) == result['cycles'], 'makespan')
    fifo, wire_ids = defaultdict(list), set()
    packets = w['packets']+w['streams']
    for p in packets:
        length, header = p['payload'], p['header_bytes']
        require(0 < length <= 1984 and header in (0, 64), 'packet payload/header limit')
        wire_n = header + ceil(length, 64)*64
        require(p['wire_bytes'] == wire_n and wire_n <= 2048, '2KiB packet credit')
        if header == 0:
            require(w['config']['organization'] == 'colocated_stream' and p['src'] in ('A', 'M') and p['dst'] in ('A0', 'A1', 'M0', 'M1'), 'unqualified stream')
        read, wire, write = (nodes[p[key]] for key in ('read', 'wire', 'write'))
        require(read['bytes'] == length and write['bytes'] == length, 'packet byte spans')
        require(set(wire['resources']) == {'bus', p['src']+'TX', p['dst']+'RX'}, 'packet bus/endpoint resource')
        require(p['read'] in wire['deps'] and p['wire'] in write['deps'], 'packet memory dependency')
        require(wire['duration'] == wire_n//16 and wire['payload'] == length and wire['header_bytes'] == header and wire['wire_bytes'] == wire_n and wire['kind'] == p['kind'], 'packet metadata/wire time')
        require(p['wire'] not in wire_ids, 'duplicate packet wire'); wire_ids.add(p['wire'])
        fifo[(p['src'], 'TX')].append((trace[p['read']][0], trace[p['wire']][1]))
        fifo[(p['dst'], 'RX')].append((trace[p['wire']][0], trace[p['write']][1]))
        traffic['wire'] += wire_n; traffic['wire_payload'] += length
        traffic['wire_'+p['kind']] += wire_n; traffic['header'] += header
    require(wire_ids == {n['id'] for n in nodes if 'wire_bytes' in n}, 'unaccounted wire nodes')
    for endpoint, events in fifo.items():
        spans(events, str(endpoint)+' credit')
    spans([(trace[l['start']][0], trace[l['end']][1]) for l in w['leases']], 'scratch leases')
    return dict(traffic), dict(operations)


def check_semantics(w, traffic, operations, compact):
    c = w['config']; config_check(c); e = formula(c)
    require(w['expected'] == e, 'witness expected shape/work')
    require(traffic == compact['traffic'] and operations == compact['operations'], 'witness counters vs compact case')
    require(w['scheduled']['cycles'] == compact['cycles'] and w['scheduled']['busy'] == compact['busy'], 'witness schedule vs case')
    require(len(w['leases']) == e['heads'], 'head lease count')
    nodes, packets = w['nodes'], w['packets']+w['streams']
    for i, lease in enumerate(w['leases']):
        require(lease['kind'] == 'attention_head' and lease['slot'] == 0 and
                nodes[lease['start']]['label'] == 'head scratch lease begin' and
                nodes[lease['start']]['head'] == i, 'head scratch lease identity')
    require(sum(n['label'] == 'PV O64 initialize' for n in nodes) == e['heads']*(c['dim']//16), 'portable O64 accumulation allocation')
    require(sum(n['label'] == 'QK S8 limb' for n in nodes) == e['QK_matrix_calls'], 'QK GQA/limbs')
    require(sum(n['label'] == 'PV S8 limb' for n in nodes) == e['PV_matrix_calls'], 'PV GQA/limbs')
    for kind, expected in [('Kraw', e['K_backing_bytes']), ('Vraw_feature_major', e['V_backing_bytes']), ('Q8', e['Q_backing_bytes']), ('RESULT64', e['result_bytes'])]:
        require(sum(p['payload'] for p in packets if p['kind'] == kind and (p['src'] == 'EXT' or kind == 'RESULT64')) == expected, 'backing bytes '+kind)
    require(sum(p['payload'] for p in packets if p['kind'] == 'SCORE32Q12') == e['score_elements']*4, 'score32 spill bytes')
    for kind in ['SCORE_SUM_PASS', 'SCORE_NORMALIZE_PASS']:
        require(sum(p['payload'] for p in packets if p['kind'] == kind) == e['valid_elements']*4, 'score32 pass bytes '+kind)
    publish = [n for n in nodes if n['label'] == 'P15 profile/epoch publish after guard']
    budgets = [32768+ceil(c['keys']-c['queries']+r+1, 2)+1 for r in range(c['queries'])]
    require(len(publish) == e['heads'] and all(n['budget'] == budgets for n in publish), 'Psum/epoch guards')


def matching_cases(w, lookup, traffic, operations):
    """Find compatible case records without inventing a missing trace policy."""
    c = w['config']
    prefix = (c['group'], c['keys'], c['queries'], c['kv_bits'], c['exp_ii'], c['organization'])
    matches = []
    for policy in POLICIES:
        row = lookup[prefix+(policy,)]
        if (row['cycles'] == w['scheduled']['cycles'] and row['busy'] == w['scheduled']['busy']
                and row['traffic'] == traffic and row['operations'] == operations):
            matches.append(row)
    require(bool(matches), 'witness does not match any same-configuration case statistics')
    return matches


def negative_checks(w, compact):
    def verify(x):
        traffic, operations = check_schedule(x)
        check_semantics(x, traffic, operations, compact)
    outcomes = {}
    for kind in ['memory_dependency', 'packet_payload', 'remove_bus', 'score_byte_record']:
        mutated = copy.deepcopy(w); packet = mutated['packets'][0]
        if kind == 'memory_dependency':
            mutated['nodes'][packet['write']]['deps'] = []
        elif kind == 'packet_payload':
            packet['payload'] += 1
        elif kind == 'remove_bus':
            mutated['nodes'][packet['wire']]['resources'].remove('bus')
        else:
            mutated['expected']['score_elements'] -= 1
        try:
            verify(mutated)
        except (ValueError, KeyError) as exc:
            outcomes[kind] = 'REJECTED: '+str(exc)
        else:
            raise ValueError('negative mutation escaped: '+kind)
    return outcomes


def self_test():
    # Hand-written three-stage packet, not a producer fixture or scheduler call.
    nodes = [dict(id=0, label='start', duration=1, resources=['control'], deps=[]),
             dict(id=1, label='read', duration=1, resources=['S0'], deps=[0], port='S0', bytes=16, offset=0, write=False),
             dict(id=2, label='wire X', duration=8, resources=['bus', 'MTX', 'A0RX'], deps=[1], payload=16, wire_bytes=128, header_bytes=64, kind='X'),
             dict(id=3, label='write', duration=1, resources=['AC'], deps=[2], port='AC', bytes=16, offset=0, write=True)]
    packet = dict(kind='X', src='M', dst='A0', payload=16, wire_bytes=128, header_bytes=64, read=1, wire=2, write=3)
    w = dict(config={'organization': 'split'}, nodes=nodes, sizes={'S0': 32768, 'AC': 32768}, packets=[packet], streams=[], leases=[],
             scheduled=dict(trace={'0': [0, 1], '1': [1, 2], '2': [2, 10], '3': [10, 11]}, busy={'control': 1, 'S0': 1, 'bus': 8, 'MTX': 8, 'A0RX': 8, 'AC': 1}, cycles=11))
    traffic, _ = check_schedule(w)
    require(traffic['wire'] == 128 and traffic['memory_physical'] == 32, 'synthetic positive')
    rejected = 0
    for edit in ('dependency', 'payload', 'bus'):
        m = copy.deepcopy(w)
        if edit == 'dependency': m['nodes'][3]['deps'] = []
        if edit == 'payload': m['packets'][0]['payload'] = 17
        if edit == 'bus': m['nodes'][2]['resources'].remove('bus')
        try: check_schedule(m)
        except ValueError: rejected += 1
    require(rejected == 3, 'synthetic negatives')
    # schedule() does not save policy: identical statistics must retain both
    # possible policies, rather than assigning the producer's usual policy.
    m = copy.deepcopy(w)
    m['config'] = dict(group='gemma_local0', keys=128, queries=1, kv_bits=16,
                       exp_ii=8, organization='split')
    traffic, operations = check_schedule(m)
    prefix = ('gemma_local0', 128, 1, 16, 8, 'split')
    lookup = {prefix+(policy,): dict(policy=policy, cycles=11, busy=m['scheduled']['busy'],
                                      traffic=traffic, operations=operations) for policy in POLICIES}
    compatible = matching_cases(m, lookup, traffic, operations)
    require([r['policy'] for r in compatible] == list(POLICIES), 'missing/ambiguous policy handling')
    return {'positive_packet': 'PASS', 'negative_mutations_rejected': rejected,
            'missing_policy_ambiguity_retained': [r['policy'] for r in compatible]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path)
    p.add_argument('--out', type=Path)
    p.add_argument('--self-test', action='store_true')
    a = p.parse_args()
    if a.self_test:
        print(json.dumps(self_test())); return
    require(a.input is not None and a.out is not None, '--input/--out required')
    require(not a.out.exists(), 'refuse existing receipt/output')
    roots = [a.input/'service01', a.input/'service02']
    manifests = [check_manifest(root) for root in roots]
    require(set(manifests[0]['files']) == set(manifests[1]['files']), 'two-round file set')
    for field in ['source_commit', 'code_sha256', 'dependency_sha256', 'source_verification']:
        require(manifests[0][field] == manifests[1][field], 'two-round source binding '+field)
    for name in manifests[0]['files']:
        require((roots[0]/name).read_bytes() == (roots[1]/name).read_bytes(), 'two-round byte mismatch '+name)
    check_protocol(load(roots[0]/'protocol.json'))
    lookup = check_cases(load(roots[0]/'cases.json'), load(roots[0]/'pairs.json'))
    witnesses, negative = {}, None
    require(len(manifests[0]['witnesses']) == 3, 'three witnesses required')
    for name in manifests[0]['witnesses']:
        w = load(roots[0]/name)
        traffic, operations = check_schedule(w)
        compatible = matching_cases(w, lookup, traffic, operations)
        for compact in compatible:
            check_semantics(w, traffic, operations, compact)
        witnesses[name] = {'nodes': len(w['nodes']), 'packets': len(w['packets']),
                           'streams': len(w['streams']), 'leases': len(w['leases']), 'status': 'PASS',
                           'statistics_matching_policies': [r['policy'] for r in compatible],
                           'policy_identified_uniquely_from_statistics': len(compatible) == 1,
                           'policy_scope': 'case statistics compatibility; no policy field exists in the trace, so this does not authenticate the scheduling algorithm'}
        if negative is None:
            negative = negative_checks(w, compatible[0])
    receipt = dict(status='PASS', independent=True, auditor_sha256=sha(__file__), source_commit=manifests[0]['source_commit'],
                   source_snapshot_verification='binding/source SHA fields checked for consistency; original frozen code snapshot verification remains a separate intake check',
                   case_rows_checked=576, reconstructed_policy_pairs=96, rounds_byte_identical_files=len(manifests[0]['files']),
                   manifests=[{'path': str(root/'manifest.json'), 'sha256': sha(root/'manifest.json')} for root in roots],
                   witnesses=witnesses, negative_mutations=negative, synthetic_self_test=self_test(),
                   evidence_boundary=__doc__, hardware_performance_accepted=False, numeric_quality_accepted=False)
    output = a.out if a.out.suffix == '.json' else a.out/'receipt.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2)+'\n', newline='\n')
    print(json.dumps({'status': 'PASS', 'cases': 576, 'pairs': 96, 'witnesses': 3, 'receipt': str(output)}))


if __name__ == '__main__':
    main()
