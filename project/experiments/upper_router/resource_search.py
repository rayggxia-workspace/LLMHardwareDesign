"""Route logical nets with optional, independently supplied combinational repeaters."""
from collections import defaultdict
from itertools import chain
import random

from check import digest
from geometry import NativePins, Occupancy, need, net_priority, validate
from repeaters import allocation_chain, check_allocations, inventory, physical_nets, projection
from search import route_net, route_shapes


def length(route):
    return sum(abs(s['a'][0]-s['b'][0])+abs(s['a'][1]-s['b'][1]) for s in route['segments'])


def position(pin, pins):
    return min((r[0]+r[2], r[1]+r[3]) for r in pins[pin])


def distance(a, b, pins):
    ax, ay = position(a, pins)
    bx, by = position(b, pins)
    return (abs(ax-bx)+abs(ay-by))/2


def choices(net, pins, resources, limit, max_repeaters):
    yield None
    if not net['sinks'] or not resources or not max_repeaters:
        return
    sinks = sorted(net['sinks'])
    for branch in [sinks] + ([[sink] for sink in sinks] if len(sinks) > 1 else []):
        frontier = [((), net['driver'], ())]
        for _ in range(min(max_repeaters, len(resources))):
            ranked = []
            for prior, driver, legs in frontier:
                for name, relay in resources.items():
                    if name in prior:
                        continue
                    route = prior+(name,)
                    output = relay['output']['id']
                    incoming = legs+(distance(driver, relay['input']['id'], pins),)
                    last = max(distance(output, sink, pins) for sink in branch)
                    ranked.append((max(*incoming, last), sum(incoming)+last, route, output, incoming))
            frontier = [(names, output, legs) for _, _, names, output, legs in sorted(ranked)[:limit]]
            for names, _, _ in frontier:
                allocation = {'repeater': names[0]} if len(names) == 1 else {'chain': list(names)}
                yield {**allocation, 'sinks': branch}


def estimated_load(net, route, limits, caps, electrical):
    wire = length(route) * electrical.get('wire_cap_ff_per_dbu', 0)
    vias = (len(route['via10']) * electrical.get('via10_cap_ff', 0)
            + len(route['via11']) * electrical.get('via11_cap_ff', 0))
    load = wire+vias+sum(caps.get(p, 0) for p in net['sinks'])
    limit = limits.get(net['driver'])
    return {'load_ff': load, 'limit_ff': limit, 'over_ff': max(0, load-limit) if limit is not None else 0}


def choose_route(net, index, spec, resources, options, occupancy, history, limit, electrical, caps, limits,
                 native, *, previous=None):
    best = None
    reasons = set()
    expanded = 0
    for option in options:
        stages = physical_nets(net, index, option, resources)
        trial = occupancy.fork()
        routes = {}
        scores = {}
        budget = limit
        for stage in stages:
            wire, reason, used, blocked = route_net(stage, spec, trial, history, budget, native)
            budget -= used
            expanded += used
            for point, count in blocked.items():
                history[point] += count
            if wire is None:
                reasons.add(reason)
                break
            routes[stage['id']] = wire
            scores[stage['id']] = estimated_load(stage, wire, limits, caps, electrical)
        if len(routes) == len(stages):
            overload = [v['over_ff'] for v in scores.values() if v['over_ff'] > 0]
            unchanged = previous is not None and routes == previous
            score = (len(overload), sum(overload), unchanged,
                     sum(length(r) for r in routes.values())
                     + electrical.get('repeater_penalty_dbu', spec['technology']['pitch'])*len(allocation_chain(option)),
                     sum(len(r['via10'])+len(r['via11']) for r in routes.values()))
            if best is None or score < best[0]:
                best = score, option, routes, scores
            # Preserve a short direct route when estimated limits are met.
            if option is None and not overload and previous is None:
                break
    reason = next((r for r in ('search_budget_exhausted', 'search_not_found', 'grid_access_not_found')
                   if r in reasons), 'search_not_found')
    return best, reason, expanded


def route_resources(spec, data, *, rounds=8, max_expansions=100000, seed=0, candidate_limit=12,
                    previous=None, targets=(), max_repeaters=1):
    need(all(type(x) is int and x > 0 for x in (rounds, max_expansions, candidate_limit)),
         'positive search budgets required')
    need(type(max_repeaters) is int and max_repeaters >= 0, 'invalid repeater stage bound')
    pins, resources = inventory(spec, data)
    electrical = data.get('electrical', {})
    caps = {**electrical.get('sink_caps_ff', {}),
            **{r['input']['id']: r['input_cap_ff'] for r in resources.values() if 'input_cap_ff' in r}}
    limits = {**electrical.get('driver_limits_ff', {}),
              **{r['output']['id']: r['output_limit_ff'] for r in resources.values() if 'output_limit_ff' in r}}
    tech = spec['technology']
    obstacles = list(chain(spec.get('obstacles', []), *(r.get('obstacles', []) for r in resources.values())))
    expanded_spec = {**spec, 'pins': pins, 'obstacles': obstacles}
    native = NativePins(expanded_spec)
    nets = {n['id']: n for n in spec['nets']}
    validate_opts = projection(spec, data, {n: None for n in nets}, {})
    validate(validate_opts)
    indices = {n: i for i, n in enumerate(sorted(nets))}
    priority = net_priority(spec).__getitem__
    order = sorted(nets, key=priority)
    history = defaultdict(int)
    locked = {}
    prior_routes = {}
    if previous is not None:
        check_allocations(spec, data, previous)
        need(not previous['failed'] and targets and set(targets) <= set(nets), 'invalid repair targets')
        order = [n for n in order if n in targets]
        old_routes = previous['physical_routes']['routes']
        for name in nets:
            allocation = previous['allocations'][name]
            stage_ids = [n['id'] for n in physical_nets(nets[name], indices[name], allocation, resources)]
            segments = {i: old_routes[i] for i in stage_ids}
            if name not in targets:
                locked[name] = allocation, segments
                continue
            prior_routes[name] = segments
            for wire in segments.values():
                for edge in wire['segments']:
                    layer = int(edge['layer'][1:])
                    for point in (edge['a'], edge['b']):
                        history[(*point, layer)] += 1
    rng = random.Random(seed)
    attempts = []
    best = None
    for _ in range(rounds):
        occupancy = Occupancy(tech)
        occupancy.add([(o['layer'], o['rect']) for o in obstacles], None)
        available = dict(resources)
        allocations, routes, failed, estimates = {}, {}, {}, {}
        stressed = []
        for name, (option, segments) in locked.items():
            allocations[name] = option
            for relay in allocation_chain(option):
                del available[relay]
            routes.update(segments)
            for stage in physical_nets(nets[name], indices[name], option, resources):
                wire = segments[stage['id']]
                occupancy.add(route_shapes(wire, tech), stage['id'])
                estimates[stage['id']] = estimated_load(stage, wire, limits, caps, electrical)
        expanded = 0
        for name in order:
            pick, reason, work = choose_route(
                nets[name], indices[name], expanded_spec, resources,
                choices(nets[name], pins, available, candidate_limit, max_repeaters), occupancy, history,
                max_expansions, electrical, caps, limits, native, previous=prior_routes.get(name))
            expanded += work
            if pick is None:
                failed[name] = reason
                continue
            score, option, segments, loads = pick
            allocations[name] = option
            for relay in allocation_chain(option):
                del available[relay]
            if score[0]:
                stressed.append(name)
            routes.update(segments)
            estimates.update(loads)
            for key, segment in segments.items():
                occupancy.add(route_shapes(segment, tech), key)
        attempts.append({'order': order, 'failed': failed, 'estimated_overload_nets': stressed,
                         'expanded': expanded})
        over = [v['over_ff'] for v in estimates.values() if v['over_ff'] > 0]
        unchanged = sum(all(routes.get(k) == v for k, v in old.items())
                        for old in prior_routes.values())
        score = (len(failed), len(over), sum(over), unchanged, sum(length(r) for r in routes.values()))
        if best is None or score < best[0]:
            best = score, allocations, routes, failed, estimates
        if not failed and not stressed and not unchanged:
            break
        urgent = set(failed) | set(stressed)
        tail = [n for n in order if n not in urgent]
        rng.shuffle(tail)
        order = sorted(urgent, key=priority) + tail
    _, allocations, routes, failed, estimates = best
    physical = projection(spec, data, allocations, failed)
    stage_failed = {'segment/%d/0' % indices[n]: reason for n, reason in failed.items()}
    status = 'partial' if failed else 'geometry_complete'
    physical_routes = {'schema_version': 'upper-router-result/1', 'routes': routes, 'failed': stage_failed,
                       'status': status, 'physical_qualified': False, 'electrical_status': 'not_evaluated',
                       'timing_status': 'not_evaluated', 'spec_sha256': digest(physical),
                       'context': physical['context']}
    result = {'schema_version': 'upper-repeater-result/1', 'allocations': allocations, 'failed': failed,
              'physical_spec': physical, 'physical_routes': physical_routes, 'attempts': attempts,
              'estimated_stage_loads': estimates, 'status': status, 'physical_qualified': False,
              'used_virtual': sorted(r for a in allocations.values() for r in allocation_chain(a)
                                     if resources[r]['status'] == 'virtual')}
    result['geometry_check'] = check_allocations(spec, data, result)
    return result
