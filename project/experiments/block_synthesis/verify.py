"""Independent event/resource/address replay. Does not import the optimizer."""
from collections import defaultdict


class InvalidPlan(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidPlan(message)


def verify(graph, hardware, plan, budget=None):
    tasks = {t['id']: t for t in graph['tasks']}
    require(set(tasks) == set(plan['tasks']), 'task coverage differs')
    ext = hardware['external']
    claims = defaultdict(list)
    used_routes, nets = set(), set()
    traffic = 0
    for tid, task in tasks.items():
        row = plan['tasks'][tid]
        service = hardware['services'][row['service']]
        require(row['service'] in task.get('alternatives', hardware['services']), 'unregistered task alternative')
        require(service.get('qualified') and (service['op'], service['numeric']) == (task['op'], task['numeric']), 'service semantic mismatch')
        require(task.get('domain', '') == service.get('domain', ''), 'operator domain mismatch')
        for field, names in [('input_words', task['inputs']), ('output_words', task['outputs'])]:
            require(field not in service or service[field] == [graph['values'][n]['words'] for n in names], 'service tile shape mismatch')
        require(task.get('attributes', {}) == service.get('attributes', {}), 'service attributes differ')
        require(row['site'] == service['site'], 'task site mismatch')
        require(row['start'] >= 0 and row['end'] - row['start'] == service['ticks'], 'task duration mismatch')
        require(all(plan['tasks'][p]['end'] <= row['start'] for p in task.get('after', [])), 'precedence violated')
        for resource in service['resources']:
            claims[resource].append((row['start'], row['end'], 1))
    for move in plan['moves']:
        route = hardware['routes'][move['route']]
        require(route.get('qualified') and route['protocol'] == 'acknowledged_copy', 'unqualified copy route')
        require((move['src'], move['dst']) == (route['src'], route['dst']), 'route endpoint mismatch')
        require(move['words'] == graph['values'][move['value']]['words'], 'copy extent mismatch')
        require(route.get('min_words', 1) <= move['words'] <= route.get('max_words', 1), 'copy outside measured profile')
        require(len(move['phases']) == len(route['phases']), 'copy phase coverage')
        require(move['start'] == move['phases'][0]['start'] and move['end'] == move['phases'][-1]['end'], 'copy boundary differs')
        previous = 0
        for phase, spec in zip(move['phases'], route['phases']):
            require(phase['name'] == spec['name'] and phase['start'] >= previous and phase['end'] - phase['start'] == spec['ticks'], 'copy phase order/duration')
            for resource in spec.get('resources', []):
                claims[resource].append((phase['start'], phase['end'], 1))
            previous = phase['end']
        for hold in route.get('holds', []):
            claims[hold['resource']].append((move['phases'][hold.get('first_phase', 0)]['start'], move['end'], 1))
        used_routes.add(move['route'])
        nets.update(route.get('nets', []))
        if ext in (move['src'], move['dst']):
            traffic += move['words']
    for resource, rows in claims.items():
        events = [(start, demand) for start, end, demand in rows if end > start]
        events += [(end, -demand) for start, end, demand in rows if end > start]
        live = 0
        for tick, change in sorted(events):
            live += change
            require(0 <= live <= hardware['resources'][resource], f'resource overlap {resource}@{tick}')
    allocs = defaultdict(list)
    for row in plan['allocations']:
        require(row['site'] != ext, 'external memory must not consume S')
        require(row['words'] > 0 and 0 <= row['address'] <= hardware['sites'][row['site']]['words'] - row['words'], 'S address outside capacity')
        require(0 <= row['start'] <= row['end'], 'invalid storage lifetime')
        if row['value'] is not None:
            require(row['value'] in graph['values'] and row['words'] == graph['values'][row['value']]['words'], 'S copy extent differs')
        allocs[row['site']].append(row)
    peaks = {}
    for site, rows in allocs.items():
        active = []
        for row in sorted(rows, key=lambda r: (r['start'], r['end'])):
            if row['start'] == row['end']:
                continue
            active = [a for a in active if a['end'] > row['start']]
            for prior in active:
                require(row['address'] + row['words'] <= prior['address'] or prior['address'] + prior['words'] <= row['address'], f'S address collision in {site}')
            active.append(row)
        events = [(r['start'], r['words']) for r in rows if r['end'] > r['start']]
        events += [(r['end'], -r['words']) for r in rows if r['end'] > r['start']]
        live = peak = 0
        for _, change in sorted(events):
            live += change
            peak = max(peak, live)
        peaks[site] = peak

    copy_index = {m['copy_id']: m for m in plan['moves']}
    require(len(copy_index) == len(plan['moves']), 'duplicate materialization ID')

    def initialized(a, tick):
        value = graph['values'][a['value']]
        if a['origin'] == 'initial':
            return 'producer' not in value and value['site'] == a['site'] and a['start'] == 0
        if a['origin'].startswith('producer:'):
            tid = a['origin'][len('producer:'):]
            p = plan['tasks'].get(tid)
            return (value.get('producer') == tid and p is not None and p['site'] == a['site']
                    and a['start'] <= p['start'] and p['end'] <= tick)
        m = copy_index.get(a['origin'])
        return (m is not None and m['value'] == a['value'] and m['dst'] == a['site']
                and a['start'] <= m['start'] and m['end'] <= tick and a['end'] >= m['end'])

    def resident(name, site, start, end, require_data=True):
        return any(a['value'] == name and a['start'] <= start and a['end'] >= end
                   and (not require_data or initialized(a, start)) for a in allocs[site])

    def available(name, site, tick):
        value = graph['values'][name]
        if 'producer' in value:
            producer = plan['tasks'][value['producer']]
            if producer['site'] == site and producer['end'] <= tick:
                return True
        elif value['site'] == site:
            return True
        if site == ext and value.get('external_copy', False):
            return True
        return any(m['value'] == name and m['dst'] == site and m['end'] <= tick for m in plan['moves'])

    for name, value in graph['values'].items():
        if 'producer' in value:
            row = plan['tasks'][value['producer']]
            require(name in tasks[value['producer']]['outputs'], 'value producer mismatch')
            require(resident(name, row['site'], row['start'], row['end'], False), 'producer output has no storage')
            require(any(a['value'] == name and a['origin'] == 'producer:' + value['producer']
                        and a['start'] <= row['start'] and a['end'] >= row['end'] for a in allocs[row['site']]),
                    'producer allocation origin differs')
    # Time strictly advances through each measured route, so checking every
    # source against earlier committed copies also rejects unsupported cycles.
    for move in sorted(plan['moves'], key=lambda m: m['start']):
        name, src, dst = move['value'], move['src'], move['dst']
        require(available(name, src, move['start']), 'read before data is available: ' + name)
        if src != ext:
            require(resident(name, src, move['start'], move['end']), 'source released before ACK: ' + name)
        if dst != ext:
            require(any(a['value'] == name and a['origin'] == move['copy_id'] and
                        a['start'] <= move['start'] and a['end'] >= move['end'] for a in allocs[dst]),
                    'copy target not allocated: ' + name)
    for tid, task in tasks.items():
        row = plan['tasks'][tid]
        for name in task['inputs']:
            require(available(name, row['site'], row['start']), 'consumer starts before data: ' + name)
            require(resident(name, row['site'], row['start'], row['end']), 'consumer input not resident: ' + name)
        scratch = hardware['services'][row['service']].get('scratch_words', 0)
        if scratch:
            require(any(a['id'] == tid + ':scratch:' + row['service'] and a['start'] <= row['start'] and a['end'] >= row['end'] and a['words'] == scratch for a in allocs[row['site']]), 'scratch buffer missing')
    for name in graph.get('outputs', []):
        value = graph['values'][name]
        require(available(name, value['output_site'], plan['makespan']), 'output was not delivered')
        if value['output_site'] != ext:
            require(resident(name, value['output_site'], plan['makespan'], plan['makespan']), 'final S output was released')
    require(sorted(nets) == sorted(plan['nets']), 'static net union differs')
    cost = sum(hardware['nets'][n]['cost'] for n in nets if not hardware['nets'][n].get('fixed', False))
    require(cost == plan['wire_cost'] and (budget is None or cost <= budget), 'static wire budget differs')
    for left, right in hardware.get('incompatible_routes', []):
        require(not {left, right} <= used_routes, 'incompatible physical drivers')
    require(traffic == plan['external_words'], 'external traffic differs')
    external_values = {n for n, v in graph['values'].items() if v.get('site') == ext or v.get('external_copy')}
    external_values.update(m['value'] for m in plan['moves'] if ext in (m['src'], m['dst']))
    regions = plan['external_regions']
    require({r['value'] for r in regions} == external_values and len(regions) == len(external_values), 'external region coverage differs')
    prior_end = 0
    for r in sorted(regions, key=lambda r: r['address_words']):
        require(r['words'] == graph['values'][r['value']]['words'] and r['address_words'] >= prior_end,
                'external region collision/extent differs')
        prior_end = r['address_words'] + r['words']
    capacity = hardware.get('external_capacity_words')
    require(capacity is None or prior_end <= capacity, 'external memory capacity exceeded')
    finish = max([r['end'] for r in plan['tasks'].values()] + [m['end'] for m in plan['moves'] if m['final']] + [0])
    require(finish == plan['makespan'], 'makespan differs')
    return {'passed': True, 'peak_words': peaks, 'external_words': traffic, 'static_nets': len(nets),
            'external_capacity_qualified': capacity is not None or not regions,
            'external_reserved_words': prior_end}
