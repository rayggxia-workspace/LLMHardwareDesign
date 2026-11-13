"""Predict cycles from ordered per-Block instructions and explicit service rules."""

from collections import Counter, deque
from dataclasses import dataclass
import heapq


@dataclass(frozen=True)
class Operation:
    identifier: str
    service: str
    after: tuple = ()


@dataclass(frozen=True)
class Service:
    resource: str
    latency: int
    interval: int
    receiver: str = ""


@dataclass(frozen=True)
class Resource:
    clients: tuple  # Block names in the RTL arbitration order
    slots: int     # In-flight reservations, including work waiting for ACK
    arbitration: str = "round_robin"


@dataclass(frozen=True)
class Receiver:
    depth: int
    latency: int   # Registered service time from enqueue to visible ACK
    ports: tuple   # Resource names in priority order for simultaneous results


@dataclass(frozen=True)
class DmaBinding:
    port: object
    requests: dict  # Operation ID to Transfer or Fence
    priority: tuple  # Physical resource order for same-edge offers
    max_cycles: int = 100_000


def _positive_int(value):
    return type(value) is int and value >= 1


def simulate(programs, services, resources, receivers, dma=None):
    """Return the events of the single-clock, registered protocol in README.md."""
    operations = [op for stream in programs.values() for op in stream]
    names = {op.identifier for op in operations}
    if len(names) != len(operations) or "" in names:
        raise ValueError("operation identifiers must be unique and nonempty")
    for name, resource in resources.items():
        if (not _positive_int(resource.slots) or resource.arbitration not in ("round_robin", "fixed")
                or not resource.clients or len(set(resource.clients)) != len(resource.clients)
                or any(client not in programs for client in resource.clients)):
            raise ValueError("invalid resource: " + name)
    for name, receiver in receivers.items():
        if (not _positive_int(receiver.depth) or not _positive_int(receiver.latency) or not receiver.ports
                or len(set(receiver.ports)) != len(receiver.ports) or not set(receiver.ports) <= resources.keys()):
            raise ValueError("invalid receiver: " + name)
    dma_priority = {}
    if dma is not None:
        if (not dma.requests or not dma.requests.keys() <= names or not dma.port.drained
                or dma.port.last_cycle != -1 or len(dma.priority) != len(set(dma.priority))
                or not _positive_int(dma.max_cycles)):
            raise ValueError("invalid DMA binding or initial state")
        dma_priority = {name: i for i, name in enumerate(dma.priority)}
        if len({request.tag for request in dma.requests.values()}) != len(dma.requests):
            raise ValueError("DMA tags must be unique across bound operations")
    for block, stream in programs.items():
        for op in stream:
            rule = services.get(op.service)
            if (rule is None or rule.resource not in resources
                    or not _positive_int(rule.latency) or not _positive_int(rule.interval)
                    or block not in resources[rule.resource].clients
                    or rule.receiver and (rule.receiver not in receivers
                                          or rule.resource not in receivers[rule.receiver].ports)):
                raise ValueError("missing or invalid service for {}:{}".format(block, op.identifier))
            if not set(op.after) <= names or op.identifier in op.after:
                raise ValueError("invalid dependency for " + op.identifier)
            if dma is not None and op.identifier in dma.requests and (rule.receiver or rule.resource not in dma_priority):
                raise ValueError("DMA operation requires an explicit resource priority and no local receiver: " + op.identifier)

    pc = dict.fromkeys(programs, 0)
    pointers = dict.fromkeys(resources, 0)
    free = {name: resource.slots for name, resource in resources.items()}
    next_issue = dict.fromkeys(resources, 0)
    waiting = {name: deque() for name in receivers}
    port_priority = {name: {port: priority for priority, port in enumerate(receiver.ports)}
                     for name, receiver in receivers.items()}
    occupied = dict.fromkeys(receivers, 0)
    done = set()
    scheduled = []
    events = []
    cycle = 0
    serial = 0
    dma_order = {block: deque() for block in programs}
    dma_ready = {}
    dma_held = None
    dma_inflight = {}
    dma_responses = {}

    def emit(kind, op, block, resource):
        events.append({"cycle": cycle, "event": kind, "op": op, "block": block, "resource": resource})

    def completion_priority(event):
        resource, receiver = event[5:]
        if dma is not None and event[3] in dma.requests:
            return dma_priority[resource], event[1]
        return port_priority.get(receiver, {}).get(resource, 0), event[1]

    while len(done) < len(operations):
        if dma is not None and cycle > dma.max_cycles:
            raise ValueError("DMA-coupled simulation did not finish by cycle {}".format(dma.max_cycles))
        finished = []
        while scheduled and scheduled[0][0] == cycle:
            finished.append(heapq.heappop(scheduled))

        retired_dma = None
        if dma is not None and dma_held is None:
            heads = [queue[0] for queue in dma_order.values() if queue and queue[0] in dma_ready]
            if heads:
                dma_held = min(heads, key=lambda op: dma_ready[op][0])
        if dma is not None and (dma_held is not None or not dma.port.drained):
            offered = dma.requests[dma_held] if dma_held is not None else None
            start_event = len(dma.port.events)
            accepted, retired_dma = dma.port.step(cycle, offered)
            events.extend(dma.port.events[start_event:])
            if accepted:
                _, block, resource = dma_ready.pop(dma_held)
                dma_inflight[offered.tag] = (dma_order[block].popleft(), block, resource)
                dma_held = None

        # Sample each queue's old occupancy. A pop cannot provide same-edge credit.
        for name, pending in waiting.items():
            receiver = receivers[name]
            if pending and occupied[name] < receiver.depth:
                op, block, resource = pending.popleft()
                occupied[name] += 1
                heapq.heappush(scheduled, (cycle + receiver.latency, serial, "ack", op, block, resource, name))
                serial += 1
                emit("enqueue", op, block, name)

        contenders = {}
        for block, stream in programs.items():
            if pc[block] == len(stream):
                continue
            op = stream[pc[block]]
            if all(dep in done for dep in op.after):
                contenders.setdefault(services[op.service].resource, {})[block] = op

        for name, eligible in contenders.items():
            if not free[name] or cycle < next_issue[name]:
                continue
            resource = resources[name]
            start = pointers[name] if resource.arbitration == "round_robin" else 0
            for offset in range(len(resource.clients)):
                index = (start + offset) % len(resource.clients)
                block = resource.clients[index]
                if block in eligible:
                    break
            op = eligible[block]
            rule = services[op.service]
            pointers[name] = (index + 1) % len(resource.clients)
            next_issue[name] = cycle + rule.interval
            free[name] -= 1
            pc[block] += 1
            if dma is not None and op.identifier in dma.requests:
                dma_order[block].append(op.identifier)
            heapq.heappush(scheduled, (cycle + rule.latency, serial, "service", op.identifier, block, name, rule.receiver))
            serial += 1
            emit("issue", op.identifier, block, name)

        # Existing queue entries precede arrivals from this edge. Simultaneous
        # arrivals use physical port priority, then launch order on that port.
        for _, sequence, kind, op, block, resource, receiver in sorted(finished, key=completion_priority):
            if kind == "service":
                emit("service_done", op, block, resource)
                if dma is not None and op in dma.requests:
                    dma_ready[op] = ((cycle, dma_priority[resource], sequence), block, resource)
                    continue
                if receiver:
                    waiting[receiver].append((op, block, resource))
                    continue
            else:
                occupied[receiver] -= 1
                emit("ack", op, block, receiver)
            emit("complete", op, block, resource)
            done.add(op)
            free[resource] += 1

        if retired_dma is not None:
            op, block, resource = dma_inflight.pop(retired_dma.tag)
            dma_responses[op] = retired_dma.data
            emit("complete", op, block, resource)
            done.add(op)
            free[resource] += 1

        if len(done) == len(operations):
            break
        # One edge exposes the state changes above. Then jump over idle edges.
        following = [scheduled[0][0]] if scheduled else []
        if dma is not None and (dma_held is not None or not dma.port.drained
                                or any(queue and queue[0] in dma_ready for queue in dma_order.values())):
            following.append(cycle + 1)
        if any(queue and occupied[name] < receivers[name].depth for name, queue in waiting.items()):
            following.append(cycle + 1)
        for block, stream in programs.items():
            if pc[block] < len(stream):
                op = stream[pc[block]]
                name = services[op.service].resource
                if free[name] and all(dep in done for dep in op.after):
                    following.append(max(cycle + 1, next_issue[name]))
        if not following:
            heads = ["{}:{}".format(block, stream[pc[block]]) for block, stream in programs.items()
                     if pc[block] < len(stream)]
            raise ValueError("deadlock at cycle {} with heads {}".format(cycle, ", ".join(heads)))
        cycle = min(following)

    result = {"last_cycle": cycle if operations else None, "events": events,
              "event_counts": dict(Counter(event["event"] for event in events))}
    if dma is not None:
        if not dma.port.drained:
            raise ValueError("DMA port remains active at model retirement")
        result["dma_responses"] = dma_responses
    return result
