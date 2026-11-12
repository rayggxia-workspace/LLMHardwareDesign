"""Enumerate the declared transport choices of one qualified binding."""
from heapq import heappop, heappush

from event_execution import Infeasible


def draft(model, state, binding, ready, protected, prefix, enqueue=None):
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
            if enqueue is not None:
                for sibling in range(1, len(options)):
                    enqueue((*selected, sibling))
        selected.append(index)
        return options[index]

    result = model.expand(state, binding, ready, protected, choose=choose)
    if len(selected) < len(prefix):
        raise ValueError('unused transport choice')
    return result


def drafts(model, state, binding, ready, protected, limit, counters):
    # Explore single deviations before combinations, keeping the old choice
    # first as a baseline. Only completed attempts consume the search limit.
    queue = [(0, 0, ())]

    def enqueue(prefix):
        heappush(queue, (sum(index != 0 for index in prefix), sum(prefix), prefix))

    remaining = limit
    while queue and (remaining is None or remaining > 0):
        _, _, prefix = heappop(queue)
        counters['transport_attempted'] += 1
        if remaining is not None:
            remaining -= 1
        try:
            execution, events = draft(model, state, binding, ready, protected, prefix, enqueue)
        except Infeasible:
            continue
        yield execution, events, prefix
    if queue:
        counters['transport_truncated'] += 1
