"""Advance a branch's operation intents through shared hardware resources."""
from collections import Counter, deque
from dataclasses import dataclass
from heapq import heappop, heappush


@dataclass(frozen=True)
class Phase:
    name: str
    ticks: int
    claims: tuple[tuple[str, int], ...] = ()
    priority: int = 0

    @classmethod
    def from_spec(cls, name, ticks, spec):
        return cls(name, ticks, tuple(sorted(spec['claims'].items())), spec.get('priority', 0))


@dataclass(frozen=True)
class Operation:
    phases: tuple[Phase, ...]
    after: frozenset[int] = frozenset()
    release: int = 0
    holds: tuple[tuple[str, int], ...] = ()
    phase_after: tuple[frozenset[tuple[int, int]], ...] = ()


@dataclass(frozen=True)
class Grant:
    operation: int
    phase: int
    start: int
    end: int


class ReplayDeadlock(ValueError):
    """Pending operations have no advancing event."""


def phase_dependencies(operations, index, phase):
    operation = operations[index]
    extra = operation.phase_after[phase] if operation.phase_after else frozenset()
    if phase:
        return extra | {(index, phase - 1)}
    return extra | {(parent, len(operations[parent].phases) - 1) for parent in operation.after}


def replay(operations, capacity, *, previous=(), issue_rates=None):
    """Simulate from reset. Lower priority numbers win among ready phases.

    At each tick, completions free resources before grants. A first grant
    acquires the operation's holds atomically, and the final completion
    releases them. Between grants, only pending arrival or completion events
    can change eligibility.
    """
    issue_rates = issue_rates or {}
    successors = {}
    dependencies = {}
    release = {}
    prerequisites = {}
    for index, operation in enumerate(operations):
        if (not operation.phases or type(operation.release) is not int or operation.release < 0
                or any(type(dep) is not int or not 0 <= dep < index for dep in operation.after)
                or operation.phase_after and len(operation.phase_after) != len(operation.phases)):
            raise ValueError('invalid replay operation or dependency')
        holds = dict(operation.holds)
        if holds.keys() & issue_rates.keys():
            raise ValueError('rate-limited issue ports cannot be held between phases')
        for phase_index, phase in enumerate(operation.phases):
            if (type(phase.ticks) is not int or phase.ticks < 1 or type(phase.priority) is not int
                    or any(type(units) is not int or not 0 < units <= capacity.get(resource, 0)
                           for resource, units in (*phase.claims, *operation.holds))
                    or holds.keys() & dict(phase.claims).keys()
                    or len(holds) != len(operation.holds)
                    or len(dict(phase.claims)) != len(phase.claims)
                    or any(r in issue_rates and units > issue_rates[r][1] for r, units in phase.claims)):
                raise ValueError('invalid replay phase duration, priority or resource claim')
            current = index, phase_index
            parents = phase_dependencies(operations, *current)
            if any(parent not in prerequisites for parent in parents):
                raise ValueError('phase dependency must name an earlier phase')
            prerequisites[current] = parents
            dependencies[current] = len(parents)
            release[current] = 0 if phase_index else operation.release
            for parent in parents:
                successors.setdefault(parent, []).append(current)

    prefix_count = len(previous)
    if prefix_count >= len(operations) and previous:
        raise ValueError('replay requires an appended operation')
    # Until a new operation could first become ready, it cannot change a grant.
    # Later grants, including grants at the boundary tick, are speculative.
    first_phases = ((index, 0) for index in range(prefix_count, len(operations)))
    tick = min((max([release[key]] + [previous[p][j].end for p, j in prerequisites[key]])
                for key in first_phases if all(p < prefix_count for p, _ in prerequisites[key])), default=0)
    grants = [[grant for grant in row if grant.start < tick] for row in previous]
    grants.extend([] for _ in operations[prefix_count:])
    completed = {}
    running = []
    occupied = Counter()
    issues = {resource: deque() for resource in issue_rates}
    used_issues = Counter()

    def record_issues(claims, start):
        for resource, units in claims:
            if resource in issue_rates:
                expires = start + issue_rates[resource][0]
                if expires > tick:
                    issues[resource].append((expires, units))
                    used_issues[resource] += units

    if issue_rates:
        cutoff = tick - max(window for window, _ in issue_rates.values())
        accepted = (grant for prefix in grants for grant in prefix if grant.start > cutoff)
        for grant in sorted(accepted, key=lambda grant: grant.start):
            record_issues(operations[grant.operation].phases[grant.phase].claims, grant.start)
    finished = 0
    for index, prefix in enumerate(grants):
        if not prefix:
            continue
        operation = operations[index]
        last = prefix[-1]
        for grant in prefix:
            if grant.end < tick:
                key = index, grant.phase
                completed[key] = grant.end
                for child in successors.get(key, ()):
                    dependencies[child] -= 1
        if len(prefix) == len(operation.phases) and last.end < tick:
            finished += 1
            continue
        occupied.update(dict(operation.holds))
        if last.end >= tick:
            occupied.update(dict(operation.phases[last.phase].claims))
            heappush(running, (last.end, index, last.phase))

    arrivals = []
    for key, parents in prerequisites.items():
        index, phase = key
        if phase >= len(grants[index]) and not dependencies[key]:
            ready = max([release[key]] + [completed[parent] for parent in parents])
            heappush(arrivals, (ready, index, phase))
    pending = []
    while finished < len(operations):
        for resource, history in issues.items():
            while history and history[0][0] <= tick:
                _, units = history.popleft()
                used_issues[resource] -= units
        while running and running[0][0] == tick:
            _, index, phase_index = heappop(running)
            operation = operations[index]
            occupied.subtract(dict(operation.phases[phase_index].claims))
            if phase_index + 1 == len(operation.phases):
                occupied.subtract(dict(operation.holds))
                finished += 1
            for child in successors.get((index, phase_index), ()):
                dependencies[child] -= 1
                if not dependencies[child]:
                    heappush(arrivals, (max(tick, release[child]), *child))
        while arrivals and arrivals[0][0] <= tick:
            ready, index, phase_index = heappop(arrivals)
            phase = operations[index].phases[phase_index]
            pending.append((phase.priority, ready, index, phase_index))

        waiting = []
        for request in sorted(pending):
            _, _, index, phase_index = request
            operation = operations[index]
            phase = operation.phases[phase_index]
            claims = phase.claims + (operation.holds if phase_index == 0 else ())
            if (any(occupied[r] + units > capacity[r] for r, units in claims)
                    or any(r in issue_rates and used_issues[r] + units > issue_rates[r][1]
                           for r, units in phase.claims)):
                waiting.append(request)
                continue
            occupied.update(dict(claims))
            record_issues(phase.claims, tick)
            end = tick + phase.ticks
            heappush(running, (end, index, phase_index))
            grants[index].append(Grant(index, phase_index, tick, end))
        pending = waiting
        if finished == len(operations):
            break
        future = [queue[0][0] for queue in (running, arrivals) if queue]
        if pending:
            future.extend(history[0][0] for history in issues.values() if history)
        if not future:
            raise ReplayDeadlock(f'no replay progress at tick {tick}: {pending}')
        tick = min(future)
    return tuple(tuple(operation) for operation in grants)
