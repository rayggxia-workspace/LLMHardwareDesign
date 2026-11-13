"""Advance a branch's operation intents through shared hardware resources."""
from collections import Counter, deque
from copy import deepcopy
from dataclasses import dataclass
from heapq import heappop, heappush

from dma_read import BeatReceipt, Read, ReadFabric
from ffn_a import P_COUNT, ActivationWindow
from ffn_mid import MidTile
from sram_feeder import Access, SramFeeder


@dataclass(frozen=True)
class ReadyWindow:
    """An external READY gate, closed for the first residues of a period."""
    period: int
    closed: int
    offset: int

    @classmethod
    def from_spec(cls, spec):
        if not isinstance(spec, dict) or spec.keys() != {'period', 'closed', 'offset'}:
            raise ValueError('invalid phase READY window')
        gate = cls(**spec)
        if not gate.valid():
            raise ValueError('invalid phase READY window')
        return gate

    def valid(self):
        return (all(type(value) is int for value in (self.period, self.closed, self.offset))
                and 0 <= self.closed < self.period and 0 <= self.offset < self.period)

    def next_tick(self, tick):
        return tick + max(0, self.closed - (tick + self.offset) % self.period)


@dataclass(frozen=True)
class Phase:
    name: str
    ticks: int
    claims: tuple[tuple[str, int], ...] = ()
    priority: int = 0
    dma_read: Read | None = None
    ready_window: ReadyWindow | None = None
    mid_tile: MidTile | None = None
    sram_access: Access | None = None
    activation: ActivationWindow | None = None

    @classmethod
    def from_spec(cls, name, ticks, spec):
        ready = ReadyWindow.from_spec(spec['ready_window']) if 'ready_window' in spec else None
        return cls(name, ticks, tuple(sorted(spec['claims'].items())), spec.get('priority', 0),
                   ready_window=ready)


@dataclass(frozen=True)
class Operation:
    phases: tuple[Phase, ...]
    after: frozenset[int] = frozenset()
    release: int = 0
    holds: tuple[tuple[str, int], ...] = ()
    phase_after: tuple[frozenset[tuple[int, int]], ...] = ()
    activation_after: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class Grant:
    operation: int
    phase: int
    start: int
    end: int
    dma_beats: tuple[BeatReceipt, ...] = ()
    sram_beats: tuple[tuple[int, int, int], ...] = ()


@dataclass(frozen=True)
class DeviceCheckpoint:
    """In-flight memory device state immediately before an arbitration edge."""

    tick: int
    fabric: ReadFabric | None
    starts: tuple[tuple[tuple[int, int], int], ...]
    feeders: dict[str, SramFeeder]


@dataclass(frozen=True)
class ReplayTrace:
    grants: tuple[tuple[Grant, ...], ...]
    checkpoints: tuple[DeviceCheckpoint, ...] = ()
    checkpoint_stride: int = 64


class ReplayDeadlock(ValueError):
    """Pending operations have no advancing event."""


def phase_dependencies(operations, index, phase):
    operation = operations[index]
    extra = operation.phase_after[phase] if operation.phase_after else frozenset()
    if phase:
        return extra | {(index, phase - 1)}
    return extra | {(parent, len(operations[parent].phases) - 1) for parent in operation.after}


def replay(operations, capacity, *, previous=(), issue_rates=None, dma_profile=None, sram_profiles=None):
    """Replay a plan, optionally reusing a fixed-service grant prefix."""
    return _replay(operations, capacity, ReplayTrace(previous), issue_rates, dma_profile, sram_profiles).grants


def replay_branch(operations, capacity, *, previous=None, issue_rates=None, dma_profile=None,
                  sram_profiles=None, save_checkpoints=True):
    """Extend a DP branch with a reusable trace and pre-edge memory snapshots."""
    return _replay(operations, capacity, previous or ReplayTrace(()), issue_rates, dma_profile, sram_profiles,
                   save_checkpoints=save_checkpoints)


def _replay(operations, capacity, previous, issue_rates, dma_profile, sram_profiles, *, save_checkpoints=False):
    """Lower priority numbers win among ready phases.

    At each tick, completions free resources before grants. A first grant
    acquires the operation's holds atomically, and the final completion
    releases them. A request can also become eligible when its external READY
    gate opens.
    """
    issue_rates = issue_rates or {}
    uses_dma = any(phase.dma_read is not None for operation in operations for phase in operation.phases)
    if uses_dma and dma_profile is None:
        raise ValueError('typed DMA phase requires a service profile')
    fabric = ReadFabric(dma_profile) if uses_dma else None
    sram_profiles = sram_profiles or {}
    sites = sorted({phase.sram_access.site for op in operations for phase in op.phases if phase.sram_access})
    if any(site not in sram_profiles for site in sites):
        raise ValueError('SRAM access requires a feeder profile')
    feeders = {site: SramFeeder(sram_profiles[site]) for site in sites}
    device_starts = {}
    activations = set()
    successors = {}
    dependencies = {}
    release = {}
    prerequisites = {}
    for index, operation in enumerate(operations):
        if (not operation.phases or type(operation.release) is not int or operation.release < 0
                or any(type(dep) is not int or not 0 <= dep < index for dep in operation.after)
                or operation.phase_after and len(operation.phase_after) != len(operation.phases)):
            raise ValueError('invalid replay operation or dependency')
        if operation.activation_after and (
                len(operation.activation_after) != P_COUNT or len(operation.phases) != 1
                or operation.phases[0].activation is None
                or any(parent not in prerequisites for parent in operation.activation_after)
                or any(resource in dict(operations[i].phases[j].claims)
                       or resource in dict(operations[i].holds)
                       for i, j in operation.activation_after
                       for resource, _ in operation.phases[0].claims)):
            raise ValueError('invalid FFN retirement dependencies')
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
                    or phase.dma_read is not None and not phase.dma_read.valid()
                    or phase.sram_access is not None and (
                        not phase.sram_access.valid() or phase.dma_read is not None or phase.mid_tile is not None)
                    or phase.ready_window is not None and (
                        not isinstance(phase.ready_window, ReadyWindow) or not phase.ready_window.valid())
                    or phase.mid_tile is not None and (
                        not isinstance(phase.mid_tile, MidTile) or not phase.mid_tile.valid()
                        or phase.dma_read is not None or dict(phase.claims) != phase.mid_tile.claims())
                    or phase.activation is not None and any(
                        device is not None for device in (phase.dma_read, phase.mid_tile, phase.sram_access))
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

    old_grants = previous.grants
    prefix_count = len(old_grants)
    if prefix_count >= len(operations) and old_grants:
        raise ValueError('replay requires an appended operation')
    # Until a new operation could first become ready, it cannot change a grant.
    # Later grants, including grants at the boundary tick, are speculative.
    first_phases = ((index, 0) for index in range(prefix_count, len(operations)))
    tick = min((max([release[key]] + [old_grants[p][j].end for p, j in prerequisites[key]])
                for key in first_phases if all(p < prefix_count for p, _ in prerequisites[key])), default=0)
    checkpoints = []
    stride = previous.checkpoint_stride
    has_live_activation = any(operation.activation_after for operation in operations)
    if uses_dma or feeders or has_live_activation:
        checkpoints = [checkpoint for checkpoint in previous.checkpoints if checkpoint.tick <= tick]
        tick = 0
        if checkpoints:
            checkpoint = checkpoints[-1]
            tick = checkpoint.tick
            if checkpoint.fabric is not None:
                fabric = deepcopy(checkpoint.fabric)
            feeders.update(deepcopy(checkpoint.feeders))
            device_starts = dict(checkpoint.starts)
            activations = {key for key in device_starts if operations[key[0]].activation_after}
    grants = [
        # An in-flight device grant's old end and receipts were speculative.
        [grant for grant in row if grant.start < tick and (index, grant.phase) not in device_starts]
        for index, row in enumerate(old_grants)
    ]
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
        accepted = [(grant.start, grant.operation, grant.phase) for prefix in grants for grant in prefix]
        accepted.extend((start, index, phase) for (index, phase), start in device_starts.items())
        cutoff = tick - max(window for window, _ in issue_rates.values())
        for start, index, phase in sorted(entry for entry in accepted if entry[0] > cutoff):
            record_issues(operations[index].phases[phase].claims, start)
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

    for index, phase in device_starts:
        operation = operations[index]
        occupied.update(dict(operation.phases[phase].claims))
        if phase == 0:
            occupied.update(dict(operation.holds))
    arrivals = []
    for key, parents in prerequisites.items():
        index, phase = key
        if key not in device_starts and phase >= len(grants[index]) and not dependencies[key]:
            ready = max([release[key]] + [completed[parent] for parent in parents])
            heappush(arrivals, (ready, index, phase))
    pending = []
    while finished < len(operations):
        if (save_checkpoints and (fabric is not None or feeders or has_live_activation)
                and tick >= (checkpoints[-1].tick if checkpoints else 0) + stride):
            if len(checkpoints) == 16:
                # Bound retained fabric copies while keeping earlier rollback points.
                checkpoints = checkpoints[1::2]
                stride *= 2
            checkpoints.append(DeviceCheckpoint(tick, deepcopy(fabric), tuple(device_starts.items()),
                                                deepcopy(feeders)))
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
        launches = []
        sram_launches = []
        next_open = []
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
            if phase.ready_window is not None:
                opens = phase.ready_window.next_tick(tick)
                if opens > tick:
                    next_open.append(opens)
                    waiting.append(request)
                    continue
            occupied.update(dict(claims))
            record_issues(phase.claims, tick)
            key = index, phase_index
            if operation.activation_after:
                device_starts[key] = tick
                activations.add(key)
                continue
            if phase.dma_read is None and phase.sram_access is None:
                if phase.activation is not None:
                    end = phase.activation.run(tick)[1] + 1
                else:
                    end = phase.mid_tile.end(tick) if phase.mid_tile is not None else tick + phase.ticks
                heappush(running, (end, index, phase_index))
                grants[index].append(Grant(index, phase_index, tick, end))
            else:
                device_starts[key] = tick
                if phase.sram_access is not None:
                    sram_launches.append((key, phase.sram_access))
                else:
                    launches.append((key, phase.dma_read))
        for key, read in sorted(launches):
            fabric.submit(key, read)
        if fabric is not None and fabric.active:
            for (index, phase_index), receipts in fabric.advance(tick):
                start = device_starts.pop((index, phase_index))
                # A sampled client response is visible to the next stage at
                # the following edge. The route still owes its own SRAM ACK.
                end = tick + 1
                grants[index].append(Grant(index, phase_index, start, end, receipts))
                heappush(running, (end, index, phase_index))
        for key, access in sorted(sram_launches):
            feeders[access.site].submit(key, access)
        for feeder in feeders.values():
            if feeder.active:
                for (index, phase_index), receipts in feeder.advance(tick):
                    start = device_starts.pop((index, phase_index))
                    end = tick + 1
                    grants[index].append(Grant(index, phase_index, start, end, sram_beats=receipts))
                    heappush(running, (end, index, phase_index))
        for key in sorted(activations):
            retirements = operations[key[0]].activation_after
            if any(j >= len(grants[i]) for i, j in retirements):
                continue
            # Only deterministic or already-confirmed end times are stored
            # in grants. If restoring at a boundary before a retirement,
            # leave this window live until those end times are known again.
            index, phase_index = key
            start = device_starts.pop(key)
            activation = operations[index].phases[phase_index].activation
            end = activation.run(start, tuple(grants[i][j].end for i, j in retirements))[1] + 1
            heappush(running, (end, index, phase_index))
            grants[index].append(Grant(index, phase_index, start, end))
            activations.remove(key)
        pending = waiting
        if finished == len(operations):
            break
        future = [queue[0][0] for queue in (running, arrivals) if queue] + next_open
        if fabric is not None and fabric.active:
            future.append(tick + 1)
        future.extend(feeder.next_edge(tick + 1) for feeder in feeders.values() if feeder.active)
        if pending:
            future.extend(history[0][0] for history in issues.values() if history)
        if not future:
            raise ReplayDeadlock(f'no replay progress at tick {tick}: {pending}')
        tick = min(future)
    return ReplayTrace(tuple(tuple(operation) for operation in grants), tuple(checkpoints), stride)
