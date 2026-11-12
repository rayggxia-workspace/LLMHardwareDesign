"""Check the grants in an emitted replay trace against the arbitration contract."""
from collections import Counter, defaultdict

from event_execution import Model
from event_replay import phase_dependencies
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
    issue_expires = defaultdict(list)
    ticks = set()
    for i, (operation, event) in enumerate(zip(operations, events)):
        phases = event.get('phases', (event,))
        for j, (phase, interval) in enumerate(zip(operation.phases, phases)):
            parents = phase_dependencies(operations, i, j)
            ready = max([0 if j else operation.release] + [
                events[p].get('phases', (events[p],))[q]['end'] for p, q in parents])
            start, end = interval['start'], interval['end']
            if start < ready:
                raise ValueError('grant precedes phase dependency')
            claims = phase.claims + (operation.holds if j == 0 else ())
            releases = phase.claims + (operation.holds if j == len(phases) - 1 else ())
            ready_at[ready].append((phase.priority, ready, i, j, start, claims))
            release_at[end].extend(releases)
            ticks.update((ready, start, end))
            for resource, units in phase.claims:
                if resource in model.issue_rates:
                    expires = start + model.issue_rates[resource][0]
                    issue_expires[expires].append((resource, units))
                    ticks.add(expires)

    free = model.capacity.copy()
    issue_count = Counter()
    waiting = []
    for tick in sorted(ticks):
        for resource, units in release_at[tick]:
            free[resource] += units
        for resource, units in issue_expires[tick]:
            issue_count[resource] -= units
        pending = sorted(waiting + ready_at[tick])
        waiting = []
        for request in pending:
            _, _, _, _, start, claims = request
            can_start = all(free[resource] >= units for resource, units in claims)
            can_start = can_start and all(
                resource not in model.issue_rates or issue_count[resource] + units <= model.issue_rates[resource][1]
                for resource, units in claims)
            if start < tick or can_start != (start == tick):
                raise ValueError(f'arbitration grant differs at tick {tick}')
            if can_start:
                for resource, units in claims:
                    free[resource] -= units
                    if resource in model.issue_rates:
                        issue_count[resource] += units
            else:
                waiting.append(request)
    if waiting or free != model.capacity or any(issue_count.values()):
        raise ValueError('arbitration trace did not drain')
