"""Fast verified incumbent for independent branches on different private S.

Each site's address-safe serial stream is retained. A global event list then
overlaps these streams whenever their declared resources allow it. Shared
initial MEM values may be reread; generated cross-site dependencies use the
general constraint solver instead of being silently treated as external data.
"""
from collections import defaultdict
from copy import deepcopy
import time

from seed import serial_seed, external_regions, SeedFailure


def parallel_seed(graph, hardware, bindings, budget=None):
    began = time.monotonic()
    if graph.get('state_groups'):
        raise SeedFailure('persistent macro contexts use the general planner')
    ext = hardware['external']
    if any(v.get('site') not in (None, ext) for v in graph['values'].values()):
        raise SeedFailure('parallel incumbent needs externally initialized inputs')
    owner = {tid: hardware['services'][sid]['site'] for tid, sid in bindings.items()}
    groups = defaultdict(list)
    for t in graph['tasks']:
        for n in t['inputs']:
            p = graph['values'][n].get('producer')
            if p and owner[p] != owner[t['id']]:
                raise SeedFailure('generated cross-site dependency needs the general planner')
        if any(owner[p] != owner[t['id']] for p in t.get('after', [])):
            raise SeedFailure('cross-site precedence needs the general planner')
        groups[owner[t['id']]].append(t)
    if len(groups) < 2:
        raise SeedFailure('one execution site; no independent stream to overlap')
    streams, calendars = {}, defaultdict(list)
    result = {'status': 'HEURISTIC', 'best_bound': 0, 'tasks': {}, 'moves': [], 'allocations': [],
              'claims': [], 'nets': [], 'external_words': 0, 'wire_cost': 0,
              'optimality_scope': 'independent branch list schedule, no optimality claim'}
    for site, tasks in groups.items():
        names = {n for t in tasks for n in t['inputs'] + t['outputs']}
        sub = {'tasks': tasks, 'values': {n: graph['values'][n] for n in names},
               'outputs': [n for n in graph.get('outputs', []) if n in names]}
        local = serial_seed(sub, hardware, {t['id']: bindings[t['id']] for t in tasks}, budget)
        actions = []
        for tid, row in local['tasks'].items():
            s = hardware['services'][row['service']]
            claims = [(r, 0, row['end'] - row['start'], 1) for r in s['resources']]
            actions.append((row['start'], row['end'], 'task', tid, row, claims))
        for m in local['moves']:
            r = hardware['routes'][m['route']]
            claims = [(resource, p['start'] - m['start'], p['end'] - m['start'], 1)
                      for p, spec in zip(m['phases'], r['phases']) for resource in spec.get('resources', [])]
            claims += [(hold['resource'], m['phases'][hold.get('first_phase', 0)]['start'] - m['start'],
                        m['end'] - m['start'], 1) for hold in r.get('holds', [])]
            actions.append((m['start'], m['end'], 'move', m['copy_id'], m, claims))
        actions.sort(key=lambda a: (a[0], a[1]))
        streams[site] = {'local': local, 'actions': actions, 'cursor': 0, 'free': 0, 'clock': {0: 0}, 'copies': {}}

    def first_slot(ready, claims):
        at = ready
        while True:
            advance = at
            for resource, a, b, demand in claims:
                overlaps = [(x, y, d) for x, y, d in calendars[resource] if x < at + b and y > at + a]
                events = [(at + a, demand), (at + b, -demand)]
                for x, y, d in overlaps:
                    events += [(max(x, at + a), d), (min(y, at + b), -d)]
                live = 0
                for tick, delta in sorted(events):
                    live += delta
                    if live > hardware['resources'][resource]:
                        advance = max(advance, min(y for x, y, _ in overlaps if x <= tick < y) - a)
                        break
            if advance == at:
                return at
            at = advance

    while any(s['cursor'] < len(s['actions']) for s in streams.values()):
        choices = []
        for site, s in streams.items():
            if s['cursor'] < len(s['actions']):
                action = s['actions'][s['cursor']]
                start = first_slot(s['free'], action[-1])
                choices.append((start, site, action))
        start, site, (old_start, old_end, kind, identity, row, claims) = min(choices, key=lambda x: (x[0], x[1]))
        s = streams[site]
        end = start + old_end - old_start
        for r, a, b, d in claims:
            calendars[r].append((start + a, start + b, d))
            result['claims'].append({'resource': r, 'start': start + a, 'end': start + b, 'demand': d})
        s['clock'][old_start] = max(s['clock'].get(old_start, 0), start)
        s['clock'][old_end] = max(s['clock'].get(old_end, 0), end)
        if kind == 'task':
            result['tasks'][identity] = {**row, 'start': start, 'end': end}
        else:
            copied = deepcopy(row)
            copied.update(copy_id=site + ':' + identity, start=start, end=end)
            s['copies'][identity] = copied['copy_id']
            for phase in copied['phases']:
                a, b = phase['start'], phase['end']
                phase.update(start=start + a - old_start, end=start + b - old_start)
                s['clock'][a] = max(s['clock'].get(a, 0), phase['start'])
                s['clock'][b] = max(s['clock'].get(b, 0), phase['end'])
            result['moves'].append(copied)
        s['cursor'] += 1
        s['free'] = end
    result['makespan'] = max(s['free'] for s in streams.values())
    nets = set()
    for site, s in streams.items():
        nets.update(s['local']['nets'])
        result['external_words'] += s['local']['external_words']
        for row in s['local']['allocations']:
            a = deepcopy(row)
            a.update(start=s['clock'][row['start']], end=s['clock'][row['end']])
            if a['origin'] in s['copies']:
                a['origin'] = s['copies'][a['origin']]
            if a['value'] in graph.get('outputs', []) and graph['values'][a['value']]['output_site'] == site:
                a['end'] = result['makespan']
            result['allocations'].append(a)
    result['nets'] = sorted(nets)
    result['wire_cost'] = sum(hardware['nets'][n]['cost'] for n in nets if not hardware['nets'][n].get('fixed'))
    if budget is not None and result['wire_cost'] > budget:
        raise SeedFailure('parallel branch bindings exceed the static connection budget')
    if any({a, b}.issubset(nets) for a, b in hardware.get('incompatible_nets', [])):
        raise SeedFailure('parallel branch bindings require incompatible static connections')
    used = {m['route'] for m in result['moves']}
    if any({a, b}.issubset(used) for a, b in hardware.get('incompatible_routes', [])):
        raise SeedFailure('parallel branch bindings require incompatible routes')
    result['external_regions'] = external_regions(graph, hardware, result)
    from verify import verify
    verify(graph, hardware, result, budget)
    result['seconds'] = time.monotonic() - began
    return result
