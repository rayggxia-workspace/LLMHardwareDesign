"""Replay integer decode boundaries with complete FFN programs on shared DDR."""
import argparse
import json
from pathlib import Path

from benchmark_attention_kv import problem as attention_problem, read_geometry, typed_route
from benchmark_ffn_program_dp import problem as ffn_problem
from ffn_program_cost import INPUT_BYTES, READ_BYTES, RESULT_BYTES, SHARED_RESOURCES
from run import compile_event_ir


def layer_pair_dependencies(directory):
    """Check the archived residual-to-QKV chain at the modeled layer boundary."""
    instructions = json.loads((directory / 'program.json').read_bytes())['instructions']
    by_id = {node['id']: node for node in instructions}

    def stage(layer, name, op):
        kernel = f'/model/model/layers.{layer}/{name}'
        node, = [n for n in instructions if n['kernel'] == kernel and n['op'] == op]
        return node

    def reaches(consumer, producer):
        seen = set()
        pending = [consumer['id']]
        while pending:
            value = pending.pop()
            if value == producer['id']:
                return True
            if value in by_id and value not in seen:
                seen.add(value)
                pending.extend(by_id[value]['inputs'])
        return False

    dimensions = {'gate_proj': (2048, 11008), 'up_proj': (2048, 11008), 'down_proj': (11008, 2048)}
    residuals = []
    for layer in range(2):
        attention = stage(layer, 'self_attn/o_proj/MatMul', 'Dot')
        residual = stage(layer, 'Add_1', 'Add')
        dots = {name: stage(layer, f'mlp/{name}/MatMul', 'Dot') for name in dimensions}
        if (any(dots[name]['shape'] != [1, 1, output] or dots[name]['attributes']['length'] != length
                for name, (length, output) in dimensions.items())
                or not all(reaches(dots[name], attention) and reaches(dots['down_proj'], dots[name])
                           for name in ('gate_proj', 'up_proj'))
                or not reaches(residual, dots['down_proj'])):
            raise ValueError('archived FFN or residual topology differs')
        residuals.append(residual)
    projections = [stage(1, f'self_attn/{kind}_proj/MatMul', 'Dot') for kind in ('q', 'k', 'v')]
    if not all(reaches(node, residuals[0]) for node in projections):
        raise ValueError('archived next-layer Q/K/V do not depend on the preceding residual')
    return {'layer_residuals': [node['id'] for node in residuals],
            'layer1_qkv': [node['id'] for node in projections]}


def build(first, second, *, tile, mode, seed, candidate, queue, cross_layer=False):
    heads, group, past, dimension = first
    if second != (heads, group, past + int(not cross_layer), dimension):
        raise ValueError('integer decode receipts do not share the expected layer or token geometry')
    a0, h0 = attention_problem(first, tile=tile, append_start=past, window_past=second[2])
    a1, h1 = attention_problem(second, tile=tile, append_start=past, window_past=second[2])
    fm, hardware = ffn_problem(1, mode, seed, [('programmed-ffn', 0, True)])
    ffn = fm['tasks'][1]
    spec = hardware['event_model']
    spec['services']['programmed-ffn']['claims'] = SHARED_RESOURCES.copy()
    spec['initial_copies'] = {}

    # The programmed FFN owns P0/P1/P2/U in full, including hidden scratch.
    # Use the other five sites in the declared nine-instance inventory for
    # the modeled Attention path and explicitly hand off to U's input.
    sites = {'P0': 'U1', 'P1': 'J0', 'P2': 'J1', 'C': 'C0', 'U': 'F0'}
    hardware['sites'].update({sites[site]: info for site, info in h0['sites'].items()})
    ports = {site + '.S': target + '.S.port' for site, target in sites.items()}
    resources = {'dot': 'U1.M.model', 'acc': 'U1.acc.model', 'norm': 'C0.norm.model',
                 'operand-context': 'U1.context.model', **ports}
    hardware['resources'].update({resources[key]: n for key, n in h0['resources'].items()})

    def claims(record):
        return {resources[k]: n for k, n in record['claims'].items()}

    def stage(name, ticks, resources=(), **args):
        spec['services'][name] = {'ticks': ticks, 'claims': dict.fromkeys(resources, 1)}
        return {'service': name, **args}

    def task(name, stages, *, after=()):
        return {'id': name, 'after': list(after), 'bindings': [{
            'id': name, 'ticks': sum(spec['services'][s['service']]['ticks'] for s in stages),
            'site': 'U1', 'resources': [], 'nets': [], 'scratch_words': 0, 'event_stages': stages,
        }]}

    first_spec, second_spec = (h['event_model'] for h in (h0, h1))
    if first_spec['windows'] != second_spec['windows']:
        raise ValueError('decode boundaries must use the same physical SRAM windows')
    spec['windows'].update({w: {**info, 'site': sites[info['site']]}
                            for w, info in first_spec['windows'].items()})
    initial = set(first_spec['initial_backing'])
    addresses = first_spec['typed_dma']['addresses']
    prefix = 'l' if cross_layer else 't'
    scopes = [f'{prefix}{index}-' for index in range(2)]
    old_versions = {f'h{head}-{kind}-{past}': f't0-current-{kind}-{head}'
                    for kind in ('k', 'v') for head in range(heads)}
    history_addresses = {v: addresses[v] for v in initial}
    published_addresses = {v: addresses[name.removeprefix('t0-')] for v, name in old_versions.items()}
    second_addresses = second_spec['typed_dma']['addresses']
    if not cross_layer and any(second_addresses.get(v) != address
                               for v, address in (history_addresses | published_addresses).items()):
        raise ValueError('historical cache moved between token versions')
    if cross_layer:
        new_addresses = {scope + v: address + index * 0x200000
                         for index, (scope, layer) in enumerate(zip(scopes, (first_spec, second_spec)))
                         for v, address in layer['typed_dma']['addresses'].items()}
        history = {scope + v for scope in scopes for v in initial}
        live_out = sorted(new_addresses.keys() - history)
    else:
        new_addresses = {**history_addresses,
                         **{v: addresses[v.removeprefix('t0-')] for v in old_versions.values()}}
        history, live_out = initial, list(old_versions.values())
    spec['typed_dma'] = {'ffn_provider': {'mode': mode, 'seed': seed},
                         'mixed': {'queue': queue, 'write_latency': 9}, 'addresses': new_addresses}
    spec['initial_backing'] = sorted(history)
    spec['routes']['load-history'] = typed_route('DDR', 'U1', 4, 'U1.S.port')
    spec['routes']['store-append'] = typed_route('U1', 'DDR', 3, 'U1.S.port')
    spec['live_out'] = live_out

    prior_results = {f'result-{p}': f'result-{p}' for p in range(len(RESULT_BYTES))}
    attentions = []
    for token, (model, old) in enumerate(((a0, first_spec), (a1, second_spec))):
        namespace = scopes[token]
        aliases = old_versions if token and not cross_layer else {}
        names = {v: aliases.get(v, v if v in initial and not cross_layer else namespace + v)
                 for v in old['value_bytes']}
        for value, size in old['value_bytes'].items():
            spec['value_bytes'][names[value]] = size
        for name, svc in old['services'].items():
            normalized = {**svc, 'claims': claims(svc)}
            if 'phases' in svc:
                normalized['phases'] = [{**phase, 'claims': claims(phase)} for phase in svc['phases']]
                normalized['hold_claims'] = {resources[k]: n for k, n in svc['hold_claims'].items()}
                phase_windows = svc['window_phases']
                normalized['window_phases'] = {**phase_windows,
                                               'result_hold': resources[phase_windows['result_hold']]}
            spec['services'][namespace + name] = normalized
        candidates = [b for b in model['tasks'][0]['bindings']
                      if (token and candidate == 'both') or b['id'] == (candidate if token else 'lookahead')]
        bindings = []
        for binding in candidates:
            stages = [{**s, 'service': namespace + s['service'],
                       'inputs': {w: names[v] for w, v in s['inputs'].items()},
                       'outputs': {w: names[v] for w, v in s['outputs'].items()}}
                      for s in binding['event_stages']]
            query = {w: names[v] for w, v in old['initial_copies'].items()}
            setup_ports = ('U1.S.port',)
            setup_inputs = {}
            if cross_layer and token:
                setup_ports += tuple(f'P{p}.S.port' for p in range(len(RESULT_BYTES)))
                setup_inputs = prior_results
            setup_ticks = 1 + (max((size + 63) // 64 for size in RESULT_BYTES) if setup_inputs else 0)
            setup = stage(namespace + 'qkv-ready', setup_ticks, setup_ports, inputs=setup_inputs, outputs=query)
            if setup_inputs:
                nets = [f'P{p}.S->U1.S' for p in range(len(RESULT_BYTES))]
                hardware['nets'].update({net: {'cost': 1} for net in nets})
                spec['services'][setup['service']]['nets'] = nets
            prefix = [setup]
            if token:
                # Historical K is independent of the new Q/K/V.
                first_tile = {w: v for w, v in stages[0]['inputs'].items() if w.startswith('cache-')}
                request = stage(namespace + 'history-ready', 1, ('U1.S.port',),
                                inputs=first_tile if binding['id'] == 'lookahead' else {})
                prefix.insert(0, request)
            bindings.append({**binding, 'site': 'U1', 'ticks': binding['ticks'] + setup_ticks + token,
                             'event_stages': [*prefix, *stages]})
        attentions.append({'id': namespace + 'attention', 'bindings': bindings})

    links = ['J0.S->U.S', 'J1.S->U.S']
    hardware['nets'].update({link: {'cost': 1} for link in links})

    def handoff(index, activation, suffix=''):
        scope = scopes[index]
        results = {f'h{head}-result': f'{scope}h{head}-result' for head in range(heads)}
        adapt = stage('projection-residual-norm' + suffix, INPUT_BYTES // 64,
                      ('J0.S.port', 'J1.S.port', 'U.S.port'), inputs=results, outputs={'input': activation})
        spec['services'][adapt['service']]['nets'] = links
        adapter = task('attention-to-ffn' + suffix, [adapt], after=(attentions[index]['id'],))
        current = {f'current-{kind}-h{head}': f'{scope}current-{kind}-{head}'
                   for kind in ('k', 'v') for head in range(heads)}
        append = task('append-kv' + suffix, [stage('publish-kv' + suffix, 1, inputs=current, persist=list(current))],
                      after=(adapter['id'],))
        return adapter, append

    adapter, append = handoff(0, 'activation')
    ffn['after'] = [adapter['id']]
    attentions[1]['after'] = [append['id']]
    attentions[1]['event_after'] = [{'task': ffn['id'], 'from': [0, 'stage'], 'to': [1, 'stage']}]
    tasks = [attentions[0], adapter, ffn, append, attentions[1]]
    if cross_layer:
        # Cache reads can start while the earlier layer's append is in flight.
        # The two layers reuse the on-chip current-K/V windows, so only QKV
        # setup waits for that append's custody to clear.
        attentions[1]['after'] = [adapter['id']]
        attentions[1]['event_after'].append({'task': append['id'], 'from': [0, 'stage'], 'to': [1, 'stage']})
        activation = 'layer1-activation'
        outputs = {window: f'layer1-{value}' for window, value in prior_results.items()}
        spec['value_bytes'][activation] = INPUT_BYTES
        spec['value_bytes'].update({v: spec['windows'][w]['bytes'] for w, v in outputs.items()})
        adapter1, append1 = handoff(1, activation, '-l1')
        service = spec['services']['programmed-ffn']
        service1 = 'programmed-ffn-l1'
        spec['services'][service1] = {**service, 'ffn_program': {**service['ffn_program'],
                                                                'address_offset': 0x10000000}}
        ffn1 = task('ffn-l1', [{'service': service1, 'inputs': {'input': activation}, 'outputs': outputs}],
                    after=(adapter1['id'],))
        retire = task('retire-layer-pair', [stage('retire', 1, inputs=outputs)],
                      after=(ffn1['id'], append['id'], append1['id']))
        tasks.extend((adapter1, ffn1, append1, retire))
    return {'tasks': tasks}, hardware


def check(plan, spec, geometry, candidate):
    if plan['status'] != 'planned':
        raise ValueError('decode handoff has no feasible plan')
    rows = {row['id']: row for row in plan['tasks']}
    heads, _, past, dimension = geometry
    baseline_bytes = 2 * heads * past * dimension * 4
    append_bytes = 2 * heads * dimension * 4
    expected_traffic = (READ_BYTES + 2 * baseline_bytes + append_bytes, append_bytes)
    if (plan['external_read_bytes'], plan['external_write_bytes']) != expected_traffic:
        raise ValueError('decode and FFN traffic differs')
    address = spec['typed_dma']['addresses']
    new = set(spec['live_out'])
    initial = set(spec['initial_backing'])
    store = {e['value']: e for e in rows['append-kv']['evaluation']['events'] if e.get('dst') == 'DDR'}
    if set(store) != new:
        raise ValueError('persistent cache publication differs')
    history = []
    for token, expected in enumerate((initial, initial | new)):
        events = rows[f't{token}-attention']['evaluation']['events']
        reads = [e for e in events if e.get('src') == 'DDR']
        if len(reads) != len(expected) or {e['value'] for e in reads} != expected:
            raise ValueError('token did not read its complete cache version')
        history.append(reads)
    for event in (*history[0], *history[1], *store.values()):
        value = event['value']
        if sorted(beat['address'] for beat in event['dma_beats']) != list(
                range(address[value], address[value] + spec['value_bytes'][value], 64)):
            raise ValueError('cache physical beat coverage differs')
        if event.get('src') == 'DDR' and value in store and event['start'] < store[value]['end']:
            raise ValueError('next token read before KV publication')
    program, = rows['ffn']['evaluation']['events']
    shared = sum(program['start'] <= b['issue'] < program['end'] for e in history[1] for b in e['dma_beats'])
    if shared != (spec['value_bytes']['h0-k-0'] // 64 if candidate == 'lookahead' else 0):
        raise ValueError('only token-independent prefetch may issue before FFN completes')
    if not any(program['start'] <= b['issue'] < program['end'] for e in store.values() for b in e['dma_beats']):
        raise ValueError('complete FFN did not share the live fabric with KV append')
    setup, = [e for e in rows['t1-attention']['evaluation']['events'] if e.get('service') == 't1-qkv-ready']
    if setup['start'] < program['end']:
        raise ValueError('next-token compute started before the previous FFN')
    return {'makespan': plan['makespan'], 'ffn': [program['start'], program['end']],
            't0_attention': rows['t0-attention']['end'], 't1_attention': rows['t1-attention']['end'],
            'cache_store_ack': {v: e['end'] for v, e in store.items()},
            't1_qkv_ready': setup['start'], 'cache_read_while_ffn': shared, 'traffic': expected_traffic}


def check_layers(plan, spec, geometry, candidate):
    if plan['status'] != 'planned':
        raise ValueError(f'layer pair has no feasible plan: {plan}')
    rows = {row['id']: row for row in plan['tasks']}
    heads, _, past, dimension = geometry
    append_bytes = 2 * heads * dimension * 4
    traffic = (2 * (READ_BYTES + past * append_bytes), 2 * append_bytes)
    if (plan['external_read_bytes'], plan['external_write_bytes']) != traffic:
        raise ValueError('layer pair traffic differs')
    addresses = spec['typed_dma']['addresses']
    sizes = spec['value_bytes']
    programs, reads, writes = [], [], []
    for index, suffix in enumerate(('', '-l1')):
        program, = rows['ffn' + suffix]['evaluation']['events']
        programs.append(program)
        scope = f'l{index}-'
        groups = ((spec['initial_backing'], rows[scope + 'attention'], 'src', reads),
                  (spec['live_out'], rows['append-kv' + suffix], 'dst', writes))
        for versions, row, direction, total in groups:
            expected = {v for v in versions if v.startswith(scope)}
            events = [event for event in row['evaluation']['events'] if event.get(direction) == 'DDR']
            if len(events) != len(expected) or {e['value'] for e in events} != expected:
                raise ValueError('layer cache versions differ')
            for event in events:
                value = event['value']
                if sorted(b['address'] for b in event['dma_beats']) != list(
                        range(addresses[value], addresses[value] + sizes[value], 64)):
                    raise ValueError('layer cache physical beat coverage differs')
            total.append(events)

    setup, = [e for e in rows['l1-attention']['evaluation']['events'] if e.get('service') == 'l1-qkv-ready']
    early = [beat for e in reads[1] for beat in e['dma_beats'] if beat['issue'] < programs[0]['end']]
    first_tile = 'l1-h0-k-0'
    expected_early = set(range(addresses[first_tile], addresses[first_tile] + sizes[first_tile], 64))
    if (sorted(b['address'] for b in early) != (sorted(expected_early) if candidate == 'lookahead' else [])
            or any(b['issue'] < programs[0]['start'] for b in early)
            or setup['start'] < max(programs[0]['end'], *(e['end'] for e in writes[0]))):
        raise ValueError('layer 1 prefetch or output dependency differs')
    final_visible = max(programs[1]['end'], *(e['end'] for group in writes for e in group))
    retire, = rows['retire-layer-pair']['evaluation']['events']
    if retire['start'] < final_visible or retire['end'] != plan['makespan']:
        raise ValueError('layer pair retired before final output or KV publication')
    return {'makespan': plan['makespan'], 'ffn': [[p['start'], p['end']] for p in programs],
            'cache_store_visible': [max(e['end'] for e in group) for group in writes],
            'layer1_qkv_start': setup['start'], 'layer_pair_retire': retire['start'],
            'cache_read_while_ffn': len(early), 'traffic': traffic}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('case', type=Path)
    cli.add_argument('--candidate', choices=('serial', 'lookahead', 'both'), required=True)
    cli.add_argument('--mode', type=int, choices=(0, 1), default=1)
    cli.add_argument('--seed', type=int, default=25001)
    cli.add_argument('--queue', type=int, default=16)
    cli.add_argument('--tile', type=int, default=8)
    cli.add_argument('--layer-pair', action='store_true')
    cli.add_argument('--width', type=int, default=1)
    args = cli.parse_args()
    first, hash0 = read_geometry(args.case / 'step-1', 0)
    second, hash1 = (read_geometry(args.case / 'step-1', 1) if args.layer_pair
                     else read_geometry(args.case / 'step-2', 0))
    dependencies = layer_pair_dependencies(args.case / 'step-1') if args.layer_pair else {}
    model, hardware = build(first, second, tile=args.tile, mode=args.mode, seed=args.seed,
                            candidate=args.candidate, queue=args.queue, cross_layer=args.layer_pair)
    result = compile_event_ir(model, hardware, width=args.width)
    plan = result['plan']
    attention = 'l1-attention' if args.layer_pair else 't1-attention'
    chosen = next((row['binding'] for row in plan.get('tasks', ()) if row['id'] == attention), args.candidate)
    check_plan = check_layers if args.layer_pair else check
    print(json.dumps({'candidate': args.candidate, 'chosen': chosen, 'width': args.width,
                      'programs': [hash0, hash1], 'mode': args.mode, 'queue': args.queue,
                      **dependencies,
                      **check_plan(plan, hardware['event_model'], first, chosen)},
                     sort_keys=True))


if __name__ == '__main__':
    main()
