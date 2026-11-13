"""Enumerate the declared transport choices of one qualified binding."""
from heapq import heappop, heappush

from event_execution import Infeasible
from event_replay import ReadyWindow, ReplayDeadlock
from event_replay_plan import event_operation


def estimated_delivery(model, events):
    """Estimate route READY delays for ordering drafts before shared replay."""
    end = 0
    for event in events:
        route = model.routes[event['route']]
        for phase in event.get('phases', (event,)):
            name = phase.get('kind')
            spec = route['phases'][name] if name in ('issue', 'ack') else route
            start = max(end, phase['start'])
            if 'ready_window' in spec:
                start = ReadyWindow.from_spec(spec['ready_window']).next_tick(start)
            end = start + phase['end'] - phase['start']
    return end


def move_key(model, events):
    return tuple((event['value'], event['src'], event['dst'], event.get('output_eviction'),
                  event_operation(model, event), frozenset(model.routes[event['route']].get('nets', ())))
                 for event in events)


def dma_paths(model, moves):
    """Distinguish physical reads before spending probes on timing variants."""
    return tuple(model.dma_read(model.routes[event['route']], event['value']) for event in moves
                 if 'typed_dma' in model.routes[event['route']])


def draft(model, state, binding, ready, protected, prefix, alternatives=None, estimate=None):
    selected = []

    def choose(options, events):
        if len(options) == 1:
            return options[0]
        at = len(selected)
        if at < len(prefix):
            index = prefix[at]
            if type(index) is not int or not 0 <= index < len(options):
                raise ValueError('unknown transport choice')
        else:
            index = 0
            if alternatives is not None:
                moves = [tuple(move) if isinstance(move, list) else (move,) for _, move in options]
                typed = estimate is not None and any('typed_dma' in model.routes[event['route']]
                                                     for path in moves for event in path)
                if typed:
                    distinct = {}
                    for sibling, path in enumerate(moves):
                        distinct.setdefault(move_key(model, path), sibling)
                    siblings = sorted(distinct.values(), key=lambda i: estimated_delivery(model, moves[i]))
                    counts = {}
                    rounds = {}
                    for sibling in siblings:
                        physical = dma_paths(model, moves[sibling])
                        rounds[sibling] = counts.get(physical, 0)
                        counts[physical] = rounds[sibling] + 1
                    siblings.sort(key=rounds.__getitem__)
                    deliveries = {sibling: estimate(events, moves[sibling]) for sibling in siblings}
                else:
                    deliveries = {i: (1, estimated_delivery(model, path)) for i, path in enumerate(moves)}
                index = min(deliveries, key=deliveries.__getitem__)
                for sibling, delivery in deliveries.items():
                    if sibling != index:
                        alternatives.append((delivery, (*selected, sibling)))
        selected.append(index)
        return options[index]

    result = model.expand(state, binding, ready, protected, choose=choose)
    if len(selected) < len(prefix):
        raise ValueError('unused transport choice')
    execution, events = result
    return execution, events, tuple(selected)


def transport_successors(model, state, binding, ready, protected, limit, counters, evaluate, rank,
                         probe_delivery=None):
    # A parent's score guides its unexplored deviations. It is a heuristic,
    # since the changed requests can also move earlier grants.
    unscored = (float('inf'),) * 4
    queue = [(unscored, (1, 0), 0, ())]
    probes = {}
    probe_budget = limit

    def estimate(events, moves):
        nonlocal probe_budget
        prefix = (*events, *moves)
        key = tuple((event['service'], tuple(event['inputs'].items()), tuple(event['outputs'].items()))
                    if event['kind'] == 'stage' else move_key(model, (event,))[0] for event in prefix)
        if key not in probes and probe_budget:
            probe_budget -= 1
            counters['transport_probed'] += 1
            try:
                probes[key] = probe_delivery(prefix)
            except ReplayDeadlock:
                probes[key] = float('inf')
        if key in probes:
            return (int(probes[key] == float('inf')) * 2, probes[key])
        counters['transport_probe_skipped'] += 1
        return (1, estimated_delivery(model, moves))

    remaining = limit
    while queue and (remaining is None or remaining > 0):
        parent_rank, _, _, prefix = heappop(queue)
        counters['transport_attempted'] += 1
        if remaining is not None:
            remaining -= 1
        alternatives = []
        try:
            execution, events, choices = draft(model, state, binding, ready, protected, prefix, alternatives,
                                                estimate if probe_delivery and limit is not None else None)
        except Infeasible:
            result = None
        else:
            result = evaluate(execution, events, choices)
        if alternatives:
            score = parent_rank if result is None else rank(result)
            for delay, path in alternatives:
                heappush(queue, (score, delay, len(path), path))
        if result is not None:
            yield result
    if queue:
        counters['transport_truncated'] += 1
