"""Bounded search over legal serial task orders and compute placements.

Objective: charged packet wire bytes, not uncalibrated hardware latency.
Fixed policy: pin all operands/output/workspace, clean LRU eviction, durable
write-through outputs, serialized shared external TX, stop-and-wait packets.
All algorithms use the identical transition/policy and resource inventory.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import time

from .resource_bridge import load_upstream


@lru_cache(maxsize=1)
def _packet_api():
    mod, profile, _ = load_upstream()
    return mod, profile


@lru_cache(maxsize=8192)
def wire(size):
    """Actual #48 implementation; alignment is NOT link bytes per cycle."""
    mod, profile = _packet_api()
    # Upstream packet fields are used directly; no second cost formula.
    return mod.packet(size, profile)["wire_bytes"]


@dataclass(frozen=True)
class Hardware:
    capacity: int = 524288
    matrices: int = 2
    vector_capacity: int = 524288
    control_bytes: int = 32
    fifo_bytes: int = 2048

    def __post_init__(self):
        if any(type(x) is not int or x <= 0 for x in
               (self.capacity,self.matrices,self.vector_capacity,self.control_bytes,self.fifo_bytes)):
            raise ValueError("positive exact integer hardware fields required")
        if self.fifo_bytes < 2048:
            raise ValueError("profile requires a 2048B packet FIFO, separate from RAM")

    def resources(self, task):
        return tuple(f"M{i}" for i in range(self.matrices)) if task.pool=="matrix" else ("V0",)

    def cap(self, resource):
        return self.vector_capacity if resource=="V0" else self.capacity

    @property
    def names(self):
        return tuple(f"M{i}" for i in range(self.matrices))+("V0",)


@dataclass
class State:
    done: int
    ready: frozenset
    caches: dict
    cost: int = 0


class Infeasible(ValueError):
    pass


def initial(workload, hardware):
    return State(0, frozenset(i for i,d in enumerate(workload.deps) if not d),
                 {r: () for r in hardware.names})


def advance(w, h, state, task_index, resource, detailed=False):
    if task_index not in state.ready or resource not in h.resources(w.tasks[task_index]):
        raise Infeasible("dependency/capability violation")
    task = w.tasks[task_index]
    required = set(task.reads)
    footprint = sum(w.values[v].size for v in task.reads)+w.values[task.output].size+task.workspace+h.control_bytes
    if footprint > h.cap(resource):
        raise Infeasible(f"working set {footprint} exceeds {resource} capacity {h.cap(resource)}")
    cache = list(state.caches[resource])
    misses = [v for v in task.reads if v not in cache]
    used = sum(w.values[v].size for v in cache)
    extra = sum(w.values[v].size for v in misses)+w.values[task.output].size+task.workspace+h.control_bytes
    evicted = []
    for v in list(cache):
        if used+extra <= h.cap(resource):
            break
        if v not in required:
            cache.remove(v)
            used -= w.values[v].size
            evicted.append(v)
    if used+extra > h.cap(resource):
        raise Infeasible("cannot reserve pinned working set")
    peak = used+extra
    for v in task.reads:
        if v in cache:
            cache.remove(v)
        cache.append(v)
    cache.append(task.output)
    cost = sum(wire(w.values[v].size) for v in misses)+wire(w.values[task.output].size)
    done = state.done | (1 << task_index)
    dead = [v for v in cache if not (w.user_masks[v] & ~done)]
    cache = [v for v in cache if v not in dead]
    ready = set(state.ready)
    ready.remove(task_index)
    for nxt in w.successors[task_index]:
        if w.deps[nxt] & done == w.deps[nxt]:
            ready.add(nxt)
    caches = dict(state.caches)
    caches[resource] = tuple(cache)
    result = State(done, frozenset(ready), caches, state.cost+cost)
    if not detailed:
        return result
    return result, dict(task=task_index, resource=resource, loads=misses,
                       evictions=evicted, dead=dead, peak_bytes=peak, wire_bytes=cost)


def actions(w, h, s, frontier=12):
    """Bounded deterministic shortlist: first ready tasks + resident-data users.

    All methods called greedy/beam use the same shortlist size. Exhaustive mode
    disables the bound. This is not a proof of global optimality.
    """
    if frontier is None:
        pool = set(s.ready)
    else:
        pool = set(sorted(s.ready)[:frontier])
        # Expose cross-row reuse beyond the row-major prefix.
        for cache in s.caches.values():
            for value in cache:
                users = [i for i in w.users[value] if i in s.ready]
                pool.update(users[:2])
    result = []
    for i in sorted(pool):
        for resource in h.resources(w.tasks[i]):
            try:
                child = advance(w,h,s,i,resource)
                result.append((child.cost-s.cost,i,resource,child))
            except Infeasible:
                pass
    return sorted(result,key=lambda a:(a[0],a[1],a[2]))


def choose_beam(w,h,s,width=4,depth=3,frontier=12,initial_bound=True):
    nodes = [(s, ())]
    expanded = 0
    for _ in range(depth):
        candidates = []
        for node,path in nodes:
            if not node.ready:
                candidates.append((node,path))
            else:
                for _,i,r,child in actions(w,h,node,frontier):
                    candidates.append((child,path+((i,r),)))
                    expanded += 1
        if not candidates:
            raise Infeasible("no capacity-feasible action")
        # Compare equal-depth prefixes; total remaining compulsory output bytes
        # differ across selected tasks, so include that admissible lower bound.
        score_cache={}
        initials=[(v.id,wire(v.size)) for v in w.values.values() if v.producer<0]
        def score(item):
            node,path=item
            if id(node) in score_cache:
                return score_cache[id(node)]
            removed=sum(wire(w.values[w.tasks[i].output].size) for i,_ in path)
            held=set(v for cache in node.caches.values() for v in cache)
            # At least one external load is still necessary for every initial
            # value with a remaining reader and no resident copy anywhere.
            # It deliberately ignores subsequent eviction and pool location.
            remaining=sum(size for v,size in initials if w.user_masks[v]&~node.done and v not in held) if initial_bound else 0
            score_cache[id(node)]=(node.cost-removed+remaining,path)
            return score_cache[id(node)]
        unique = {}
        for node,path in sorted(candidates,key=score):
            key=(node.done, tuple(node.caches.items()))
            if key not in unique:
                unique[key]=(node,path)
            if len(unique)>=width:
                break
        nodes=list(unique.values())
    return min(nodes,key=score)[1][0],expanded


def solve(w,h,method="greedy",width=4,depth=3,frontier=12,initial_bound=True):
    if method not in ("fixed","greedy","beam"):
        raise ValueError("unknown search method")
    if any(type(x) is not int or x<1 for x in (width,depth,frontier)):
        raise ValueError("positive search budget required")
    start=time.perf_counter()
    s=initial(w,h)
    plan=[]
    expanded=0
    while s.ready:
        if method=="fixed":
            i=min(s.ready)
            resource=h.resources(w.tasks[i])[0]
        elif method=="greedy":
            options=actions(w,h,s,frontier)
            if not options:
                raise Infeasible("no feasible action")
            _,i,resource,_=options[0]
            expanded+=len(options)
        else:
            (i,resource),count=choose_beam(w,h,s,width,depth,frontier,initial_bound)
            expanded+=count
        s,record=advance(w,h,s,i,resource,True)
        plan.append(record)
    if s.done.bit_count()!=len(w.tasks):
        raise Infeasible("incomplete/cyclic graph")
    return dict(method=method,wire_bytes=s.cost,plan=plan,
                expanded=expanded,algorithm_seconds=time.perf_counter()-start,
                search_budget=dict(width=width,depth=depth,frontier=frontier,initial_bound=initial_bound))


def exact(w,h):
    """Exhaustive optimum for tiny instances ONLY; independent of beam scoring."""
    if len(w.tasks)>8:
        raise ValueError("exact audit limited to eight tasks")
    def walk(s):
        if not s.ready:
            return s.cost
        return min(walk(child) for _,_,_,child in actions(w,h,s,None))
    return walk(initial(w,h))
