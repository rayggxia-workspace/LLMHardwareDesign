"""Check the grants in an emitted replay trace against the arbitration contract."""
from collections import defaultdict

from event_execution import Model
from event_replay_plan import Decision, intents


def verify_grants(tasks, hardware, rows):
    model = Model(hardware)
    dependencies = {task['id']: frozenset(task.get('after', ())) for task in tasks}
    decisions = [Decision(row, dependencies[row['id']]) for row in rows]
    operations = intents(model, decisions)
    events = [event for row in rows for event in row['evaluation']['events']]
    # Use only reported intervals to derive eligibility and releases. No call
    # to the planner, its checkpoint reconstruction, or its grant loop.
    ready_at = defaultdict(list)
    release_at = defaultdict(list)
    ticks = set()
    for i, (operation, event) in enumerate(zip(operations, events)):
        phases = event.get('phases', (event,))
        ready = max([operation.release] + [events[p]['end'] for p in operation.after])
        for j, (phase, interval) in enumerate(zip(operation.phases, phases)):
            start, end = interval['start'], interval['end']
            claims = phase.claims + (operation.holds if j == 0 else ())
            releases = phase.claims + (operation.holds if j == len(phases) - 1 else ())
            ready_at[ready].append((phase.priority, ready, i, j, start, claims))
            release_at[end].extend(releases)
            ticks.update((ready, start, end))
            ready = end

    free = model.capacity.copy()
    waiting = []
    for tick in sorted(ticks):
        for resource, units in release_at[tick]:
            free[resource] += units
        pending = sorted(waiting + ready_at[tick])
        waiting = []
        for request in pending:
            _, _, _, _, start, claims = request
            can_start = all(free[resource] >= units for resource, units in claims)
            if start < tick or can_start != (start == tick):
                raise ValueError(f'arbitration grant differs at tick {tick}')
            if can_start:
                for resource, units in claims:
                    free[resource] -= units
            else:
                waiting.append(request)
    if waiting or free != model.capacity:
        raise ValueError('arbitration trace did not drain')
