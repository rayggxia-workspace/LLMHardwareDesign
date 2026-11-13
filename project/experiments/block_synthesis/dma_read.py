"""Clock the typed DMA fabric with an explicit DDR service profile."""
from bisect import bisect_right
from collections import deque
from collections.abc import Hashable
from dataclasses import dataclass, field

from dma_offer import DmaOfferChannel


@dataclass(frozen=True)
class Read:
    client: int
    address: int
    size: int
    record_beats: int
    write: bool = False

    def valid(self):
        lengths = (2,) if self.client < 9 else (17, 18)
        alignment = 128 if self.client < 9 else 64
        return (0 <= self.client < 12 and (not self.write or 3 <= self.client < 9)
                and self.record_beats in lengths
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
class MixedTiming:
    """Bank and direction rules derived from PR182, in scheduler ticks."""

    queue: int
    write_latency: int
    bank_issue: int = 2
    row_miss: int = 6
    turnaround: int = 4

    @classmethod
    def from_spec(cls, spec):
        if (not isinstance(spec, dict) or spec.keys() != {'queue', 'write_latency'}
                or any(type(n) is not int or n < 1 for n in spec.values())):
            raise ValueError('mixed DMA requires positive queue depth and write latency')
        return cls(**spec)


@dataclass(frozen=True)
class Profile:
    return_latency: tuple[int, int]
    ddr_ready: tuple = ()
    client_ready: tuple = ()
    ffn_provider: FfnProvider | None = None
    mixed: MixedTiming | None = None

    @classmethod
    def from_spec(cls, spec):
        if (not isinstance(spec, dict)
                or spec.keys() - {'return_latency', 'ddr_ready', 'client_ready', 'addresses', 'ffn_provider',
                                  'mixed'}):
            raise ValueError('unknown typed DMA profile field')
        client_ready = ready_intervals(spec.get('client_ready', ()), 4095)
        mixed = MixedTiming.from_spec(spec['mixed']) if 'mixed' in spec else None
        if 'ffn_provider' in spec:
            if {'return_latency', 'ddr_ready'} & spec.keys():
                raise ValueError('#251 FFN provider already defines DDR timing and readiness')
            return cls((7, 8), client_ready=client_ready,
                       ffn_provider=FfnProvider.from_spec(spec['ffn_provider']), mixed=mixed)
        latencies = tuple(spec.get('return_latency', ()))
        if len(latencies) != 2 or any(type(n) is not int or n < 1 for n in latencies):
            raise ValueError('typed DMA needs one positive DDR return latency per channel')
        return cls(latencies, ready_intervals(spec.get('ddr_ready', ()), 15), client_ready, mixed=mixed)


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
    write: bool | None = None


@dataclass(eq=False)
class ReadRecord:
    key: Hashable
    client: int
    address: int
    length: int
    sent: int = 0
    returned: int = 0
    write: bool = False

    @property
    def channel(self):
        return (self.address >> 11) & 1


@dataclass
class _Beat:
    record: ReadRecord
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
    bank_free: list = field(default_factory=lambda: [0] * 4)
    bank_rows: list = field(default_factory=lambda: [None] * 4)
    response_write: bool = False
    response_open: int = 0


@dataclass(slots=True)
class ReadEdge:
    """Explicit registered client offers and the resulting edge handshakes."""

    offers: dict[int, ReadRecord]
    accepted: list = field(default_factory=list)
    delivered: list = field(default_factory=list)
    issued: list = field(default_factory=list)
    captured: list = field(default_factory=list)


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
        if key in self.remaining or read.write and self.profile.mixed is None:
            raise ValueError('invalid or duplicate DMA submission')
        stride = 64 * read.record_beats
        self.remaining[key] = read.size // 64
        self.receipts[key] = []
        self.source[read.client].extend(ReadRecord(key, read.client, address, read.record_beats, write=read.write)
                                       for address in range(read.address, read.address + read.size, stride))

    def open_native(self, key, read):
        """Register one record whose client will offer each beat explicitly."""
        if key in self.remaining or not read.valid() or read.write or read.size != 64 * read.record_beats:
            raise ValueError('invalid native DMA record')
        self.remaining[key] = read.record_beats
        self.receipts[key] = []
        return ReadRecord(key, read.client, read.address, read.record_beats)

    def advance(self, tick, *, edge=None):
        """Plan from pre-edge state, apply the handshakes, return completed reads."""
        offers = edge.offers if edge is not None else {}
        if any(not 0 <= client < 12 or client != record.client or self.source[client]
               or record.key not in self.remaining or record.sent >= record.length
               for client, record in offers.items()):
            raise ValueError('native DMA offer does not match an open record and idle source')
        completed = []
        client_ready = ready_mask(self.profile.client_ready, tick, 4095)
        forwarded = self._client_responses(client_ready)
        reservations = []
        captures = []
        for ch, channel in enumerate(self.channels):
            free = [entry for entry, beat in enumerate(channel.beats) if beat is None]
            reservations.append(self._source_reservations(ch, channel, free, offers))
            channel.descriptors = {r for r in channel.descriptors if r.returned < r.length}
            self._ddr_offers(tick, ch, channel, self._ddr_ready(tick, ch, channel), edge)
            captures.extend(self._ddr_returns(tick, ch, channel, forwarded, edge))
        for skid in sorted(forwarded):
            ch, entry = self.skids[skid]
            beat = self.channels[ch].beats[entry]
            record = beat.record
            self.channels[ch].beats[entry] = None
            self.skids[skid] = None
            self.client_counts[record.client] -= 1
            record.returned += 1
            if edge is not None:
                edge.delivered.append((record, beat.address))
            key = record.key
            self.receipts[key].append(BeatReceipt(beat.address, ch, entry, beat.reserved,
                                                  beat.offer, beat.issue, beat.captured, tick,
                                                  beat.issue_lane, beat.return_lane, True if record.write else None))
            self.remaining[key] -= 1
            if self.remaining[key] == 0:
                del self.remaining[key]
                completed.append((key, tuple(sorted(self.receipts.pop(key), key=lambda row: row.address))))
        for skid, item in captures:
            self.skids[skid] = item
        for ch, (channel, reserved) in enumerate(zip(self.channels, reservations)):
            for entry, record in reserved:
                address = record.address + 64 * record.sent
                channel.beats[entry] = _Beat(record, address, tick)
                channel.descriptors.add(record)
                self.client_counts[record.client] += 1
                record.sent += 1
                source = self.source[record.client]
                if source and source[0] is record and record.sent == record.length:
                    source.popleft()
                if edge is not None:
                    edge.accepted.append((record, address, 32 * ch + entry))
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

    def _source_reservations(self, ch, channel, free, offers):
        result = []
        free_desc = 32 - len(channel.descriptors)
        lanes = min(2, len(free))
        for offset in range(12):
            client = (channel.source_cursor + offset) % 12
            if len(result) == lanes:
                break
            if self.client_counts[client] >= 32:
                continue
            source = self.source[client]
            record = source[0] if source else offers.get(client)
            if record is None:
                continue
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
        if self.profile.mixed is not None:
            # Already-held return lanes still consume backend queue entries.
            free = self.profile.mixed.queue - sum(map(len, channel.returns))
            free -= sum(entry is not None for entry in channel.return_lanes)
            available = self._provider_ready(tick, ch, channel, provider)
            if free <= 0:
                return 0
            if free == 1 and available == 3:
                if channel.offer.entries[0] is None and channel.offer.entries[1] is not None:
                    return 2
                return 1
            return available
        return self._provider_ready(tick, ch, channel, provider)

    def _provider_ready(self, tick, ch, channel, provider):
        if provider is None:
            return (ready_mask(self.profile.ddr_ready, tick, 15) >> (2 * ch)) & 3
        return sum(1 << lane for lane in range(2) if provider.ready(
            tick, 2 * ch + lane, len(channel.returns[lane]) + (channel.return_lanes[lane] is not None)))

    def _ddr_offers(self, tick, ch, channel, ready, edge):
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
                if edge is not None:
                    edge.issued.append((2 * ch + lane, beat.address, 32 * ch + entry))
                timing = self.profile.mixed
                due = tick + self.profile.return_latency[ch]
                if timing is not None:
                    bank, row = (beat.address // 64) % 4, beat.address // 1024
                    command = max(tick, channel.bank_free[bank])
                    latency = timing.write_latency if beat.record.write else self.profile.return_latency[ch]
                    due = command + latency + (timing.row_miss if channel.bank_rows[bank] != row else 0)
                    channel.bank_free[bank] = command + timing.bank_issue
                    channel.bank_rows[bank] = row
                queue.append((due, entry))
        for entry in channel.offer.entries:
            if entry is not None and channel.beats[entry].offer is None:
                channel.beats[entry].offer = tick + 1

    def _ddr_returns(self, tick, ch, channel, forwarded, edge):
        free = deque(slot for slot in range(3 * ch, 3 * ch + 3)
                     if self.skids[slot] is None or slot in forwarded)
        captures = []
        timing = self.profile.mixed
        if timing is not None:
            self._select_response_direction(tick, channel, free)
        for lane in range(2):
            entry = channel.return_lanes[lane]
            queue = channel.returns[lane if self.profile.ffn_provider is not None else 0]
            if entry is None and queue and queue[0][0] <= tick:
                candidate = queue[0][1]
                if timing is not None and (tick < channel.response_open
                                           or channel.beats[candidate].record.write != channel.response_write):
                    continue
                _, entry = queue.popleft()
            if entry is not None and free:
                beat = channel.beats[entry]
                beat.captured = tick
                if self.profile.ffn_provider is not None:
                    beat.return_lane = 2 * ch + lane
                if edge is not None:
                    edge.captured.append((2 * ch + lane, 32 * ch + entry))
                captures.append((free.popleft(), (ch, entry)))
                entry = None
            channel.return_lanes[lane] = entry
        return captures

    def _select_response_direction(self, tick, channel, free):
        if not free or tick < channel.response_open or any(entry is not None for entry in channel.return_lanes):
            return
        heads = [queue[0][1] for queue in channel.returns if queue and queue[0][0] <= tick]
        if heads:
            entry = min(heads, key=lambda head: channel.beats[head].issue)
            write = channel.beats[entry].record.write
            if write != channel.response_write:
                channel.response_write = write
                channel.response_open = tick + self.profile.mixed.turnaround


def receipt_json(receipts):
    return [{key: value for key, value in vars(receipt).items() if value is not None} for receipt in receipts]
