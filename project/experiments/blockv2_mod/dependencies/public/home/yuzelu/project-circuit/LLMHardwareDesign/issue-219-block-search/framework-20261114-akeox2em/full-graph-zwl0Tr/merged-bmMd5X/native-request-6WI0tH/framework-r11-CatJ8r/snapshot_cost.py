"""Memory resource demand at scheduling granularity."""
from collections import deque
from dataclasses import dataclass
from math import gcd
from types import MappingProxyType

from dma_read import ready_mask


CHANNEL_BYTES = 2048
BEAT_BYTES = 64
CHANNELS = ('DDR.channel0', 'DDR.channel1')


@dataclass(frozen=True)
class ClientResponse:
    """Earliest possible ACK following an enabled client response edge."""
    stalls: tuple
    endpoint: object = None

    def valid(self):
        return self.endpoint is None or self.endpoint.valid()

    def next_tick(self, tick):
        while True:
            allowed = self.endpoint.next_tick(tick) if self.endpoint else tick
            for start, end in self.stalls:
                if start <= allowed - 1 < end:
                    allowed = end + 1
            if allowed == tick:
                return tick
            tick = allowed


class SnapshotSram:
    """Track pending access counts and two response slots per feeder port."""

    def __init__(self, ready):
        self.ready = ready
        self.requests = (deque(), deque())
        self.responses = (deque(), deque())
        self.run = None

    @property
    def active(self):
        return any(self.requests) or any(self.responses)

    def submit(self, key, access):
        width = 4 if access.wide else 1
        self.requests[access.wide].append((key, access.words // width))

    def next_edge(self, tick):
        for port in (1, 0):
            queue, slots = self.requests[port], self.responses[port]
            if (queue and queue[0][1] > 1 and len(slots) == 2
                    and slots[0][0] == tick and slots[1][0] == tick + 1
                    and all(owner is None for _, owner in slots)
                    and not self.responses[1 - port] and (port or not self.requests[1])
                    and ready_mask(self.ready, tick, 3) & (1 << port)):
                # With both slots rotating, ACK and issue each advance once
                # per tick until a gate closes or the last request can issue.
                end = tick + queue[0][1] - 1
                for lo, hi, mask in self.ready:
                    if hi > tick and not mask & (1 << port):
                        end = min(end, lo)
                        break
                self.run = tick, port
                return end
        future = []
        for port, (queue, slots) in enumerate(zip(self.requests, self.responses)):
            if queue and len(slots) < 2:
                return tick
            if slots:
                edge = max(tick, slots[0][0])
                for lo, hi, mask in self.ready:
                    if edge < lo:
                        break
                    if edge < hi and not mask & (1 << port):
                        edge = hi
                future.append(edge)
        return min(future)

    def advance(self, tick):
        if self.run is not None:
            start, port = self.run
            self.run = None
            if tick > start:
                key, count = self.requests[port][0]
                self.requests[port][0] = key, count - (tick - start)
                slots = self.responses[port]
                slots.clear()
                slots.extend(((tick, None), (tick + 1, None)))
        ready = ready_mask(self.ready, tick, 3)
        completed = []
        for port, slots in enumerate(self.responses):
            if slots and slots[0][0] <= tick and ready & (1 << port):
                _, owner = slots.popleft()
                if owner is not None:
                    completed.append((owner, ()))
        for port in (1, 0):
            queue, slots = self.requests[port], self.responses[port]
            if queue and len(slots) < 2:
                key, count = queue[0]
                if count == 1:
                    queue.popleft()
                else:
                    queue[0] = key, count - 1
                slots.append((tick + 2, key if count == 1 else None))
                break
        return completed


def channel_bytes(address, size, record_beats=2):
    """Split a contiguous transfer across the two 2 KiB-interleaved channels."""
    if record_beats != 2:
        # Each record stays on the channel selected by its starting address.
        record_bytes = record_beats * BEAT_BYTES
        period = (2 * CHANNEL_BYTES) // gcd(2 * CHANNEL_BYTES, record_bytes)
        whole, tail = divmod(size // record_bytes, period)
        first_channel = sum((address + i * record_bytes) // CHANNEL_BYTES % 2 == 0 for i in range(tail))
        first_bytes = (whole * (period // 2) + first_channel) * record_bytes
        return first_bytes, size - first_bytes
    first, within = divmod(address, CHANNEL_BYTES)
    pair_count, tail = divmod(within + size, 2 * CHANNEL_BYTES)
    counts = [pair_count * CHANNEL_BYTES + min(tail, CHANNEL_BYTES) - within,
              pair_count * CHANNEL_BYTES + max(0, tail - CHANNEL_BYTES)]
    return tuple(counts if first % 2 == 0 else reversed(counts))


def measured_dma_cost(samples):
    """Index isolated transfer measurements by channel work and direction."""
    result = {}
    for row in samples:
        if (not isinstance(row, (tuple, list)) or len(row) != 4
                or any(type(n) is not int for n in row) or min(row[:2]) < 0
                or any(n % 128 for n in row[:2]) or not sum(row[:2])
                or row[2] not in (0, 1) or row[3] < 1):
            raise ValueError('invalid snapshot DMA measurement')
        ch0, ch1, direction, ticks = row
        key = ((ch0, ch1), bool(direction))
        if key in result:
            raise ValueError('duplicate snapshot DMA measurement')
        result[key] = ticks
    return MappingProxyType(result)


def dma_cost(profile, request, measured=None):
    """Price a burst by its bottleneck channel and fixed response latency."""
    counts = channel_bytes(request.address, request.size, request.record_beats)
    used = tuple(channel for channel, size in enumerate(counts) if size)
    active = tuple(CHANNELS[channel] for channel in used)
    measured_ticks = measured.get((counts, request.write)) if measured and request.record_beats == 2 else None
    if measured_ticks is not None:
        return measured_ticks, active
    if profile.mixed is None:
        return max(counts[ch] // BEAT_BYTES + profile.return_latency[ch] for ch in used), active

    timing = profile.mixed
    beats = request.size // BEAT_BYTES
    latency = timing.write_latency if request.write else max(profile.return_latency[ch] for ch in used)
    # One client delivers at most one beat per tick across both channels.
    # Reservation and return-slot handoff add three edges to the cold read.
    startup = latency + timing.row_miss + 3
    if request.write:
        startup += timing.turnaround
    # The backend queue recycles a slot at capture, before the client ACK.
    # Charge its steady-state rate only for beats beyond the initial credits.
    queue = timing.queue
    remaining = max(0, max(counts) // BEAT_BYTES - queue)
    credit_latency = latency + 3
    credit_delay = (remaining * max(0, credit_latency - queue) + queue - 1) // queue
    return startup + beats + credit_delay, active

