"""Resource demand for a typed DMA transfer at scheduling granularity."""
from dataclasses import dataclass
from math import gcd


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


def dma_cost(profile, request):
    """Price a burst by its bottleneck channel and fixed response latency."""
    duration = 0
    active = []
    for channel, size in enumerate(channel_bytes(request.address, request.size, request.record_beats)):
        if not size:
            continue
        active.append(CHANNELS[channel])
        latency = profile.return_latency[channel]
        if profile.mixed:
            if request.write:
                latency = profile.mixed.write_latency
            latency += profile.mixed.row_miss
        duration = max(duration, size // BEAT_BYTES + latency)
    return duration, active

