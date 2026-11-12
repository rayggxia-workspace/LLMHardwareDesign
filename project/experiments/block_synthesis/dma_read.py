"""Clock the #251 typed read fabric with an explicit DDR service profile."""
from bisect import bisect_right
from collections import deque
from dataclasses import dataclass, field

from dma_offer import DmaOfferChannel


@dataclass(frozen=True)
class Read:
    client: int
    address: int
    size: int
    record_beats: int

    def valid(self):
        lengths = (2,) if self.client < 9 else (17, 18)
        alignment = 128 if self.client < 9 else 64
        return (0 <= self.client < 12 and self.record_beats in lengths
                and self.address % alignment == 0 and self.size > 0 and self.size % (self.record_beats * 64) == 0
                and 0 <= self.address < self.address + self.size <= 2**64)


def ready_intervals(rows, full):
    ranges = tuple(tuple(row) for row in rows)
    previous = 0
    for start, end, mask in ranges:
        if (any(type(v) is not int for v in (start, end, mask))
                or not previous <= start < end or not 0 <= mask <= full):
            raise ValueError('invalid typed DMA ready intervals')
        previous = end
    return ranges


@dataclass(frozen=True)
class FfnProvider:
    mode: int
    seed: int
    cycle_offset: int = 0

    @classmethod
    def from_spec(cls, spec):
        if (not isinstance(spec, dict) or spec.keys() - {'mode', 'seed', 'cycle_offset'}
                or not {'mode', 'seed'} <= spec.keys()
                or any(type(n) is not int or n < 0 for n in spec.values()) or spec['mode'] not in (0, 1)):
            raise ValueError('invalid #251 FFN provider')
        return cls(**spec)

    def ready(self, tick, lane, queued):
        return queued < 16 and (self.mode == 0 or (self.cycle_offset + tick + lane) % 7 != self.seed % 7)


@dataclass(frozen=True)
class Profile:
    return_latency: tuple[int, int]
    ddr_ready: tuple = ()
    client_ready: tuple = ()
    ffn_provider: FfnProvider | None = None

    @classmethod
    def from_spec(cls, spec):
        if (not isinstance(spec, dict)
                or spec.keys() - {'return_latency', 'ddr_ready', 'client_ready', 'addresses', 'ffn_provider'}):
            raise ValueError('unknown typed DMA profile field')
        client_ready = ready_intervals(spec.get('client_ready', ()), 4095)
        if 'ffn_provider' in spec:
            if {'return_latency', 'ddr_ready'} & spec.keys():
                raise ValueError('#251 FFN provider already defines DDR timing and readiness')
            return cls((7, 8), client_ready=client_ready, ffn_provider=FfnProvider.from_spec(spec['ffn_provider']))
        latencies = tuple(spec.get('return_latency', ()))
        if len(latencies) != 2 or any(type(n) is not int or n < 1 for n in latencies):
            raise ValueError('typed DMA needs one positive DDR return latency per channel')
        return cls(latencies, ready_intervals(spec.get('ddr_ready', ()), 15), client_ready)


def ready_mask(ranges, tick, full):
    index = bisect_right(ranges, tick, key=lambda row: row[0]) - 1
    if index >= 0 and tick < ranges[index][1]:
        return ranges[index][2]
    return full


@dataclass(frozen=True)
class BeatReceipt:
    address: int
    channel: int
    entry: int
    reserved: int
    offer: int
    issue: int
    captured: int
    delivered: int
    issue_lane: int | None = None
    return_lane: int | None = None


@dataclass(eq=False)
class _Record:
    key: tuple[int, int]
    client: int
    address: int
    length: int
    sent: int = 0
    returned: int = 0

    @property
    def channel(self):
        return (self.address >> 11) & 1


@dataclass
class _Beat:
    record: _Record
    address: int
    reserved: int
    offer: int | None = None
    issue: int | None = None
    captured: int | None = None
    issue_lane: int | None = None
    return_lane: int | None = None


@dataclass
class _Channel:
    beats: list = field(default_factory=lambda: [None] * 32)
    descriptors: set = field(default_factory=set)
    offer: DmaOfferChannel = field(default_factory=DmaOfferChannel)
    source_cursor: int = 0
    returns: tuple = field(default_factory=lambda: (deque(), deque()))
    return_lanes: list = field(default_factory=lambda: [None, None])


class ReadFabric:
    def __init__(self, profile):
        self.profile = profile
        self.channels = (_Channel(), _Channel())
        self.source = [deque() for _ in range(12)]
        self.client_counts = [0] * 12
        self.client_cursor = [0] * 12
        self.client_locked = [None] * 12
        self.skids = [None] * 6
        self.remaining = {}
        self.receipts = {}

    @property
    def active(self):
        return bool(self.remaining or any(c.descriptors for c in self.channels))

    def submit(self, key, read):
        stride = 64 * read.record_beats
        self.remaining[key] = read.size // 64
        self.receipts[key] = []
        self.source[read.client].extend(_Record(key, read.client, address, read.record_beats)
                                       for address in range(read.address, read.address + read.size, stride))

    def advance(self, tick):
        """Plan from pre-edge state, apply the handshakes, return completed reads."""
        completed = []
        client_ready = ready_mask(self.profile.client_ready, tick, 4095)
        forwarded = self._client_responses(client_ready)
        reservations = []
        captures = []
        for ch, channel in enumerate(self.channels):
            free = [entry for entry, beat in enumerate(channel.beats) if beat is None]
            reservations.append(self._source_reservations(ch, channel, free))
            channel.descriptors = {r for r in channel.descriptors if r.returned < r.length}
            self._ddr_offers(tick, ch, channel, self._ddr_ready(tick, ch, channel))
            captures.extend(self._ddr_returns(tick, ch, channel, forwarded))
        for skid in sorted(forwarded):
            ch, entry = self.skids[skid]
            beat = self.channels[ch].beats[entry]
            record = beat.record
            self.channels[ch].beats[entry] = None
            self.skids[skid] = None
            self.client_counts[record.client] -= 1
            record.returned += 1
            key = record.key
            self.receipts[key].append(BeatReceipt(beat.address, ch, entry, beat.reserved,
                                                  beat.offer, beat.issue, beat.captured, tick,
                                                  beat.issue_lane, beat.return_lane))
            self.remaining[key] -= 1
            if self.remaining[key] == 0:
                del self.remaining[key]
                completed.append((key, tuple(sorted(self.receipts.pop(key), key=lambda row: row.address))))
        for skid, item in captures:
            self.skids[skid] = item
        for channel, reserved in zip(self.channels, reservations):
            for entry, record in reserved:
                channel.beats[entry] = _Beat(record, record.address + 64 * record.sent, tick)
                channel.descriptors.add(record)
                self.client_counts[record.client] += 1
                record.sent += 1
                if record.sent == record.length:
                    self.source[record.client].popleft()
        return completed

    def _client_responses(self, ready):
        forwarded = set()
        for client in range(12):
            chosen = self.client_locked[client]
            if chosen is None:
                for offset in range(6):
                    slot = (self.client_cursor[client] + offset) % 6
                    item = self.skids[slot]
                    if item is not None and self.channels[item[0]].beats[item[1]].record.client == client:
                        chosen = slot
                        break
            if chosen is not None and ready & (1 << client):
                forwarded.add(chosen)
                self.client_locked[client] = None
                self.client_cursor[client] = (chosen + 1) % 6
            else:
                self.client_locked[client] = chosen
        return forwarded

    def _source_reservations(self, ch, channel, free):
        result = []
        free_desc = 32 - len(channel.descriptors)
        lanes = min(2, len(free))
        for offset in range(12):
            client = (channel.source_cursor + offset) % 12
            if len(result) == lanes:
                break
            if not self.source[client] or self.client_counts[client] >= 32:
                continue
            record = self.source[client][0]
            if record.channel != ch or (not record.sent and not free_desc):
                continue
            free_desc -= not record.sent
            result.append((free[len(result)], record))
        if result:
            # Simultaneous sequential assignments in RTL use numeric client order.
            channel.source_cursor = (max(record.client for _, record in result) + 1) % 12
        return result

    def _ddr_ready(self, tick, ch, channel):
        provider = self.profile.ffn_provider
        if provider is None:
            return (ready_mask(self.profile.ddr_ready, tick, 15) >> (2 * ch)) & 3
        return sum(1 << lane for lane in range(2) if provider.ready(
            tick, 2 * ch + lane, len(channel.returns[lane]) + (channel.return_lanes[lane] is not None)))

    def _ddr_offers(self, tick, ch, channel, ready):
        old = channel.offer.entries
        reserved = sum(1 << i for i, beat in enumerate(channel.beats) if beat and beat.offer is None)
        channel.offer = channel.offer.advance(reserved, ready)
        for lane, entry in enumerate(old):
            if entry is not None and ready & (1 << lane):
                beat = channel.beats[entry]
                beat.issue = tick
                queue = channel.returns[0]
                if self.profile.ffn_provider is not None:
                    queue = channel.returns[lane]
                    beat.issue_lane = 2 * ch + lane
                queue.append((tick + self.profile.return_latency[ch], entry))
        for entry in channel.offer.entries:
            if entry is not None and channel.beats[entry].offer is None:
                channel.beats[entry].offer = tick + 1

    def _ddr_returns(self, tick, ch, channel, forwarded):
        free = deque(slot for slot in range(3 * ch, 3 * ch + 3)
                     if self.skids[slot] is None or slot in forwarded)
        captures = []
        for lane in range(2):
            entry = channel.return_lanes[lane]
            queue = channel.returns[lane if self.profile.ffn_provider is not None else 0]
            if entry is None and queue and queue[0][0] <= tick:
                _, entry = queue.popleft()
            if entry is not None and free:
                beat = channel.beats[entry]
                beat.captured = tick
                if self.profile.ffn_provider is not None:
                    beat.return_lane = 2 * ch + lane
                captures.append((free.popleft(), (ch, entry)))
                entry = None
            channel.return_lanes[lane] = entry
        return captures


def receipt_json(receipts):
    return [{key: value for key, value in vars(receipt).items() if value is not None} for receipt in receipts]
