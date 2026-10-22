"""Audit-sized nonpreemptive event scheduler and independent integer-time oracle.

Hypothetical task durations only. This is not an accelerator calibration. Ports,
links, HBM and engines are explicit unit-capacity resource names. Buffer lifetimes
cover allocation before producer start through completion of the last reader.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class Task:
    name: str
    duration: int
    resources: tuple[str, ...]
    deps: tuple[str, ...] = ()
    priority: int = 0


@dataclass(frozen=True)
class Buffer:
    name: str
    size: int
    storage: str
    producer: str | None
    consumers: tuple[str, ...]
    retain: bool = False


def _validate(tasks, buffers, capacities):
    names = {task.name for task in tasks}
    if len(names) != len(tasks) or any(not task.name for task in tasks):
        raise ValueError("duplicate/empty task name")
    if any(isinstance(t.duration, bool) or not isinstance(t.duration, int) or t.duration <= 0
           or len(set(t.resources)) != len(t.resources) or any(not r for r in t.resources)
           or len(set(t.deps)) != len(t.deps) or not set(t.deps) <= names for t in tasks):
        raise ValueError("invalid duration/resource/dependency")
    done = set()
    while len(done) != len(names):
        extra = {t.name for t in tasks if t.name not in done and set(t.deps) <= done}
        if not extra:
            raise ValueError("dependency cycle")
        done |= extra
    if len({b.name for b in buffers}) != len(buffers):
        raise ValueError("duplicate buffer")
    by_name = {t.name: t for t in tasks}
    for b in buffers:
        if (isinstance(b.size, bool) or not isinstance(b.size, int) or b.size <= 0
                or b.storage not in capacities or b.producer is not None and b.producer not in names
                or not set(b.consumers) <= names):
            raise ValueError("invalid buffer")
        # Explicit producer->reader edges make buffer version readiness auditable.
        if b.producer is not None and any(b.producer not in by_name[c].deps for c in b.consumers):
            raise ValueError("buffer consumers require direct producer dependencies")
    if any(isinstance(c, bool) or not isinstance(c, int) or c <= 0 for c in capacities.values()):
        raise ValueError("invalid storage capacity")


def _live_bytes(buffers, started, completed, capacities):
    live = {storage: 0 for storage in capacities}
    for b in buffers:
        born = b.producer is None or b.producer in started
        finished = (b.producer is None or b.producer in completed) and set(b.consumers) <= completed
        if born and (b.retain or not finished):
            live[b.storage] += b.size
    return live


def event_schedule(tasks, buffers=(), capacities=None):
    """Greedy atomic admission; a deadlock is scheduler failure, not infeasibility."""
    capacities = capacities or {}
    _validate(tasks, buffers, capacities)
    started, completed, running, records = set(), set(), {}, []
    now = 0
    peak = {name: 0 for name in capacities}
    while len(completed) != len(tasks):
        for name, end in list(running.items()):
            if end == now:
                completed.add(name)
                del running[name]
        occupied = {r for t in tasks if t.name in running for r in t.resources}
        for task in sorted(tasks, key=lambda t: (t.priority, t.name)):
            if task.name in started or not set(task.deps) <= completed or occupied.intersection(task.resources):
                continue
            prospective = _live_bytes(buffers, started | {task.name}, completed, capacities)
            if any(prospective[name] > capacities[name] for name in capacities):
                continue
            started.add(task.name)
            running[task.name] = now + task.duration
            occupied.update(task.resources)
            records.append({"task": task.name, "start": now, "end": now + task.duration})
            for storage in peak:
                peak[storage] = max(peak[storage], prospective[storage])
        if len(completed) == len(tasks):
            break
        if not running:
            return {"status": "scheduler_deadlock", "makespan": None, "events": records, "peak_bytes": peak}
        now = min(running.values())
    return {"status": "ok", "makespan": now, "events": records, "peak_bytes": peak}


def exact_cycles(tasks, buffers=(), capacities=None, max_tasks=8):
    """Independent BFS over every integer-cycle start subset, allowing idling.

    A state omits absolute time because service/dependencies are time invariant;
    BFS first arrival dominates later arrivals of the same state. Tiny only.
    """
    capacities = capacities or {}
    _validate(tasks, buffers, capacities)
    if len(tasks) > max_tasks:
        raise ValueError("tiny oracle task limit exceeded")
    count = len(tasks)
    index = {task.name: i for i, task in enumerate(tasks)}
    prerequisite = [sum(1 << index[d] for d in task.deps) for task in tasks]
    resource_sets = [set(task.resources) for task in tasks]
    all_done = (1 << count) - 1
    initial = (0, (0,) * count)
    queue, seen = deque([(initial, 0)]), {initial}
    while queue:
        (done, remaining), time = queue.popleft()
        if done == all_done:
            return time
        active = {i for i in range(count) if remaining[i]}
        used = set().union(*(resource_sets[i] for i in active)) if active else set()
        ready = [i for i in range(count) if not done & (1 << i) and i not in active
                 and prerequisite[i] & done == prerequisite[i] and not resource_sets[i] & used]
        for size in range(len(ready) + 1):
            for selected in combinations(ready, size):
                if not selected and not active:
                    continue
                taken = set(used)
                admitted = True
                for i in selected:
                    if resource_sets[i] & taken:
                        admitted = False
                        break
                    taken |= resource_sets[i]
                if not admitted:
                    continue
                # Independent lifetime evaluation from bit masks, not the event
                # engine's helper, and includes all outputs allocated this cycle.
                started_indices = active | set(selected) | {i for i in range(count) if done & (1 << i)}
                memory = {name: 0 for name in capacities}
                for b in buffers:
                    born = b.producer is None or index[b.producer] in started_indices
                    producer_done = b.producer is None or bool(done & (1 << index[b.producer]))
                    readers_done = all(done & (1 << index[c]) for c in b.consumers)
                    if born and (b.retain or not (producer_done and readers_done)):
                        memory[b.storage] += b.size
                if any(memory[name] > capacities[name] for name in capacities):
                    continue
                next_remaining = list(remaining)
                for i in selected:
                    next_remaining[i] = tasks[i].duration
                next_done = done
                for i, duration in enumerate(next_remaining):
                    if duration:
                        next_remaining[i] -= 1
                        if not next_remaining[i]:
                            next_done |= 1 << i
                state = (next_done, tuple(next_remaining))
                if state not in seen:
                    seen.add(state)
                    queue.append((state, time + 1))
    return None


def validate_schedule(tasks, schedule, buffers=(), capacities=None):
    """Independent interval audit; raises on incomplete/illegal execution."""
    capacities = capacities or {}
    events = schedule["events"]
    mapping = {event["task"]: event for event in events}
    if len(mapping) != len(events) or set(mapping) != {t.name for t in tasks}:
        raise ValueError("incomplete or duplicate task schedule")
    for task in tasks:
        event = mapping[task.name]
        if event["start"] < 0 or event["end"] - event["start"] != task.duration:
            raise ValueError("invalid task duration")
        if any(mapping[d]["end"] > event["start"] for d in task.deps):
            raise ValueError("dependency violation")
    for left, right in combinations(tasks, 2):
        a, b = mapping[left.name], mapping[right.name]
        if set(left.resources) & set(right.resources) and max(a["start"], b["start"]) < min(a["end"], b["end"]):
            raise ValueError("resource overlap")
    intervals = []
    for b in buffers:
        birth = 0 if b.producer is None else mapping[b.producer]["start"]
        death = max([mapping[c]["end"] for c in b.consumers]
                    + ([mapping[b.producer]["end"]] if b.producer is not None else [0]))
        if b.retain:
            death = max(event["end"] for event in events) + 1
        intervals.append((b, birth, death))
    for time in {0} | {e[k] for e in events for k in ("start", "end")}:
        for storage, capacity in capacities.items():
            live = sum(b.size for b, start, end in intervals if b.storage == storage and start <= time < end)
            if live > capacity:
                raise ValueError("live-buffer capacity exceeded")
    return True


def fixtures():
    # Equal 8 cycles of port service, same M/V compute: placement alone changes
    # shared-port serialization. Both banks/ports exist in both fixtures.
    result = {}
    for placement, port in (("colocated", "B0.RW"), ("separated", "B1.RW")):
        result[placement] = ([Task("loadA", 4, ("B0.RW",)), Task("loadB", 4, (port,)),
                              Task("mat", 6, ("M",), ("loadA",)), Task("vec", 6, ("V",), ("loadB",))], (), {})
    # Greedy starts low-value long P transfer at t0, preventing a critical task
    # released at t1. Exact may idle P until t1; a scheduler gain is not wiring.
    result["greedy_counterexample"] = ([Task("a_long", 5, ("P",)), Task("b_release", 1, ("R",)),
                                        Task("c_critical", 1, ("P",), ("b_release",)),
                                        Task("d_tail", 10, ("M",), ("c_critical",))], (), {})
    # A supposedly free DMA must reserve both endpoint ports as well as link.
    result["dma_two_ends"] = ([Task("copy", 3, ("B0.RW", "B1.RW", "L")),
                                Task("other", 3, ("B1.RW",))], (), {})
    # Simultaneous temporary outputs cannot each borrow the whole same bank.
    cap_tasks = [Task("a_make", 1, ("A",)), Task("b_make", 1, ("B",)),
                 Task("c_consume", 1, ("C",), ("a_make", "b_make"))]
    cap_buffers = [Buffer("a", 4, "SRAM", "a_make", ("c_consume",)),
                   Buffer("b", 4, "SRAM", "b_make", ("c_consume",))]
    result["capacity_exact_fit"] = (cap_tasks, cap_buffers, {"SRAM": 8})
    result["capacity_impossible"] = (cap_tasks, cap_buffers, {"SRAM": 7})
    return result


if __name__ == "__main__":
    import json
    output = {}
    for name, (tasks, buffers, capacities) in fixtures().items():
        event = event_schedule(tasks, buffers, capacities)
        optimal = exact_cycles(tasks, buffers, capacities)
        if event["status"] == "ok":
            validate_schedule(tasks, event, buffers, capacities)
        output[name] = {"event": event, "exact_minimum_cycles": optimal}
    print(json.dumps(output, indent=2))
