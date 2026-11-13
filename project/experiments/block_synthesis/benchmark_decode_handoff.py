"""Replay two integer decode boundaries with a complete FFN on the shared DDR."""
import argparse
import json
from pathlib import Path

from benchmark_attention_kv import problem as attention_problem, read_geometry, typed_route
from benchmark_ffn_program_dp import problem as ffn_problem
from ffn_program_cost import INPUT_BYTES, READ_BYTES, SHARED_RESOURCES
from run import compile_event_ir


def build(first, second, *, tile, mode, seed, candidate, queue):
    heads, group, past, dimension = first
    if second != (heads, group, past + 1, dimension):
        raise ValueError('integer decode receipts are not adjacent')
    a0, h0 = attention_problem(first, tile=tile, append_start=past, window_past=past + 1)
    a1, h1 = attention_problem(second, tile=tile, append_start=past, window_past=past + 1)
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
        raise ValueError('successive tokens must use the same physical SRAM windows')
    spec['windows'].update({w: {**info, 'site': sites[info['site']]}
                            for w, info in first_spec['windows'].items()})
    initial = set(first_spec['initial_backing'])
    addresses = dict(first_spec['typed_dma']['addresses'])
    old_versions = {f'h{head}-{kind}-{past}': f't0-current-{kind}-{head}'
                    for kind in ('k', 'v') for head in range(heads)}
    history_addresses = {v: addresses[v] for v in initial}
    published_addresses = {v: addresses[name.removeprefix('t0-')] for v, name in old_versions.items()}
    second_addresses = second_spec['typed_dma']['addresses']
    if any(second_addresses.get(v) != address for v, address in (history_addresses | published_addresses).items()):
        raise ValueError('historical cache moved between token versions')
    new_addresses = {**{v: addresses[v] for v in initial},
                     **{version: addresses[version.removeprefix('t0-')] for version in old_versions.values()}}
    spec['typed_dma'] = {'ffn_provider': {'mode': mode, 'seed': seed},
                         'mixed': {'queue': queue, 'write_latency': 9}, 'addresses': new_addresses}
    spec['initial_backing'] = sorted(initial)
    spec['routes']['load-history'] = typed_route('DDR', 'U1', 4, 'U1.S.port')
    spec['routes']['store-append'] = typed_route('U1', 'DDR', 3, 'U1.S.port')
    spec['live_out'] = list(old_versions.values())

    attentions = []
    for token, (model, old) in enumerate(((a0, first_spec), (a1, second_spec))):
        namespace = f't{token}-'
        aliases = old_versions if token else {}
        names = {v: aliases.get(v, v if v in initial else namespace + v)
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
        candidates = model['tasks'][0]['bindings']
        if token:
            candidates = [b for b in candidates if b['id'] == candidate]
        else:
            candidates = [b for b in candidates if b['id'] == 'lookahead']
        bindings = []
        for binding in candidates:
            stages = [{**s, 'service': namespace + s['service'],
                       'inputs': {w: names[v] for w, v in s['inputs'].items()},
                       'outputs': {w: names[v] for w, v in s['outputs'].items()}}
                      for s in binding['event_stages']]
            query = {w: names[v] for w, v in old['initial_copies'].items()}
            setup = stage(namespace + 'qkv-ready', 1, ('U1.S.port',), outputs=query)
            prefix = [setup]
            if token:
                # The first immutable K tile may be moved without knowing the
                # sampled token or its Q/K/V. The serial binding leaves it idle.
                first_tile = {w: v for w, v in stages[0]['inputs'].items() if w.startswith('cache-')}
                request = stage(namespace + 'history-ready', 1, ('U1.S.port',),
                                inputs=first_tile if candidate == 'lookahead' else {})
                prefix.insert(0, request)
            bindings.append({**binding, 'site': 'U1', 'ticks': binding['ticks'] + len(prefix),
                             'event_stages': [*prefix, *stages]})
        attentions.append({'id': namespace + 'attention', 'bindings': bindings})

    results = {f'h{head}-result': f't0-h{head}-result' for head in range(heads)}
    links = ['J0.S->U.S', 'J1.S->U.S']
    hardware['nets'].update({link: {'cost': 1} for link in links})
    adapter = task('attention-to-ffn', [stage('projection-residual-norm', INPUT_BYTES // 64,
                   ('J0.S.port', 'J1.S.port', 'U.S.port'), inputs=results, outputs={'input': 'activation'})],
                   after=('t0-attention',))
    spec['services']['projection-residual-norm']['nets'] = links
    ffn['after'] = ['attention-to-ffn']
    current = {f'current-{kind}-h{head}': f't0-current-{kind}-{head}'
               for kind in ('k', 'v') for head in range(heads)}
    append = task('append-kv', [stage('publish-kv', 1, inputs=current, persist=list(current))],
                  after=('attention-to-ffn',))
    attentions[1]['after'] = ['append-kv']
    attentions[1]['event_after'] = [{'task': 'ffn', 'from': [0, 'stage'], 'to': [1, 'stage']}]
    return {'tasks': [attentions[0], adapter, ffn, append, attentions[1]]}, hardware


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


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('case', type=Path)
    cli.add_argument('--candidate', choices=('serial', 'lookahead'), required=True)
    cli.add_argument('--mode', type=int, choices=(0, 1), default=1)
    cli.add_argument('--seed', type=int, default=25001)
    cli.add_argument('--queue', type=int, default=16)
    cli.add_argument('--tile', type=int, default=8)
    args = cli.parse_args()
    first, hash0 = read_geometry(args.case / 'step-1', 0)
    second, hash1 = read_geometry(args.case / 'step-2', 0)
    model, hardware = build(first, second, tile=args.tile, mode=args.mode, seed=args.seed,
                            candidate=args.candidate, queue=args.queue)
    result = compile_event_ir(model, hardware, width=1)
    print(json.dumps({'candidate': args.candidate, 'programs': [hash0, hash1], 'mode': args.mode,
                      'queue': args.queue, **check(result['plan'], hardware['event_model'], first, args.candidate)},
                     sort_keys=True))


if __name__ == '__main__':
    main()
