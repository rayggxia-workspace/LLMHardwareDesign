"""Audit event plans from the qualified contract and emitted trace.

Check data custody on the resulting timeline, independently of the planner's
copy map, resource profiles, route selection and cost evaluation.
"""
from bisect import bisect_right
from collections import defaultdict

DDR = 'DDR'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(tasks, hardware, plan, wire_budget=None):
    spec = hardware['event_model']
    windows, sizes = spec['windows'], spec['value_bytes']
    reservations, reads, writes = defaultdict(list), defaultdict(list), defaultdict(list)
    backing = dict.fromkeys(spec.get('initial_backing', ()), 0)
    read_external = []
    ends, nets = {}, set()
    total_read = total_write = 0
    for w, value in spec.get('initial_copies', {}).items():
        writes[w].append((0, 0, value))

    def claim(record, start, end):
        for r, units in record['claims'].items():
            reservations[r].extend(((start, units), (end, -units)))
        nets.update(record.get('nets', ()))

    def access(table, w, value, start, end):
        require(w in windows and value in sizes and sizes[value] <= windows[w]['bytes'],
                'window capacity or identity differs')
        table[w].append((start, end, value))

    def phased_claims(event, expected, holds, nets):
        start, end = event['start'], event['end']
        timeline = event.get('phases', [])
        require([p['kind'] for p in timeline] == [p['kind'] for p in expected]
                and timeline[0]['start'] == start and timeline[-1]['end'] == end,
                'event phase coverage differs')
        previous = start
        for phase, item in zip(timeline, expected):
            begin, stop = phase['start'], phase['end']
            require(type(begin) is int and type(stop) is int and previous <= begin
                    and stop-begin == item['ticks'], 'event phase order or duration differs')
            claim(item, begin, stop)
            previous = stop
        claim({'claims': holds, 'nets': nets}, start, end)

    def route_claims(event, route, size):
        start, end = event['start'], event['end']
        duration = route['setup'] + (size+route['bytes_per_tick']-1)//route['bytes_per_tick']
        profile = route.get('phases')
        if profile is None:
            require(end-start == duration and 'phases' not in event, 'route service duration differs')
            claim(route, start, end)
            return
        phased_claims(event, (
            {**profile['issue'], 'kind': 'issue'},
            {'kind': 'data', 'ticks': duration, 'claims': route['claims']},
            {**profile['ack'], 'kind': 'ack'},
        ), profile['hold_claims'], route.get('nets', ()))

    by_task = {t['id']: t for t in tasks}
    require(len(by_task) == len(tasks) == len(plan['tasks']), 'event coverage differs')
    for row in plan['tasks']:
        task = by_task[row['id']]
        require(task['id'] not in ends and all(p in ends for p in task.get('after', ())),
                'event task order differs')
        (binding,) = [b for b in task['bindings'] if b['id'] == row['binding']]
        nets.update(binding['nets'])
        boundary = max((ends[p] for p in task.get('after', ())), default=0)
        detail = row['evaluation']
        events = detail['events']
        require(bool(events), 'empty event trace')
        stages = iter(binding['event_stages'])
        pending_moves, local_read, local_write = [], 0, 0
        for event in events:
            start, end = event['start'], event['end']
            require(type(start) is int and type(end) is int and boundary <= start < end,
                    'invalid event interval or prerequisite')
            if event['kind'] == 'move':
                src, dst, value = event['src'], event['dst'], event['value']
                route = spec['routes'][event['route']]
                require(src != dst and route['src'] == (DDR if src == DDR else windows[src]['site'])
                        and route['dst'] == (DDR if dst == DDR else windows[dst]['site']),
                        'route endpoints differ')
                size = sizes[value]
                route_claims(event, route, size)
                if src == DDR:
                    read_external.append((start, value))
                    local_read += size
                else:
                    access(reads, src, value, start, end)
                if dst == DDR:
                    backing[value] = min(end, backing.get(value, end))
                    local_write += size
                else:
                    access(writes, dst, value, start, end)
                pending_moves.append(event)
            else:
                stage = next(stages, None)
                require(event['kind'] == 'stage' and stage and event['service'] == stage['service'],
                        'native stage identity or order differs')
                service = spec['services'][stage['service']]
                inputs, outputs = stage.get('inputs', {}), stage.get('outputs', {})
                require(event['inputs'] == inputs and event['outputs'] == outputs,
                        'native stage values differ')
                if 'copy_sites' in service:
                    source, destinations = service['copy_sites']
                    require(len(inputs) == 1 and [windows[w]['site'] for w in inputs] == [source]
                            and sorted(windows[w]['site'] for w in outputs) == sorted(destinations)
                            and set(outputs.values()) == set(inputs.values()),
                            'COPY identity or endpoints differ')
                require(all(move['end'] <= start for move in pending_moves), 'stage precedes move ACK')
                if stage.get('input_policy') == 'backing':
                    loaded = {(m['dst'], m['value']) for m in pending_moves if m['src'] == DDR}
                    require(set(inputs.items()) <= loaded, 'backing-only stage missed required DDR read')
                if stage.get('input_policy') == 'resident':
                    loaded = {(m['dst'], m['value']) for m in pending_moves if m['src'] == DDR}
                    require(not set(inputs.items()) & loaded, 'resident stage introduced a DDR read')
                for w, value in inputs.items():
                    access(reads, w, value, start, end)
                for w, value in outputs.items():
                    access(writes, w, value, start, end)
                if 'phases' in service:
                    phased_claims(event, service['phases'], service.get('hold_claims', {}),
                                  service.get('nets', ()))
                else:
                    require(end-start == service['ticks'] and 'phases' not in event,
                            'native stage service duration differs')
                    claim(service, start, end)
                local_read += service.get('read_bytes', 0)
                local_write += service.get('write_bytes', 0)
                boundary = end
                pending_moves.clear()
        require(not pending_moves and next(stages, None) is None, 'incomplete native stage sequence')
        require(row['start'] == min(e['start'] for e in events) and row['end'] == boundary,
                'action timing differs')
        require((detail['external_read_bytes'], detail['external_write_bytes']) == (local_read, local_write),
                'action traffic differs')
        total_read += local_read
        total_write += local_write
        ends[row['id']] = boundary

    for w in writes.keys() | reads.keys():
        changes = sorted(writes[w])
        require(all(a[1] <= b[0] for a, b in zip(changes, changes[1:])), 'window writers overlap')
        starts = [a for a, _, _ in changes]
        for start, end, value in reads[w]:
            i = bisect_right(starts, start) - 1
            require(i >= 0 and changes[i][1] <= start and changes[i][2] == value
                    and (i+1 == len(changes) or end <= changes[i+1][0]),
                    'window read precedes ACK or outlives source custody')
    require(all(value in backing and backing[value] <= start for start, value in read_external),
            'external read precedes store ACK')
    require(set(spec.get('live_out', ())) <= (backing.keys() |
            {max(items)[2] for items in writes.values() if items}), 'live output lost')
    capacity = spec.get('external_capacity_bytes')
    if capacity is not None:
        require(sum(sizes[v] for v in backing) <= capacity,
                'external backing capacity exceeded')
    for r, changes in reservations.items():
        occupied = 0
        for _, change in sorted(changes):
            occupied += change
            require(0 <= occupied <= hardware['resources'][r], 'resource capacity exceeded')
        require(occupied == 0, 'unreleased resource reservation')
    fixed = {n for n, info in hardware['nets'].items() if info.get('fixed')}
    wire_cost = sum(hardware['nets'][n]['cost'] for n in nets-fixed)
    require(not any(set(pair) <= nets | fixed for pair in hardware.get('incompatible_nets', ()))
            and (wire_budget is None or wire_cost <= wire_budget), 'static wire conflict or budget')
    makespan = max(ends.values(), default=0)
    require((makespan, total_read, total_write, sorted(nets), wire_cost) ==
            (plan['makespan'], plan['external_read_bytes'], plan['external_write_bytes'],
             plan['nets'], plan['wire_cost']), 'event plan summary differs')
    timing = spec.get('timing', 'calendar')
    require(timing == plan.get('timing', 'calendar'), 'event timing model differs')
    if timing == 'replay':
        from verify_event_replay import verify_grants
        verify_grants(tasks, hardware, plan['tasks'])
    return {'passed': True, 'makespan': makespan, 'external_read_bytes': total_read,
            'external_write_bytes': total_write, 'resources': len(reservations)}
