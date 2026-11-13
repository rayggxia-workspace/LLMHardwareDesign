"""Compare tiled cache movement for a receipt-verified integer decode layer."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from run import compile_event_ir


def decode_geometry(program, layer):
    prefix = f'/model/model/layers.{layer}/self_attn/'
    instructions = [node for node in program['instructions'] if node['kernel'].startswith(prefix)]
    by_id = {node['id']: node for node in instructions}
    dots = {node['kernel'][len(prefix):]: node for node in instructions if node['op'] == 'Dot'}
    qk, pv = dots['MatMul'], dots['MatMul_1']
    _, heads, _, length = qk['shape']
    dimension = qk['attributes']['length']
    _, kv_heads, past, _ = program['runtime_formats'][f'past_{layer}_k']['shape']
    if (kv_heads != 2 or heads != 16 or dimension != 128 or past <= 0 or length != past + 1
            or qk['shape'] != [1, heads, 1, length] or pv['shape'] != [1, heads, 1, dimension]
            or pv['attributes']['length'] != length):
        raise ValueError('unsupported cached decode attention')
    for kind in ('k', 'v'):
        previous = program['runtime_formats'][f'past_{layer}_{kind}']
        updated = program['output_formats'][f'next_{layer}_{kind}']
        if (previous != {'shape': [1, kv_heads, past, dimension], 'bits': 32, 'exponent': -20}
                or updated != {**previous, 'shape': [1, kv_heads, length, dimension]}):
            raise ValueError('unsupported cache format or shape')
        (convert,) = [n for n in instructions if n['inputs'] == [f'past_{layer}_{kind}']]
        (concat,) = [n for n in instructions if n['op'] == 'Concat' and convert['id'] in n['inputs']]
        if (convert['op'] != 'Convert' or concat['attributes']['axis'] != -2
                or concat['shape'] != updated['shape']):
            raise ValueError('cache history does not feed the expected concatenate')
        operand = by_id[(qk if kind == 'k' else pv)['inputs'][1]]
        while operand['op'] == 'View':
            operand = by_id[operand['inputs'][0]]
        if operand is not concat:
            raise ValueError('cache history does not reach the expected attention operand')
    reductions = {node['op']: node for node in instructions if node['kernel'] == prefix + 'Softmax'
                  and node['op'] in ('Max', 'Sum')}
    def ancestors(value):
        found = set()
        pending = [value]
        while pending:
            key = pending.pop()
            if key not in found and key in by_id:
                found.add(key)
                pending.extend(by_id[key]['inputs'])
        return found

    if (set(reductions) != {'Max', 'Sum'}
            or any(n['attributes']['length'] != length for n in reductions.values())
            or qk['id'] not in ancestors(reductions['Max']['id'])
            or reductions['Max']['id'] not in ancestors(reductions['Sum']['id'])
            or reductions['Sum']['id'] not in ancestors(pv['inputs'][0])):
        raise ValueError('unsupported cached decode attention')
    return kv_heads, heads // kv_heads, past, dimension


def typed_route(src, dst, client, port):
    return {'src': src, 'dst': dst, 'claims': {port: 1}, 'setup': 0, 'bytes_per_tick': 64,
            'typed_dma': {'client': client, 'record_beats': 2},
            'phases': {'issue': {'ticks': 1, 'claims': {}}, 'ack': {'ticks': 2, 'claims': {port: 1}},
                       'hold_claims': {}}}


def problem(geometry, *, tile, write_release=None, write_channel=0, post_write_work=0,
            append_start=None, window_past=None):
    kv_heads, group, past, dimension = geometry
    row = dimension * 4
    if (tile < 1 or row % 128 or write_channel not in (0, 1) or post_write_work < 0
            or post_write_work and write_release is None):
        raise ValueError('unsupported tile or row alignment')
    sites = {name: {'words': 1024, 'bytes': 16384} for name in ('P0', 'P1', 'P2', 'C', 'U')}
    resources = dict.fromkeys(('dot', 'norm', 'acc', 'operand-context', *(site + '.S' for site in sites)), 1)
    windows, sizes, addresses, resident, services = {}, {}, {}, {}, {}
    historical = set()
    used = dict.fromkeys(sites, 0)

    def allocate(window, site, size):
        windows[window] = {'site': site, 'offset': used[site], 'bytes': size}
        used[site] += size

    def stage(name, ticks, claims=(), *, inputs=None, outputs=None, **options):
        services[name] = {'ticks': ticks, 'claims': dict.fromkeys(claims, 1)}
        return {'service': name, 'inputs': inputs or {}, 'outputs': outputs or {}, **options}

    def dot_stage(name, ticks, claims, inputs, outputs):
        def port_phase(kind, operands):
            port = dict.fromkeys((windows[w]['site'] + '.S' for w in operands), 1)
            return {'kind': kind, 'claims': port,
                    'ticks': sum((sizes[v] + 63) // 64 for v in operands.values())}

        # Reserve the local port while capturing the tile and publishing it.
        # The modeled operand context remains owned through compute and write.
        phases = [port_phase('capture', inputs), {'kind': 'compute', 'ticks': ticks,
                                                  'claims': dict.fromkeys(claims, 1)},
                  port_phase('write', outputs)]
        result = stage(name, sum(p['ticks'] for p in phases), inputs=inputs, outputs=outputs)
        services[name].update(phases=phases, hold_claims={'operand-context': 1},
                              window_phases={'read': 'capture', 'write': 'write', 'publish': 'write',
                                             'result_hold': 'operand-context'})
        return result

    def binding(name, stages):
        return {'id': name, 'site': 'P0', 'ticks': sum(services[s['service']]['ticks'] for s in stages),
                'resources': [], 'nets': [], 'scratch_words': 0, 'event_stages': stages}

    # Reserve 96 bits per output element and align each buffer as a whole. No S32
    # narrowing between tiles, and no overlapping live SSA storage windows.
    accumulator_bytes = dimension * group * 12
    for slot in range(2):
        allocate(f'cache-{slot}', 'P0', row * tile)
        allocate(f'pv-state-{slot}', f'P{slot + 1}', accumulator_bytes)
    separate = append_start is not None
    base = past if append_start is None else append_start
    maximum = past if window_past is None else window_past
    if not 0 < base <= past <= maximum:
        raise ValueError('invalid history allocation')

    def current(name, head):
        return f'{name}-h{head}' if separate and name != 'query' else name

    allocate('query', 'P0', row * group)
    for name in ('current-k', 'current-v'):
        for head in range(kv_heads if separate else 1):
            allocate(current(name, head), 'P0', row)
    base_chunks = [(start, min(tile, base - start)) for start in range(0, base, tile)]
    chunks = base_chunks + [(start, 1) for start in range(base, past + 1)]
    for i, (_, count) in enumerate(base_chunks + [(start, 1) for start in range(base, maximum + 1)]):
        size = count * group * 4
        for name, site in (('score', 'C'), ('prob', 'U')):
            allocate(f'{name}-{i}', site if used[site] + size <= sites[site]['bytes'] else 'P0', size)
    if write_release is not None:
        allocate('older-write', 'P0', 2048)
        resident['older-write'] = 'older-write'
        sizes['older-write'] = 2048
        addresses['older-write'] = 0x100000 + write_channel * 2048
    if any(used[site] > sites[site]['bytes'] for site in sites):
        raise ValueError('attention tile or score row exceeds finite SRAM')

    stages = []
    results = []
    stream_base = 0x200000
    stream_stride = ((maximum + int(separate)) * row + 4095) // 4096 * 4096
    for head in range(kv_heads):
        for name in ('query', 'current-k', 'current-v'):
            value = f'{name}-{head}'
            sizes[value] = windows[current(name, head)]['bytes']
        if head == 0:
            resident.update({current(name, head): f'{name}-{head}' for name in ('query', 'current-k', 'current-v')})
        else:
            # Projection and RoPE delivery are outside this comparison.
            stages.append(stage(f'provide-{head}', 1, ('P0.S',),
                                outputs={current(name, head): f'{name}-{head}'
                                         for name in ('query', 'current-k', 'current-v')}))
        scores, probabilities = {}, {}
        for kind in ('k', 'v'):
            previous = {}
            for i, (start, count) in enumerate(chunks):
                value = f'h{head}-{kind}-{start}'
                if start == past:
                    window = current('current-' + kind, head)
                    value = f'current-{kind}-{head}'
                    if separate:
                        stream = 2 * head + (kind == 'v')
                        addresses[value] = stream_base + stream * stream_stride + start * row
                else:
                    window = f'cache-{i % 2}'
                    stream = 2 * head + (kind == 'v')
                    addresses[value] = stream_base + stream * stream_stride + start * row
                    sizes[value] = count * row
                    historical.add(value)
                inputs = {window: value}
                if kind == 'k':
                    score = f'h{head}-score-{i}'
                    scores[f'score-{i}'] = score
                    sizes[score] = count * group * 4
                    inputs['query'] = f'query-{head}'
                    outputs = {f'score-{i}': score}
                    claims = ('dot',)
                else:
                    inputs.update(previous)
                    inputs[f'prob-{i}'] = probabilities[f'prob-{i}']
                    result = f'h{head}-partial-{i}'
                    sizes[result] = accumulator_bytes
                    outputs = {f'pv-state-{i % 2}': result}
                    previous = outputs
                    claims = ('dot', 'acc')
                # Explicit modeled service times. PV accumulates in history order
                # and does its only narrowing in the final stage.
                stages.append(dot_stage(f'h{head}-{kind}-{i}', 2 + group * count, claims, inputs, outputs))
            if kind == 'k':
                probabilities = {f'prob-{i}': f'h{head}-prob-{i}' for i in range(len(chunks))}
                sizes.update({v: windows[w]['bytes'] for w, v in probabilities.items()})
                ports = tuple(sorted({windows[w]['site'] + '.S' for w in scores.keys() | probabilities.keys()}))
                stages.append(stage(f'h{head}-softmax', group * (past + 1), ('norm', *ports),
                                    inputs=scores, outputs=probabilities))
        result = f'h{head}-result'
        result_site = f'P{head + 1}'
        allocate(result, result_site, row * group)
        sizes[result] = row * group
        results.append(result)
        final_ports = {windows[w]['site'] + '.S' for w in previous.keys() | {result}}
        stages.append(stage(f'h{head}-final', group, ('dot', 'acc', *sorted(final_ports)),
                            inputs=previous, outputs={result: result}))
    if any(used[site] > sites[site]['bytes'] for site in sites):
        raise ValueError('attention accumulator and output exceed finite SRAM')

    loads = [dict(s, prefetch=[w for w in s['inputs'] if w.startswith('cache-')])
             if i and any(w.startswith('cache-') for w in s['inputs']) else s for i, s in enumerate(stages)]
    candidates = [binding('serial', stages), binding('lookahead', loads)]
    tasks = [{'id': 'attention', 'bindings': candidates}]
    routes = {'load-history': typed_route('DDR', 'P0', 4, 'P0.S')}
    if write_release is not None:
        older = [stage('wait-release', write_release),
                 stage('write', 1, inputs={'older-write': 'older-write'}, persist=['older-write'])]
        tasks.insert(0, {'id': 'older-write', 'bindings': [binding('older-write', older)]})
        routes['store-old'] = typed_route('P0', 'DDR', 3, 'P0.S')
        if post_write_work:
            successor = stage('write-dependent-work', post_write_work)
            tasks.append({'id': 'write-dependent-work', 'after': ['older-write'],
                          'bindings': [binding('write-dependent-work', [successor])]})
    initial = sorted(historical)
    return {'tasks': tasks}, {'sites': sites, 'resources': resources, 'nets': {}, 'event_model': {
        'kind': 'qualified-event-model-v1', 'timing': 'replay', 'windows': windows,
        'value_bytes': sizes, 'initial_copies': resident, 'initial_backing': initial, 'live_out': results,
        'routes': routes, 'services': services, 'typed_dma': {
            'return_latency': [7, 8], 'mixed': {'queue': 4, 'write_latency': 9}, 'addresses': addresses},
    }}


def check_plan(plan, hardware, expected, expected_bytes):
    row = next(r for r in plan['tasks'] if r['id'] == 'attention')
    events = row['evaluation']['events']
    moves = [e for e in events if e['kind'] == 'move']
    spec = hardware['event_model']
    if len(moves) != len(expected) or {e['value'] for e in moves} != expected:
        raise ValueError('schedule skipped or duplicated a historical cache tile')
    if row['evaluation']['external_read_bytes'] != expected_bytes:
        raise ValueError('schedule read the wrong cache byte count')
    for move in moves:
        value = move['value']
        start = spec['typed_dma']['addresses'][value]
        if sorted(b['address'] for b in move['dma_beats']) != list(range(start, start + spec['value_bytes'][value], 64)):
            raise ValueError('schedule read the wrong physical cache beats')
    old = next((r for r in plan['tasks'] if r['id'] == 'older-write'), None)
    return {'binding': row['binding'], 'cycles': plan['makespan'], 'attention_end': row['end'],
            'old_end': old['end'] if old else None, 'read_bytes': plan['external_read_bytes'],
            'write_bytes': plan['external_write_bytes'], 'cache_loads': len(moves),
            'early_loads': sum(e.get('prefetch', False) and e['start'] < events[i - 1]['end']
                               for i, e in enumerate(events) if i and e['kind'] == 'move')}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('receipt_directory', type=Path)
    cli.add_argument('--layer', type=int, default=0)
    cli.add_argument('--tile', type=int, default=8)
    cli.add_argument('--write-release', type=int)
    cli.add_argument('--write-channel', type=int, default=0)
    cli.add_argument('--post-write-work', type=int, default=0)
    args = cli.parse_args()
    geometry, digest = read_geometry(args.receipt_directory, args.layer)
    model, hardware = problem(geometry, tile=args.tile, write_release=args.write_release,
                              write_channel=args.write_channel, post_write_work=args.post_write_work)
    attention = next(task for task in model['tasks'] if task['id'] == 'attention')
    expected = set(hardware['event_model']['initial_backing'])
    kv_heads, _, past, dimension = geometry
    expected_bytes = 2 * kv_heads * past * dimension * 4
    candidates = {}
    for candidate in attention['bindings']:
        forced = deepcopy(model)
        next(task for task in forced['tasks'] if task['id'] == 'attention')['bindings'] = [candidate]
        plan = compile_event_ir(forced, hardware, width=8)['plan']
        candidates[candidate['id']] = check_plan(plan, hardware, expected, expected_bytes)
    selected = {}
    for width in (1, 8):
        plan = compile_event_ir(model, hardware, width=width)['plan']
        selected[width] = check_plan(plan, hardware, expected, expected_bytes)
    if selected[8]['cycles'] != min(r['cycles'] for r in candidates.values()):
        raise ValueError('DP did not select the best forced binding in this candidate pool')
    print(json.dumps({'program_sha256': digest, 'geometry': geometry, 'tile': args.tile,
                      'write_release': args.write_release, 'write_channel': args.write_channel,
                      'post_write_work': args.post_write_work,
                      'forced': candidates, 'selected': selected}, sort_keys=True))


def read_geometry(directory, layer):
    raw = (directory / 'program.json').read_bytes()
    digest = sha256(raw).hexdigest()
    receipt = json.loads((directory / 'receipt.json').read_text(encoding='utf-8'))
    geometry = decode_geometry(json.loads(raw), layer)
    if digest != receipt['program_sha256'] or not receipt['passed'] or receipt['query_tokens'] != 1:
        raise ValueError('integer program differs from its qualified receipt')
    if receipt['prefix_tokens'] != geometry[2]:
        raise ValueError('integer receipt has the wrong prefix length')
    return geometry, digest


if __name__ == '__main__':
    main()
