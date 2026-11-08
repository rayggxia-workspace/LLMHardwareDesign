"""Model-independent joint access/route search with bounded rip-up rounds."""
from collections import defaultdict
from heapq import heappush, heappop
import random

from geometry import (Occupancy, access_points, segment_shape, via_shapes, validate, need)


def route_shapes(route, tech):
    shapes = [segment_shape(s['layer'], s['a'], s['b'], tech) for s in route['segments']]
    for v in route['via10']:
        shapes.extend(via_shapes('via10', v['at'], tech))
    for point in route['via11']:
        shapes.extend(via_shapes('via11', point, tech))
    return shapes


def connect(starts, goals, tech, occupancy, owner, history, limit):
    """Multi-source A*: selecting endpoints and path in one search.

    Starts/goals are legal access or existing tree nodes, never pin centers
    guessed outside the actual M10 conductor. Cost units are DBU plus explicit
    nonnegative via/history penalties, not chip cycles.
    """
    pitch = tech['pitch']
    goalset = set(goals)
    def heuristic(node):
        return min(abs(node[0]-g[0])+abs(node[1]-g[1]) for g in goals)
    queue = []
    previous = {}
    costs = {}
    root = {}
    for s in starts:
        costs[s] = 0
        previous[s] = None
        root[s] = s
        heappush(queue, (heuristic(s), 0, s))
    expanded = 0
    blocked = defaultdict(int)
    while queue and expanded < limit:
        _, cost, node = heappop(queue)
        if cost != costs[node]:
            continue
        expanded += 1
        if node in goalset:
            path = []
            end = node
            while node is not None:
                path.append(node)
                node = previous[node]
            return path[::-1], expanded, blocked
        x, y, layer = node
        moves = [(x+pitch, y, layer), (x-pitch, y, layer)] if layer == 11 else [(x, y+pitch, layer), (x, y-pitch, layer)]
        moves.append((x, y, 23-layer))
        for nxt in moves:
            switching = nxt[2] != layer
            shapes = via_shapes('via11', (x, y), tech) if switching else [segment_shape('M'+str(layer), (x, y), nxt[:2], tech)]
            if not occupancy.legal(shapes, owner):
                blocked[nxt] += 1
                continue
            edge = tech.get('via_cost', pitch) if switching else pitch
            new = cost+edge+history.get(nxt, 0)*tech.get('history_weight', pitch)
            if new < costs.get(nxt, float('inf')):
                costs[nxt] = new
                previous[nxt] = node
                root[nxt] = root[node]
                heappush(queue, (new+heuristic(nxt), new, nxt))
    return None, expanded, blocked


def route_net(net, spec, occupancy, history, limit):
    tech = spec['technology']
    name = net['id']
    result = {'segments': [], 'via10': [], 'via11': []}
    tree = set()
    expanded = 0
    blocked = defaultdict(int)
    def candidates(pin):
        return [(x, y, 11) for x, y in access_points(spec['pins'][pin], tech)
                if occupancy.legal(via_shapes('via10', (x, y), tech), name)]
    starts = candidates(net['driver'])
    if not net['sinks']:
        return result, None, 0, blocked
    if not starts:
        return None, 'grid_access_not_found', 0, blocked
    # Scarce accesses first within a tree. No model/Block names participate.
    sinks = sorted(net['sinks'], key=lambda p: (len(candidates(p)), p))
    for sink in sinks:
        goals = candidates(sink)
        if not goals:
            return None, 'grid_access_not_found', expanded, blocked
        path, used, failures = connect(tree or starts, goals, tech, occupancy, name, history, max(0, limit-expanded))
        expanded += used
        for key, n in failures.items():
            blocked[key] += n
        if path is None:
            return None, 'search_budget_exhausted' if expanded >= limit else 'search_not_found', expanded, blocked
        if not tree:
            result['via10'].append({'pin': net['driver'], 'at': list(path[0][:2])})
        result['via10'].append({'pin': sink, 'at': list(path[-1][:2])})
        for a, b in zip(path, path[1:]):
            if a[2] == b[2]:
                result['segments'].append({'layer': 'M'+str(a[2]), 'a': list(a[:2]), 'b': list(b[:2])})
            elif list(a[:2]) not in result['via11']:
                result['via11'].append(list(a[:2]))
        tree.update(path)
        # Only commit after a sink is connected; caller discards this entire
        # temporary net if any later sink fails.
        occupancy.add(route_shapes(result, tech), name)
    return result, None, expanded, blocked


def route(spec, *, rounds=8, max_expansions=100000, seed=0):
    validate(spec)
    need(type(rounds) is int and rounds > 0 and type(max_expansions) is int and max_expansions > 0, 'positive search budgets required')
    t = spec['technology']
    need(t.get('via_cost', t['pitch']) >= 0 and t.get('history_weight', t['pitch']) >= 0, 'negative route cost')
    history = defaultdict(int)
    nets = {n['id']: n for n in spec['nets']}
    order = sorted(nets, key=lambda n: (min([len(access_points(spec['pins'][p], t)) for p in [nets[n]['driver']]+nets[n]['sinks']]), n))
    rng = random.Random(seed)
    attempts = []
    best = None
    for iteration in range(rounds):
        routes, failed = {}, {}
        total = 0
        for name in order:
            # Rebuild from accepted nets; a failed multi-sink tentative tree
            # must not leave ghost obstacles behind.
            occupancy = Occupancy(t)
            occupancy.add([(o['layer'], o['rect']) for o in spec.get('obstacles', [])], None)
            for other, r in routes.items():
                occupancy.add(route_shapes(r, t), other)
            r, reason, used, blocked = route_net(nets[name], spec, occupancy, history, max_expansions)
            total += used
            for point in blocked:
                history[point] += 1
            if reason:
                failed[name] = reason
            else:
                routes[name] = r
        attempts.append({'round': iteration, 'order': list(order), 'routed': len(routes),
                         'failed': dict(failed), 'expanded': total})
        score = (-len(routes), sum(len(r['segments']) for r in routes.values()))
        if best is None or score < best[0]:
            best = (score, routes, failed)
        if not failed:
            break
        # Failed nets get first access to resources on the next rip-up round.
        tail = [n for n in order if n not in failed]
        rng.shuffle(tail)
        order = sorted(failed)+tail
    _, routes, failed = best
    result = {'schema_version': 'upper-router-result/1', 'routes': routes, 'failed': failed,
              'attempts': attempts, 'status': 'geometry_complete' if not failed else 'partial',
              'physical_qualified': False, 'electrical_status': 'not_evaluated',
              'timing_status': 'not_evaluated', 'context': spec.get('context', {})}
    from check import verify, digest
    result['spec_sha256'] = digest(spec)
    result['geometry_check'] = verify(spec, result)
    return result
