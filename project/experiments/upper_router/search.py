"""Model-independent joint access/route search with bounded rip-up rounds."""
from collections import defaultdict
from heapq import heappush, heappop
import random

from geometry import (NativePins, Occupancy, RoutingGrid, access_points, box, segment_shape,
                      net_priority, too_close, via_shapes, validate, need)


def route_shapes(route, tech):
    shapes = [segment_shape(s['layer'], s['a'], s['b'], tech) for s in route['segments']]
    for v in route['via10']:
        shapes.extend(via_shapes('via10', v['at'], tech))
    for point in route['via11']:
        shapes.extend(via_shapes('via11', point, tech))
    return shapes


def connect(starts, goals, tech, occupancy, owner, history, limit, *,
            grid=None, source_via=False, blockers=None):
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
    cuts = {}
    grid = grid or RoutingGrid(tech, ())
    fine = grid.fine < grid.pitch
    for s in sorted(starts):
        costs[s] = 0
        previous[s] = None
        cuts[s] = ()
        heappush(queue, (heuristic(s), 0, s))
    expanded = 0
    blocked = defaultdict(int)
    while queue and expanded < limit:
        _, neg_cost, node = heappop(queue)
        cost = -neg_cost
        if cost != costs[node]:
            continue
        expanded += 1
        if node in goalset:
            path = [node]
            while previous[path[-1]] is not None:
                path.append(previous[path[-1]])
            v10 = tech['via10']
            if not source_via or not too_close(box(path[0][:2], v10['cut']),
                                               box(path[-1][:2], v10['cut']), v10['spacing']):
                return path[::-1], expanded, blocked
        x, y, layer = node
        for nxt in grid.moves(node):
            switching = nxt[2] != layer
            shapes = via_shapes('via11', (x, y), tech) if switching else [segment_shape('M'+str(layer), (x, y), nxt[:2], tech)]
            if switching and fine:
                cut = shapes[0][1]
                if any(too_close(cut, old, tech['via11']['spacing']) for old in cuts[node]):
                    blocked[nxt] += 1
                    continue
            if not occupancy.legal(shapes, owner, blockers):
                blocked[nxt] += 1
                continue
            edge = (tech.get('via_cost', pitch) if switching
                    else abs(x-nxt[0])+abs(y-nxt[1]))
            new = cost+edge+history.get(nxt, 0)*tech.get('history_weight', pitch)
            if new < costs.get(nxt, float('inf')):
                costs[nxt] = new
                previous[nxt] = node
                cuts[nxt] = cuts[node]+(shapes[0][1],) if switching and fine else cuts[node]
                heappush(queue, (new+heuristic(nxt), -new, nxt))
    return None, expanded, blocked


def route_net(net, spec, occupancy, history, limit, native, blockers=None):
    tech = spec['technology']
    name = net['id']
    result = {'segments': [], 'via10': [], 'via11': []}
    tree = set()
    expanded = 0
    blocked = defaultdict(int)
    terminals = [net['driver'], *net['sinks']]
    own_pins = set(terminals)
    grid = RoutingGrid(tech, (spec['pins'][pin] for pin in terminals))
    accesses = {pin: access_points(spec['pins'][pin], tech) for pin in terminals}
    def candidates(pin):
        committed = {tuple(v['at']) for v in result['via10']}
        return [(x, y, 11) for x, y in accesses[pin] if (x, y) not in committed
                and native.exclusive((x, y), own_pins)
                and occupancy.legal(via_shapes('via10', (x, y), tech), name, blockers)]
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
        path, used, failures = connect(tree or starts, goals, tech, occupancy, name, history,
                                       max(0, limit-expanded), grid=grid, source_via=not tree,
                                       blockers=blockers)
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
    native = NativePins(spec)
    history = defaultdict(int)
    nets = {n['id']: n for n in spec['nets']}
    priority = net_priority(spec).__getitem__
    order = sorted(nets, key=priority)
    rng = random.Random(seed)
    attempts = []
    best = None
    locked = {}
    for iteration in range(rounds):
        routes, failed, conflicts = dict(locked), {}, {}
        total = 0
        occupancy = Occupancy(t)
        occupancy.add([(o['layer'], o['rect']) for o in spec.get('obstacles', [])], None)
        for name, wire in locked.items():
            occupancy.add(route_shapes(wire, t), name)
        for name in order:
            trial = occupancy.fork()
            blockers = set()
            r, reason, used, blocked = route_net(nets[name], spec, trial, history, max_expansions,
                                                native, blockers)
            total += used
            for point in blocked:
                history[point] += 1
            if reason:
                failed[name] = reason
                conflicts[name] = sorted(blockers - {name})
            else:
                routes[name] = r
                occupancy.add(route_shapes(r, t), name)
        attempts.append({'round': iteration, 'order': list(order), 'routed': len(routes),
                         'failed': dict(failed), 'blockers': conflicts, 'kept': sorted(locked),
                         'expanded': total})
        score = (-len(routes), sum(len(r['segments']) for r in routes.values()))
        if best is None or score < best[0]:
            best = (score, routes, failed)
        if not failed:
            break
        # A local round preserves unrelated copper. If it stalls, reopen all routes.
        affected = {blocker for ids in conflicts.values() for blocker in ids}
        if iteration % 2 == 0 and affected:
            locked = {name: wire for name, wire in routes.items() if name not in affected}
            tail = sorted(affected - set(failed), key=priority)
        else:
            locked = {}
            tail = [n for n in nets if n not in failed]
            rng.shuffle(tail)
        order = sorted(failed, key=priority)+tail
    _, routes, failed = best
    result = {'schema_version': 'upper-router-result/1', 'routes': routes, 'failed': failed,
              'attempts': attempts, 'status': 'geometry_complete' if not failed else 'partial',
              'physical_qualified': False, 'electrical_status': 'not_evaluated',
              'timing_status': 'not_evaluated', 'context': spec.get('context', {})}
    from check import verify, digest
    result['spec_sha256'] = digest(spec)
    result['geometry_check'] = verify(spec, result)
    return result
