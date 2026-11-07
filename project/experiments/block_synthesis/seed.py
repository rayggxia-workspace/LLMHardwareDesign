"""Fast conservative incumbent with real copies, spill and byte-address reuse.

This scheduler serializes services/copies, so it is a feasible baseline rather
than a throughput model. It evicts dead values first, then farthest-next-use;
dirty values are actually stored before their S allocation is released.
"""
from collections import Counter, defaultdict
import time


class SeedFailure(ValueError):
    pass


def external_regions(graph, hardware, plan):
    """Stable external slots, shared across loads of a value; no silent RAM infinity.

    Extents are conservative permanent reservations for this invocation. Reuse
    of external slots across lifetimes is not optimized in this first version.
    Capacity is checked independently when provided; absence means unqualified.
    """
    ext = hardware['external']
    names = {n for n, v in graph['values'].items() if v.get('site') == ext or v.get('external_copy')}
    names.update(m['value'] for m in plan['moves'] if ext in (m['src'], m['dst']))
    rows, cursor = [], 0
    for name in sorted(names):
        words = graph['values'][name]['words']
        rows.append({'value': name, 'address_words': cursor, 'words': words})
        cursor += words
    if hardware.get('external_capacity_words') is not None and cursor > hardware['external_capacity_words']:
        raise SeedFailure('stable external region allocation exceeds declared memory capacity')
    return rows


def serial_seed(graph, hardware, bindings, budget=None):
    began = time.monotonic()
    ext = hardware['external']
    tasks = {t['id']: t for t in graph['tasks']}
    order, pending, done = [], list(tasks), set()
    while pending:
        ready = [tid for tid in pending if set(tasks[tid].get('after', [])).issubset(done) and
                 {graph['values'][n]['producer'] for n in tasks[tid]['inputs'] if 'producer' in graph['values'][n]}.issubset(done)]
        if not ready:
            raise SeedFailure('cycle or missing task precedence')
        for tid in ready:
            order.append(tid)
            pending.remove(tid)
            done.add(tid)
    remaining = Counter(n for t in tasks.values() for n in set(t['inputs']))
    next_uses = defaultdict(list)
    for index, tid in enumerate(order):
        for n in set(tasks[tid]['inputs']):
            next_uses[n].append(index)
    plan = {'status': 'HEURISTIC', 'best_bound': 0, 'tasks': {}, 'moves': [], 'allocations': [],
            'claims': [], 'nets': [], 'wire_cost': 0, 'external_words': 0,
            'optimality_scope': 'verified serial incumbent; no global optimality claim'}
    resident, external, net_set, used_routes = {}, set(), set(), set()
    now = 0

    def retain(name):
        return name in graph.get('outputs', []) and graph['values'][name]['output_site'] != ext

    def release(site, name):
        nonlocal now
        row = resident.pop((site, name))
        row['end'] = now

    def route_for(src, dst, words):
        options = []
        for rid, r in hardware['routes'].items():
            if not r.get('qualified') or (r['src'], r['dst']) != (src, dst):
                continue
            if not r.get('min_words', 1) <= words <= r.get('max_words', 1):
                continue
            routes = used_routes | {rid}
            if any({a, b}.issubset(routes) for a, b in hardware.get('incompatible_routes', [])):
                continue
            nets = net_set | set(r.get('nets', []))
            cost = sum(hardware['nets'][n]['cost'] for n in nets if not hardware['nets'][n].get('fixed'))
            if budget is not None and cost > budget:
                continue
            options.append(((sum(p['ticks'] for p in r['phases']), cost, rid), rid, r))
        if not options:
            raise SeedFailure(f'no legal seed copy {src}->{dst}, {words} words')
        _, rid, route = min(options)
        return rid, route

    def transfer(name, src, dst, *, final=False):
        nonlocal now
        words = graph['values'][name]['words']
        rid, route = route_for(src, dst, words)
        cid = f'seed-copy-{len(plan["moves"])}'
        start, phases = now, []
        for phase in route['phases']:
            end = now + phase['ticks']
            phases.append({'name': phase['name'], 'start': now, 'end': end})
            for resource in phase.get('resources', []):
                plan['claims'].append({'resource': resource, 'start': now, 'end': end, 'demand': 1})
            now = end
        for hold in route.get('holds', []):
            plan['claims'].append({'resource': hold['resource'],
                'start': phases[hold.get('first_phase', 0)]['start'], 'end': now, 'demand': 1})
        move = {'value': name, 'src': src, 'dst': dst, 'route': rid, 'words': words,
                'copy_id': cid, 'start': start, 'end': now, 'phases': phases, 'final': final}
        plan['moves'].append(move)
        used_routes.add(rid)
        net_set.update(route.get('nets', []))
        if ext in (src, dst):
            plan['external_words'] += words
        if dst == ext:
            external.add(name)
        else:
            resident[dst, name]['origin'] = cid
        return move

    def free_address(site, words):
        cursor = 0
        rows = sorted((r for (s, _), r in resident.items() if s == site), key=lambda r: r['address'])
        for r in rows:
            if cursor + words <= r['address']:
                return cursor
            cursor = r['address'] + r['words']
        return cursor if cursor + words <= hardware['sites'][site]['words'] else None

    def allocate(site, name, words, origin, protected=()):
        nonlocal now
        while (address := free_address(site, words)) is None:
            victims = [(n, r) for (s, n), r in resident.items() if s == site and n not in protected and not retain(n)]
            if not victims:
                raise SeedFailure(f'{site}: tile operands/output/scratch do not fit, or fragmentation needs another plan')
            def priority(item):
                n, row = item
                return (remaining[n] == 0, n in external,
                        min(next_uses[n], default=len(order)+1), row['words'])
            name_v, row_v = max(victims, key=priority)
            if remaining[name_v] and name_v not in external:
                transfer(name_v, site, ext)
            release(site, name_v)
        row = {'id': f'seed-alloc-{len(plan["allocations"])}', 'value': name, 'site': site,
               'words': words, 'start': now, 'end': None, 'address': address, 'origin': origin}
        resident[site, name] = row
        plan['allocations'].append(row)
        return row

    for name, v in graph['values'].items():
        if 'producer' not in v:
            if v['site'] == ext or v.get('external_copy'):
                external.add(name)
            if v['site'] != ext:
                # Initial residency is a physical input condition; cannot evict
                # one initial object before allocating the others at time zero.
                address = free_address(v['site'], v['words'])
                if address is None:
                    raise SeedFailure('declared initial S image does not fit')
                allocate(v['site'], name, v['words'], 'initial', protected=tuple(graph['values']))
    for index, tid in enumerate(order):
        task = tasks[tid]
        service = hardware['services'][bindings[tid]]
        site = service['site']
        protected = set(task['inputs'])
        for name in dict.fromkeys(task['inputs']):
            if (site, name) in resident:
                continue
            sources = [s for s, n in resident if n == name]
            source = ext if name in external else (sources[0] if sources else None)
            if source is None:
                raise SeedFailure('lost a live input: ' + name)
            try:
                route_for(source, site, graph['values'][name]['words'])
            except SeedFailure:
                if source == ext:
                    raise
                transfer(name, source, ext)
                source = ext
            allocate(site, name, graph['values'][name]['words'], None, protected)
            transfer(name, source, site)
        for name in task['outputs']:
            allocate(site, name, graph['values'][name]['words'], 'producer:' + tid, protected)
            protected.add(name)
        scratch_name = tid + ':scratch:' + bindings[tid]
        if service.get('scratch_words'):
            scratch = allocate(site, scratch_name, service['scratch_words'], None, protected)
            scratch['id'] = scratch_name
            scratch['value'] = None
        start = now
        now += service['ticks']
        plan['tasks'][tid] = {'service': bindings[tid], 'site': site, 'start': start, 'end': now}
        for r in service['resources']:
            plan['claims'].append({'resource': r, 'start': start, 'end': now, 'demand': 1})
        if service.get('scratch_words'):
            release(site, scratch_name)
        for name in set(task['inputs']):
            remaining[name] -= 1
            next_uses[name].remove(index)
        for name in task['outputs']:
            if name in graph.get('outputs', []) and graph['values'][name]['output_site'] == ext:
                transfer(name, site, ext, final=True)
        for (s, name) in list(resident):
            if remaining[name] == 0 and not retain(name):
                release(s, name)
    for (site, name) in list(resident):
        release(site, name)
    plan.update(makespan=now, nets=sorted(net_set), seconds=time.monotonic()-began,
                wire_cost=sum(hardware['nets'][n]['cost'] for n in net_set if not hardware['nets'][n].get('fixed')))
    plan['external_regions'] = external_regions(graph, hardware, plan)
    from verify import verify
    verify(graph, hardware, plan, budget)
    return plan
