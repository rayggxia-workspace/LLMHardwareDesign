"""Enumerate the declared transport choices of one qualified binding."""
from heapq import heappop, heappush

from event_execution import Infeasible
from event_replay import ReadyWindow


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


def draft(model, state, binding, ready, protected, prefix, alternatives=None):
    selected = []

    def choose(options):
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
                deliveries = [estimated_delivery(model, events if isinstance(events, list) else (events,))
                              for _, events in options]
                index = min(range(len(options)), key=deliveries.__getitem__)
                for sibling, delivery in enumerate(deliveries):
                    if sibling != index:
                        alternatives.append((delivery - deliveries[index], (*selected, sibling)))
        selected.append(index)
        return options[index]

    result = model.expand(state, binding, ready, protected, choose=choose)
    if len(selected) < len(prefix):
        raise ValueError('unused transport choice')
    execution, events = result
    return execution, events, tuple(selected)


def transport_successors(model, state, binding, ready, protected, limit, counters, evaluate, rank):
    # A parent's score guides its unexplored deviations. It is a heuristic,
    # since the changed requests can also move earlier grants.
    unscored = (float('inf'),) * 4
    queue = [(unscored, 0, 0, ())]

    remaining = limit
    while queue and (remaining is None or remaining > 0):
        parent_rank, _, _, prefix = heappop(queue)
        counters['transport_attempted'] += 1
        if remaining is not None:
            remaining -= 1
        alternatives = []
        try:
            execution, events, choices = draft(model, state, binding, ready, protected, prefix, alternatives)
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
