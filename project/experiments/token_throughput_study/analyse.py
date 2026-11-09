"""Frozen-order sensitivity and conditional dense-decode capacity, not simulation.

No compiler, production RTL, or upstream worktree is imported or modified.
Whole-service contractions include copies; their factors are hypotheses.
"""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import heapq
import json
from pathlib import Path
import platform

HERE = Path(__file__).resolve().parent


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def checked_json(path, expected):
    if sha(path) != expected:
        raise ValueError('input SHA mismatch: ' + str(path))
    with Path(path).open() as stream:
        return json.load(stream)


def extract(source, probe, spec):
    """Independently rebuild the exact service/resource-order fixture of PR241."""
    ir_path = source / 'generated/ir.json'
    plan_path = source / 'generated/conditional-dp.json'
    ir = checked_json(ir_path, spec['ir_sha256'])
    plan = checked_json(plan_path, spec['plan_sha256'])
    checked_json(probe / 'generated/input-report.json', spec['probe_report_sha256'])
    if sha(probe / 'generated/tasks.txt') != spec['probe_tasks_sha256']:
        raise ValueError('upstream task fixture SHA mismatch')
    if plan['makespan'] != spec['plan_ticks'] or plan['external_words'] != spec['logical_records']:
        raise ValueError('frozen plan totals changed')
    rows = plan['tasks']
    ids = {row['id']: i for i, row in enumerate(rows)}
    if len(ids) != len(rows):
        raise ValueError('duplicate selected task')
    task_map = {task['id']: task for task in ir['tasks']}
    operations = {node['id']: node['op'] for node in ir['program']}
    nodes = []
    claims = {}
    for i, row in enumerate(rows):
        task = task_map[row['id']]
        matches = [b for b in task['bindings'] if b['id'] == row['binding']]
        if len(matches) != 1:
            raise ValueError('ambiguous binding')
        binding = matches[0]
        if binding.get('materialized_tile') or ('parallel_shards' in binding and 'phase_execution' not in binding):
            raise ValueError('fixture requires stage/shard extraction; refuse approximation')
        start, end = row['start'], row['end']
        if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end:
            raise ValueError('invalid interval')
        parents = {ids[p] for p in task.get('after', [])}
        resources = binding['resources']
        if len(set(resources)) != len(resources):
            raise ValueError('duplicate resource')
        for resource in resources:
            if ir['hardware']['resources'][resource] != 1:
                raise ValueError('fixture needs capacity-slot allocation')
            claims.setdefault(resource, []).append((start, end, i))
        nodes.append(dict(id=row['id'], op=operations[row['id']], duration=end-start,
                          parents=parents, resources=resources))
    for intervals in claims.values():
        intervals.sort()
        for previous, current in zip(intervals, intervals[1:]):
            if previous[1] > current[0]:
                raise ValueError('overlapping exclusive reservations')
            nodes[current[2]]['parents'].add(previous[2])
    for node in nodes:
        node['parents'] = sorted(node['parents'])
    # Equality of the serialized *complete graph*, not only its makespan.
    fixture = str(len(nodes)) + '\n' + ''.join(
        ' '.join(map(str, [node['duration'], len(node['parents']), *node['parents']])) + '\n'
        for node in nodes)
    if hashlib.sha256(fixture.encode()).hexdigest() != spec['probe_tasks_sha256']:
        raise ValueError('independent dependency/resource graph differs from PR241')
    return nodes, dict(source_inputs={str(ir_path): spec['ir_sha256'],
                                     str(plan_path): spec['plan_sha256']},
                       resource_counts=ir['hardware']['resources'],
                       memory_model=ir['hardware']['virtual_memory'],
                       logical_records=plan['external_words'],
                       selected_plan_ticks=plan['makespan'],
                       full_graph_matches_pr241=True)


def topology(nodes):
    children = [[] for _ in nodes]
    pending = []
    for i, node in enumerate(nodes):
        parents = node['parents']
        if len(set(parents)) != len(parents):
            raise ValueError('duplicate parent')
        pending.append(len(parents))
        for p in parents:
            if not isinstance(p, int) or not 0 <= p < len(nodes) or p == i:
                raise ValueError('invalid dependency')
            children[p].append(i)
    ready = [i for i, n in enumerate(pending) if n == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        current = heapq.heappop(ready)
        order.append(current)
        for child in children[current]:
            pending[child] -= 1
            if pending[child] == 0:
                heapq.heappush(ready, child)
    if len(order) != len(nodes):
        raise ValueError('cyclic graph')
    return order


def longest(nodes, factors=None):
    factors = factors or {}
    durations = []
    for node in nodes:
        duration = node['duration']
        if not isinstance(duration, int) or duration < 0:
            raise ValueError('invalid duration')
        scaled = duration * Fraction(factors.get(node['op'], 1))
        if scaled < 0:
            raise ValueError('negative contraction')
        durations.append((scaled.numerator + scaled.denominator - 1) // scaled.denominator)
    finish = [0] * len(nodes)
    predecessor = [None] * len(nodes)
    for i in topology(nodes):
        if nodes[i]['parents']:
            p = max(nodes[i]['parents'], key=lambda j: (finish[j], -j))
            predecessor[i] = p
            finish[i] = finish[p]
        finish[i] += durations[i]
    end = max(range(len(nodes)), key=lambda i: finish[i])
    ticks = finish[end]
    by_op = Counter()
    chain = []
    while end is not None:
        chain.append(end)
        by_op[nodes[end]['op']] += durations[end]
        end = predecessor[end]
    if sum(by_op.values()) != ticks:
        raise ValueError('critical-chain attribution not conserved')
    return dict(ticks=ticks, critical_chain_ticks_by_operator=dict(by_op),
                chain=list(reversed(chain)))


def decode_capacity(config, spec):
    h = config['hidden_size']
    q_heads, kv_heads = config['num_attention_heads'], config['num_key_value_heads']
    dim = config.get('head_dim', h // q_heads)
    if 'head_dim' not in config and h % q_heads:
        raise ValueError('head dimension not derivable')
    q, kv = q_heads * dim, kv_heads * dim
    ffn, layers = config['intermediate_size'], config['num_hidden_layers']
    per_layer = h*q + 2*h*kv + q*h + 3*h*ffn
    macs = layers*per_layer + h*config['vocab_size']
    if macs != spec['dense_macs_per_token']:
        raise ValueError('configuration and dense-work reference disagree')
    frequency, engines = spec['frequency_hz'], spec['m_count']
    ceilings = []
    for command in spec['commands']:
        # Grant perfect divisibility, load balancing and zero feeder overhead.
        products = command['k'] * command['n']
        rate = Fraction(engines * frequency * products, command['interval'] * macs)
        ceilings.append(dict(**command, optimistic_linear_token_s_ceiling=float(rate),
                             exact_ceiling=[rate.numerator, rate.denominator],
                             scope='dense linear work only; operands already resident; not decode simulation'))
    traffic = []
    for context in (128, 512, 2048):
        kv_bytes = 2*layers*kv*context*2
        attention_macs = 2*layers*q*context
        traffic.append(dict(context=context, s16_kv_read_bytes_ideal_gqa_reuse=kv_bytes,
                            attention_macs=attention_macs))
    payload = []
    for bits in (16, 8, 4):
        weight_bytes = Fraction(macs*bits, 8)
        payload.append(dict(bits=bits, weight_stream_bytes_per_token=float(weight_bytes),
                            required_GB_s_at_5_token_s=float(weight_bytes*5/10**9),
                            required_GB_s_at_10_token_s=float(weight_bytes*10/10**9)))
    return dict(dense_linear_macs_per_token=macs, per_layer_macs=per_layer,
                ceilings=ceilings, ideal_weight_stream_payload=payload, kv=traffic,
                low_bit_quality_qualified=False, physical_memory_bandwidth_known=False,
                scope='configuration-derived necessary/opportunity bounds, not token generation')


def descriptor_sweep():
    # PR182-derived cold descriptor example, not DDR or system calibration.
    # Reproduce only the supplied endpoints; do not invent intermediate timings.
    return dict(single_64_total_ticks=64*20, contiguous_64_ticks=287,
                isolated_speedup=64*20/287, saved_ticks=64*20-287,
                basis='PR241 S-access=3 cold-descriptor endpoints',
                scope='isolated abstract transfer example; contiguity and command support must be proven')


def run(nodes, spec, config):
    baseline = longest(nodes)
    if baseline['ticks'] != spec['plan_ticks']:
        raise ValueError('baseline makespan mismatch')
    scenarios = [
        ('dot_half', {'Dot': Fraction(1, 2)}),
        ('pointwise_half', {'Product': Fraction(1, 2), 'Add': Fraction(1, 2)}),
        ('dot_and_pointwise_half', dict.fromkeys(('Dot', 'Product', 'Add'), Fraction(1, 2))),
        ('add_ffn_ratio_hypothesis', {'Add': Fraction(632654644, 901467136)}),
        ('dot_zero_ideal', {'Dot': 0}),
        ('pointwise_zero_ideal', {'Product': 0, 'Add': 0}),
        ('dot_and_pointwise_zero_ideal', dict.fromkeys(('Dot', 'Product', 'Add'), 0)),
    ]
    results = []
    for name, factors in scenarios:
        result = longest(nodes, factors)
        if result['ticks'] > baseline['ticks']:
            raise ValueError('contraction increased makespan')
        result.pop('chain')
        result.update(name=name, whole_service_factors={k: str(v) for k, v in factors.items()},
                      model_speedup=baseline['ticks']/result['ticks'],
                      conditional_prefill_token_s=spec['tokens']*spec['frequency_hz']/result['ticks'],
                      qualification='fixed bindings/resource order, hypothetical full-service costs; no new executable plan')
        results.append(result)
    return dict(baseline=dict(ticks=baseline['ticks'],
                    critical_chain_ticks_by_operator=baseline['critical_chain_ticks_by_operator'],
                    service_counts=dict(Counter(n['op'] for n in nodes)),
                    seconds_if_300MHz_cycle=baseline['ticks']/spec['frequency_hz'],
                    conditional_prefill_token_s=spec['tokens']*spec['frequency_hz']/baseline['ticks']),
                sensitivity=results, decode=decode_capacity(config, spec), descriptor=descriptor_sweep(),
                scope='research sensitivity, not calibrated SystemC/RTL, decode throughput, energy or physical qualification')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    spec = json.loads((HERE/'study.json').read_text())
    config = checked_json(HERE/'qwen2.5-3b-config.json', spec['config_sha256'])
    nodes, provenance = extract(args.source, args.probe, spec)
    (args.out/'graph.json').write_text(json.dumps(nodes, separators=(',', ':'))+'\n')
    result = run(nodes, spec, config)
    result.update(provenance=provenance, python_version=platform.python_version(),
                  graph_sha256=sha(args.out/'graph.json'),
                  source_sha256={p.name: sha(p) for p in HERE.iterdir() if p.is_file()},
                  code_commit=json.loads((args.out.parent/'inputs.json').read_text())['source_commit']
                  if (args.out.parent/'inputs.json').exists() else '待核实')
    (args.out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: result[key] for key in ('baseline', 'decode', 'descriptor')}))


if __name__ == '__main__':
    main()
