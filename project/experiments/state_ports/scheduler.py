"""Deterministic cumulative-resource list scheduling and a small exact oracle.

All intervals are half-open [start, end). Resource demand is constant throughout
one atomic nonpreemptive task. This is an abstract service scheduler: static
buffers, data/scale correctness, addressing and real hardware cycles belong to
the caller's separately validated model. See LIMITATIONS.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import heapq
from typing import Any


POLICIES = ("critical", "fifo", "shortest", "longest")


@dataclass(frozen=True)
class _Task:
    id: str
    duration: int
    deps: tuple[int, ...]
    resources: tuple[tuple[str, int], ...]
    index: int


def _positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def _problem(tasks, capacities):
    if not isinstance(tasks, list):
        raise ValueError("tasks must be a list")
    if not isinstance(capacities, dict):
        raise ValueError("capacities must be a dict")
    caps = dict(capacities)
    for resource, capacity in caps.items():
        if not isinstance(resource, str) or not resource:
            raise ValueError("resource names must be nonempty strings")
        if not _positive_int(capacity):
            raise ValueError(f"capacity for {resource!r} must be a positive integer")
    ids = []
    for row in tasks:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
            raise ValueError("each task must have a nonempty string id")
        ids.append(row["id"])
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate task ids")
    indices = {name: i for i, name in enumerate(ids)}
    normalized = []
    for i, row in enumerate(tasks):
        if not _positive_int(row.get("duration")):
            raise ValueError(f"duration for {ids[i]!r} must be a positive integer")
        deps = row.get("deps")
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
            raise ValueError(f"deps for {ids[i]!r} must be a list of ids")
        if len(deps) != len(set(deps)):
            raise ValueError(f"duplicate dependencies for {ids[i]!r}")
        if any(d not in indices for d in deps):
            raise ValueError(f"unknown dependency for {ids[i]!r}")
        if ids[i] in deps:
            raise ValueError(f"self dependency for {ids[i]!r}")
        resources = row.get("resources")
        if not isinstance(resources, dict):
            raise ValueError(f"resources for {ids[i]!r} must be a dict")
        for name, demand in resources.items():
            if name not in caps:
                raise ValueError(f"unknown resource {name!r} for {ids[i]!r}")
            if not _positive_int(demand) or demand > caps[name]:
                raise ValueError(f"demand for {name!r} in {ids[i]!r} must be positive and <= capacity")
        normalized.append(_Task(ids[i], row["duration"], tuple(indices[d] for d in deps),
                                tuple(sorted(resources.items())), i))
    successors = [[] for _ in normalized]
    indegree = [len(task.deps) for task in normalized]
    for task in normalized:
        for dep in task.deps:
            successors[dep].append(task.index)
    ready = [i for i, degree in enumerate(indegree) if degree == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        i = heapq.heappop(ready)
        order.append(i)
        for child in successors[i]:
            indegree[child] -= 1
            if indegree[child] == 0:
                heapq.heappush(ready, child)
    if len(order) != len(normalized):
        raise ValueError("dependency cycle")
    remaining = [0] * len(normalized)
    for i in reversed(order):
        remaining[i] = normalized[i].duration + max((remaining[j] for j in successors[i]), default=0)
    return normalized, caps, remaining


def _bounds(tasks, caps, remaining):
    work = {name: sum(task.duration * dict(task.resources).get(name, 0) for task in tasks)
            for name in caps}
    resource_bound = max(((work[name] + cap - 1) // cap for name, cap in caps.items()), default=0)
    return {"critical_path": max(remaining, default=0), "resource_workload": resource_bound,
            "lower_bound": max(max(remaining, default=0), resource_bound)}


def schedule(tasks, capacities, policy="critical"):
    """Return a feasible deterministic greedy list schedule, without optimality claims.

    critical: largest duration-weighted remaining path; shortest/longest: task
    duration; fifo: earliest time all predecessors completed. Ties use original
    input order. At an event the policy scans all ready tasks, allowing a later
    ready task to fit when an earlier task is blocked by a different resource.
    No deliberate idling is used by these four heuristics.
    """
    if policy not in POLICIES:
        raise ValueError(f"policy must be one of {POLICIES}")
    nodes, caps, remaining = _problem(tasks, capacities)
    available = dict(caps)
    done = set()
    successors = [[] for _ in nodes]
    waiting = [len(task.deps) for task in nodes]
    for task in nodes:
        for dep in task.deps:
            successors[dep].append(task.index)
    ready = {task.index for task in nodes if waiting[task.index] == 0}
    ready_since = {i: 0 for i in ready}
    running = []
    events = []
    now = 0
    while len(done) < len(nodes):
        while running and running[0][0] == now:
            _, i = heapq.heappop(running)
            done.add(i)
            for resource, demand in nodes[i].resources:
                available[resource] += demand
            for child in successors[i]:
                waiting[child] -= 1
                if waiting[child] == 0:
                    ready.add(child)
                    ready_since[child] = now
        if policy == "critical":
            key = lambda i: (-remaining[i], i)
        elif policy == "shortest":
            key = lambda i: (nodes[i].duration, i)
        elif policy == "longest":
            key = lambda i: (-nodes[i].duration, i)
        else:
            key = lambda i: (ready_since[i], i)
        for i in sorted(ready, key=key):
            task = nodes[i]
            if all(available[r] >= demand for r, demand in task.resources):
                ready.remove(i)
                for resource, demand in task.resources:
                    available[resource] -= demand
                end = now + task.duration
                heapq.heappush(running, (end, i))
                events.append({"id": task.id, "start": now, "end": end})
        if running:
            now = running[0][0]
        elif len(done) < len(nodes):
            raise RuntimeError("validated DAG unexpectedly cannot make progress")
    indices = {task.id: task.index for task in nodes}
    events.sort(key=lambda event: (event["start"], indices[event["id"]]))
    return {"policy": policy, "makespan": max((e["end"] for e in events), default=0),
            "events": events, "proven_optimal": False, "bounds": _bounds(nodes, caps, remaining)}


def validate_schedule(tasks, capacities, result):
    """Independently validate event spans, precedences and a resource boundary sweep.

    This does not call the scheduling algorithm or use its resource availability
    state. Invalid problems and invalid results return valid=False with errors.
    The function never repairs/reorders supplied events or trusts reported peaks.
    """
    try:
        nodes, caps, _ = _problem(tasks, capacities)
    except ValueError as exc:
        return {"valid": False, "errors": ["invalid problem: " + str(exc)],
                "makespan": None, "resource_peaks": {}}
    errors = []
    lookup = {task.id: task for task in nodes}
    spans = {}
    boundaries = []
    if not isinstance(result, dict) or not isinstance(result.get("events"), list):
        return {"valid": False, "errors": ["result must contain an events list"],
                "makespan": None, "resource_peaks": {name: 0 for name in caps}}
    for row in result["events"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            errors.append("event must have a string id")
            continue
        name = row["id"]
        if name not in lookup:
            errors.append(f"unknown event id {name!r}")
            continue
        if name in spans:
            errors.append(f"duplicate event id {name!r}")
            continue
        start, end = row.get("start"), row.get("end")
        if type(start) is not int or type(end) is not int or start < 0 or end <= start:
            errors.append(f"invalid integer interval for {name!r}")
            continue
        spans[name] = (start, end)
        if end - start != lookup[name].duration:
            errors.append(f"duration mismatch for {name!r}")
        for resource, demand in lookup[name].resources:
            boundaries.append((start, 1, resource, demand))
            boundaries.append((end, 0, resource, -demand))
    for name, task in lookup.items():
        if name not in spans:
            errors.append(f"missing event {name!r}")
            continue
        for dep in task.deps:
            dep_name = nodes[dep].id
            if dep_name in spans and spans[dep_name][1] > spans[name][0]:
                errors.append(f"dependency violation {dep_name!r} -> {name!r}")
    usage = {name: 0 for name in caps}
    peaks = dict(usage)
    for time, _, resource, delta in sorted(boundaries):
        usage[resource] += delta
        peaks[resource] = max(peaks[resource], usage[resource])
        if usage[resource] > caps[resource]:
            errors.append(f"resource {resource!r} exceeds capacity at time {time}")
        if usage[resource] < 0:
            errors.append(f"resource {resource!r} has negative usage at time {time}")
    makespan = max((end for _, end in spans.values()), default=0)
    if type(result.get("makespan")) is not int or result["makespan"] != makespan:
        errors.append("reported makespan mismatch")
    return {"valid": not errors, "errors": errors, "makespan": makespan, "resource_peaks": peaks}


def exact_schedule(tasks, capacities, max_tasks=9, max_states=250_000):
    """Find the exact minimum makespan for <=9 tasks using exhaustive event DP.

    Every feasible subset of currently ready tasks is considered, including
    nonmaximal subsets and deliberate idling until a running task completes.
    It therefore does NOT assume non-delay schedules are optimal. The event-time
    restriction is exact only under the model documented in LIMITATIONS.md.
    A state guard raises rather than returning an unproven optimum.
    """
    nodes, caps, remaining = _problem(tasks, capacities)
    if not _positive_int(max_tasks) or max_tasks > 9 or len(nodes) > max_tasks:
        raise ValueError("exact oracle requires at most max_tasks <= 9 tasks")
    if not _positive_int(max_states):
        raise ValueError("max_states must be a positive integer")
    n = len(nodes)
    all_done = (1 << n) - 1
    dep_masks = [sum(1 << dep for dep in task.deps) for task in nodes]
    choices = {}
    counters = {"states": 0, "transitions": 0, "deliberate_idle_transitions": 0}

    @lru_cache(maxsize=None)
    def solve(done, running):
        counters["states"] += 1
        if counters["states"] > max_states:
            raise RuntimeError("exact oracle state budget exhausted; no optimality result returned")
        if done == all_done:
            return 0
        active = {i for i, _ in running}
        available = dict(caps)
        for i in active:
            for resource, demand in nodes[i].resources:
                available[resource] -= demand
        ready = [i for i in range(n) if not done & (1 << i) and i not in active
                 and dep_masks[i] & done == dep_masks[i]]
        subsets = []

        def enumerate_subsets(position, selected, free):
            if position == len(ready):
                if selected or running:
                    subsets.append(tuple(selected))
                return
            i = ready[position]
            enumerate_subsets(position + 1, selected, free)
            if all(free[r] >= demand for r, demand in nodes[i].resources):
                after = dict(free)
                for resource, demand in nodes[i].resources:
                    after[resource] -= demand
                enumerate_subsets(position + 1, selected + [i], after)

        enumerate_subsets(0, [], available)
        subsets.sort(key=lambda subset: (-len(subset), subset))
        best = None
        best_choice = None
        for subset in subsets:
            progressing = list(running) + [(i, nodes[i].duration) for i in subset]
            delta = min(duration for _, duration in progressing)
            next_done = done
            next_running = []
            for i, duration in progressing:
                if duration == delta:
                    next_done |= 1 << i
                else:
                    next_running.append((i, duration - delta))
            next_running = tuple(sorted(next_running))
            counters["transitions"] += 1
            if not subset:
                counters["deliberate_idle_transitions"] += 1
            value = delta + solve(next_done, next_running)
            if best is None or value < best:
                best = value
                best_choice = (subset, delta, next_done, next_running)
        if best_choice is None:
            raise RuntimeError("validated oracle state unexpectedly cannot progress")
        choices[(done, running)] = best_choice
        return best

    optimum = solve(0, ())
    done, running, now = 0, (), 0
    events = []
    while done != all_done:
        subset, delta, next_done, next_running = choices[(done, running)]
        for i in subset:
            events.append({"id": nodes[i].id, "start": now, "end": now + nodes[i].duration})
        now += delta
        done, running = next_done, next_running
    indices = {task.id: task.index for task in nodes}
    events.sort(key=lambda e: (e["start"], indices[e["id"]]))
    return {"policy": "exact_event_dp", "makespan": optimum, "events": events,
            "proven_optimal": True, "bounds": _bounds(nodes, caps, remaining),
            "search": counters, "max_tasks": max_tasks, "max_states": max_states}
