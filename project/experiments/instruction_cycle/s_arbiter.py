"""Event model for the registered block_local_s_arbiter and its directed peer."""

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    arrival: int
    sequence: int
    address: int
    write: int


def next_ready(cycle, closed):
    for first, last in closed:
        if first <= cycle <= last:
            cycle = last + 1
    return cycle


def simulate(requests, memory_closed, response_closed, response_latency):
    """Return accepted ingress, SRAM, and response handshakes in pre-edge cycles.

    The upstream queues supply persistent head-valid. The peer holds each SRAM
    response once eligible. Closed intervals are sorted and disjoint.
    """
    if not requests or len(requests) != len(response_closed) or response_latency < 1:
        raise ValueError("incomplete arbiter peer configuration")
    for intervals in (memory_closed, *response_closed):
        end = -1
        for first, last in intervals:
            if first <= end or last < first:
                raise ValueError("invalid ready interval")
            end = last
    for stream in requests:
        if any(item.arrival < 0 or item.sequence != index or not 0 <= item.address < 1024
               or item.write not in (0, 1) for index, item in enumerate(stream)):
            raise ValueError("invalid client request")
    queues = [deque(stream) for stream in requests]
    pointer, cycle = 0, 0
    events = []
    while any(queues):
        cycle = max(cycle, min(queue[0].arrival for queue in queues if queue))
        # The grant is accepted into a one-entry command register even if SRAM is stalled.
        for distance in range(len(queues)):
            client = (pointer + distance) % len(queues)
            if queues[client] and queues[client][0].arrival <= cycle:
                break
        request = queues[client].popleft()
        pointer = (client + 1) % len(queues)
        sent = next_ready(cycle + 1, memory_closed)
        returned = next_ready(sent + response_latency, response_closed[client])
        for kind, edge in (("grant", cycle), ("send", sent), ("response", returned)):
            events.append({"event": kind, "cycle": edge, "client": client,
                           "sequence": request.sequence, "address": request.address,
                           "write": request.write})
        # RETURN sees the old owner until the accepting edge has completed.
        cycle = returned + 1
    return events
