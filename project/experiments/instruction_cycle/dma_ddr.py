"""Finite ordered DMA with explicit backend completion and client retirement."""

from collections import deque
from dataclasses import dataclass, field
import heapq


BURST = 64


def positive(value):
    return type(value) is int and value > 0


@dataclass(frozen=True)
class Transfer:
    tag: str
    address: int
    size: int
    write: bool = False
    data: bytes = b""


@dataclass(frozen=True)
class Fence:
    tag: str


@dataclass(frozen=True)
class Response:
    tag: str
    data: bytes


@dataclass(frozen=True)
class Beat:
    identifier: tuple
    address: int
    write: bool
    payload: bytes


@dataclass
class Descriptor:
    request: object
    next_beat: int = 0
    completed: dict = field(default_factory=dict)

    @property
    def count(self):
        return 0 if isinstance(self.request, Fence) else self.request.size // BURST

    def beat(self):
        offset = self.next_beat * BURST
        request = self.request
        return Beat((request.tag, self.next_beat), request.address + offset, request.write,
                    request.data[offset:offset + BURST])


class TimedBackend:
    """Deterministic finite reference peer. Due edges are write-visibility edges."""

    def __init__(self, depth, latency, write_latency=None, accept_period=1, accept_phase=0):
        write_latency = latency if write_latency is None else write_latency
        if (not all(positive(n) for n in (depth, latency, write_latency, accept_period))
                or type(accept_phase) is not int or not 0 <= accept_phase < accept_period):
            raise ValueError("invalid timed backend configuration")
        self.depth, self.latency, self.write_latency = depth, latency, write_latency
        self.period, self.phase = accept_period, accept_phase
        self.pending = []
        self.serial = 0
        self.last_accept = -1

    @property
    def idle(self):
        return not self.pending

    def can_accept(self, cycle, beat):
        return len(self.pending) < self.depth and cycle % self.period == self.phase and self.last_accept != cycle

    def submit(self, cycle, beat):
        if not self.can_accept(cycle, beat):
            raise ValueError("backend did not accept burst")
        latency = self.write_latency if beat.write else self.latency
        heapq.heappush(self.pending, (cycle + latency, self.serial, beat.identifier))
        self.serial += 1
        self.last_accept = cycle

    def completions(self, cycle):
        completed = []
        while self.pending and self.pending[0][0] <= cycle:
            _, _, identifier = heapq.heappop(self.pending)
            completed.append(identifier)
        return completed


class DmaPort:
    """One admitted and one offered backend beat per edge; in-order client responses.

    The backend must report completion IDs only when write data is visible or a
    read really returns. A same-address lock lasts until that completion. Beat
    credits are held through completion; descriptor slots through retirement.
    """

    def __init__(self, backend, queue_depth, credits, response_depth, initial_memory=None):
        if not all(positive(n) for n in (queue_depth, credits, response_depth)):
            raise ValueError("invalid DMA capacity")
        self.memory = dict(initial_memory or {})
        if any(type(addr) is not int or not 0 <= addr < 2**64 or addr % BURST
               or not isinstance(data, bytes) or len(data) != BURST for addr, data in self.memory.items()):
            raise ValueError("invalid initial memory")
        self.backend = backend
        self.queue_depth, self.credits, self.response_depth = queue_depth, credits, response_depth
        self.descriptors = deque()
        self.responses = deque()
        self.inflight = {}
        self.addresses = set()
        self.tags = set()
        self.held = None
        self.pending_offer = None
        self.blocking_fence = None
        self.events = []
        self.last_cycle = -1

    @property
    def drained(self):
        return (not self.descriptors and not self.responses and not self.inflight and self.held is None
                and self.pending_offer is None and self.blocking_fence is None and self.backend.idle)

    def _emit(self, cycle, event, tag, beat=None):
        row = {"cycle": cycle, "event": event, "tag": tag}
        if beat is not None:
            row.update(beat=beat.identifier[1], addr=beat.address)
        self.events.append(row)

    def _validate(self, offer):
        if not isinstance(offer, (Transfer, Fence)) or not isinstance(offer.tag, str) or not offer.tag:
            raise ValueError("invalid DMA request identity")
        if offer.tag in self.tags:
            raise ValueError("reused DMA tag: " + offer.tag)
        if isinstance(offer, Transfer) and (
                type(offer.address) is not int or offer.address < 0 or offer.address % BURST
                or not positive(offer.size) or offer.size % BURST or offer.address + offer.size > 2**64
                or type(offer.write) is not bool or not isinstance(offer.data, bytes)
                or len(offer.data) != (offer.size if offer.write else 0)):
            raise ValueError("invalid DMA burst range or payload")

    def step(self, cycle, offer=None, consume=True):
        if (type(cycle) is not int or cycle <= self.last_cycle or type(consume) is not bool
                or (not self.drained and cycle != self.last_cycle + 1)):
            raise ValueError("DMA must sample active edges exactly once in order")
        if offer is not None:
            self._validate(offer)
        if self.pending_offer is not None and offer != self.pending_offer:
            raise ValueError("DMA source changed an unaccepted offer")
        self.last_cycle = cycle
        ids = list(self.backend.completions(cycle))
        if len(set(ids)) != len(ids) or any(identifier not in self.inflight for identifier in ids):
            raise ValueError("unknown or duplicate backend completion identity")

        # Sample beginning-of-edge DMA occupancy. Backend capacity can refill
        # on a completion edge; DMA credits and address locks release next edge.
        accepted = offer is not None and len(self.descriptors) + len(self.responses) < self.queue_depth
        retired = self.responses[0] if self.responses and consume else None
        publish = None
        if self.descriptors and len(self.responses) < self.response_depth:
            head = self.descriptors[0]
            if isinstance(head.request, Fence):
                if not self.responses and not self.inflight and self.held is None and self.backend.idle:
                    publish = Response(head.request.tag, b"")
                    self.blocking_fence = head.request.tag
                    self._emit(cycle, "fence_ready", head.request.tag)
            elif len(head.completed) == head.count:
                publish = Response(head.request.tag, b"".join(head.completed[index] for index in range(head.count)))

        if not self.blocking_fence and self.held is None and len(self.inflight) < self.credits:
            for descriptor in self.descriptors:
                if isinstance(descriptor.request, Fence):
                    break
                if descriptor.next_beat < descriptor.count:
                    beat = descriptor.beat()
                    # Preserve issue order, including across requests from
                    # different Blocks sharing this port.
                    if beat.address not in self.addresses:
                        self.held = (descriptor, beat)
                    break
        if self.held is not None:
            descriptor, beat = self.held
            if self.backend.can_accept(cycle, beat):
                self.backend.submit(cycle, beat)
                self.inflight[beat.identifier] = (descriptor, beat)
                self.addresses.add(beat.address)
                descriptor.next_beat += 1
                self.held = None
                self._emit(cycle, "backend_accept", beat.identifier[0], beat)
            else:
                self._emit(cycle, "backend_stall", beat.identifier[0], beat)

        for identifier in ids:
            descriptor, beat = self.inflight.pop(identifier)
            self.addresses.remove(beat.address)
            if beat.write:
                self.memory[beat.address] = beat.payload
                value = b""
            else:
                if beat.address not in self.memory:
                    raise ValueError("read of undefined memory at {:#x}".format(beat.address))
                value = self.memory[beat.address]
            descriptor.completed[identifier[1]] = value
            self._emit(cycle, "write_visible" if beat.write else "read_return", identifier[0], beat)
        if retired is not None:
            self.responses.popleft()
            if self.blocking_fence == retired.tag:
                self.blocking_fence = None
            self._emit(cycle, "retire", retired.tag)
        if publish is not None:
            self.descriptors.popleft()
            self.responses.append(publish)
            self._emit(cycle, "response", publish.tag)
        if accepted:
            self.descriptors.append(Descriptor(offer))
            self.tags.add(offer.tag)
            self._emit(cycle, "accept", offer.tag)
        self.pending_offer = None if accepted else offer
        return accepted, retired
