"""Advance a branch's operation intents through shared hardware resources."""
from collections import Counter
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


@dataclass(frozen=True)
class Grant:
    operation: int
    phase: int
    start: int
    end: int


class ReplayDeadlock(ValueError):
    """Pending operations have no advancing event."""


def replay(operations, capacity, *, previous=()):
    """Simulate from reset. Lower priority numbers win among ready phases.

    At each tick, completions free resources before grants. A first grant
    acquires the operation's holds atomically, and the final completion
    releases them. Between grants, only pending arrival or completion events
    can change eligibility.
    """
    successors = [[] for _ in operations]
    dependencies = []
    for index, operation in enumerate(operations):
        if (not operation.phases or type(operation.release) is not int or operation.release < 0
                or any(type(dep) is not int or not 0 <= dep < index for dep in operation.after)):
            raise ValueError('invalid replay operation or dependency')
        holds = dict(operation.holds)
        for phase in operation.phases:
            if (type(phase.ticks) is not int or phase.ticks < 1 or type(phase.priority) is not int
                    or any(type(units) is not int or not 0 < units <= capacity.get(resource, 0)
                           for resource, units in (*phase.claims, *operation.holds))
                    or holds.keys() & dict(phase.claims).keys()
                    or len(holds) != len(operation.holds)
                    or len(dict(phase.claims)) != len(phase.claims)):
                raise ValueError('invalid replay phase duration, priority or resource claim')
        for dependency in operation.after:
            successors[dependency].append(index)
        dependencies.append(len(operation.after))

    prefix_count = len(previous)
    if prefix_count >= len(operations) and previous:
        raise ValueError('replay requires an appended operation')
    # Until a new operation could first become ready, it cannot change a grant.
    # Later grants, including grants at the boundary tick, are speculative.
    tick = min((max([op.release] + [previous[p][-1].end for p in op.after])
                for op in operations[prefix_count:] if all(p < prefix_count for p in op.after)), default=0)
    if not previous:
        tick = 0
    grants = [[grant for grant in row if grant.start < tick] for row in previous]
    grants.extend([] for _ in operations[prefix_count:])
    completed = {}
    running = []
    occupied = Counter()
    for index, prefix in enumerate(grants):
        if not prefix:
            continue
        operation = operations[index]
        last = prefix[-1]
        if len(prefix) == len(operation.phases) and last.end < tick:
            completed[index] = last.end
            for child in successors[index]:
                dependencies[child] -= 1
            continue
        occupied.update(dict(operation.holds))
        if last.end >= tick:
            occupied.update(dict(operation.phases[last.phase].claims))
            heappush(running, (last.end, index, last.phase))

    arrivals = []
    for index, operation in enumerate(operations):
        prefix = grants[index]
        if prefix and index not in completed and prefix[-1].end < tick:
            heappush(arrivals, (prefix[-1].end, index, len(prefix)))
        if not prefix and not dependencies[index]:
            ready = max([operation.release] + [completed[p] for p in operation.after])
            heappush(arrivals, (ready, index, 0))
    pending = []
    finished = len(completed)
    while finished < len(operations):
        while running and running[0][0] == tick:
            _, index, phase_index = heappop(running)
            operation = operations[index]
            occupied.subtract(dict(operation.phases[phase_index].claims))
            if phase_index + 1 < len(operation.phases):
                heappush(arrivals, (tick, index, phase_index + 1))
                continue
            occupied.subtract(dict(operation.holds))
            finished += 1
            for child in successors[index]:
                dependencies[child] -= 1
                if not dependencies[child]:
                    heappush(arrivals, (max(tick, operations[child].release), child, 0))
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
            if any(occupied[r] + units > capacity[r] for r, units in claims):
                waiting.append(request)
                continue
            occupied.update(dict(claims))
            end = tick + phase.ticks
            heappush(running, (end, index, phase_index))
            grants[index].append(Grant(index, phase_index, tick, end))
        pending = waiting
        if finished == len(operations):
            break
        future = [queue[0][0] for queue in (running, arrivals) if queue]
        if not future:
            raise ReplayDeadlock(f'no replay progress at tick {tick}: {pending}')
        tick = min(future)
    return tuple(tuple(operation) for operation in grants)
