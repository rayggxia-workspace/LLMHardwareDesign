"""Native M weight transport on the two live 105530 DDR devices.

The driver supplies bank install/release edges. This model owns request
locking, typed admission, both lane queues per channel and the response
skids. Only valid, uncancelled M weight records are accepted.
"""

from collections import deque
from dataclasses import dataclass, field

from dma_ddr import Beat
from qwen_descriptor_dma import BURST_BYTES, SLOTS_PER_CHANNEL
from qwen_native_ddr import DDR_PS, require
from qwen_prompt_cycle import CORE_PS, ROW_BYTES
from qwen_weight_record import ISSUE_WINDOW_CREDITS, LANE_DEPTH, SKIDS_PER_CHANNEL


CLIENTS = (9, 10, 11)
BANKS = 4
CHANNELS = 2
LANES_PER_CHANNEL = 2
TOTAL_SKIDS = CHANNELS * SKIDS_PER_CHANNEL
M_CREDITS = 32
# The historical fixture uses direct physical reads when advancing the U
# embedding/RMS row. These lanes and exact frozen regions carry local beat
# tags, not typed-M DMA generations.
HISTORY_DIRECT_BASES = {1: (3300175872, 3969437696), 3: (4543033344,)}


@dataclass(frozen=True)
class WeightFill:
    cycle: int
    client: int
    bank: int
    generation: int
    epoch: int
    beat: int
    address: int
    last: bool
    record_complete: bool


@dataclass
class _WeightRecord:
    address: int
    beats: int
    generation: int
    epoch: int
    issued: int = 0
    received: int = 0
    accepts: list = field(default_factory=list)
    timings: dict = field(init=False)

    def __post_init__(self):
        self.timings = {key: [None] * self.beats for key in
                        ("phy_admits", "phy_returns", "client_responses", "global_tags", "lanes")}

    @property
    def channel(self):
        return (self.address >> 11) & 1


@dataclass(frozen=True)
class _Request:
    client: int
    bank: int
    index: int
    record: _WeightRecord

    @property
    def address(self):
        return self.record.address + BURST_BYTES * self.index


@dataclass
class _Pending:
    slot: int
    request: _Request
    tag: int
    submitted: bool = False
    completed: bool = False


class WeightPipeline:
    """Advance registered M/fabric/bridge state from the drained prefix."""

    def __init__(self, fabric):
        self.fabric = fabric
        self.ddr = fabric.ddr
        require(fabric.open_record is None and not hasattr(fabric, "weight_prefix_state")
                and all(device.idle for device in self.ddr.dram), "weight pipeline requires drained descriptor prefix")
        self.generation = fabric.generation
        self.cycle = fabric.last_response
        self.records = {client: {} for client in CLIENTS}
        self.history = {}
        self.installs = {}
        self.releases = {}
        self.locked = {client: None for client in CLIENTS}
        self.bank_cursor = dict.fromkeys(CLIENTS, 0)
        self.response_cursor = dict.fromkeys(CLIENTS, 0)
        self.outstanding = dict.fromkeys(CLIENTS, 0)
        self.request_cursor = [0, 0]
        self.issue_cursor = [0, 0]
        self.previous_issues = [0, 0]
        self.occupied = {}
        self.reserved = set()
        self.offered = {}
        self.skids = {}
        self.lane_queues = [deque() for _ in range(CHANNELS * LANES_PER_CHANNEL)]
        self._restore_serial_cursors(self.ddr.events)
        self.event_count = len(self.ddr.events)

    def _restore_serial_cursors(self, events):
        # The earlier quiescent typed traffic has one source and one lane at
        # a time, or is a two-beat post-projection descriptor. In either
        # case the last physical issue on each channel is also the last
        # registered offer and belongs to the last source accepted.
        for kind, _, lane, tag, _ in events:
            if kind == "admit" and tag >> 32 == self.generation:
                client = (tag >> 6) & 15
                require(client in (0, 5), "unknown serial client during weight pipeline handoff")
                channel = lane // LANES_PER_CHANNEL
                self.issue_cursor[channel] = ((tag >> 10) + 1) % SLOTS_PER_CHANNEL
                self.request_cursor[channel] = (client + 1) % 12

    def resume_after_drained_clients(self):
        """Resume M after typed reads, historical row refills and strict writes."""
        require(self.idle and not any(self.records.values()) and not self.installs and not self.releases
                and not any(self.outstanding.values()) and self.fabric.open_record is None
                and self.fabric.generation == self.generation and all(device.idle for device in self.ddr.dram),
                "weight scope handoff requires drained M banks and unchanged DMA generation")
        events = self.ddr.events[self.event_count:]
        if events:
            require(all(cycle > self.cycle and (tag >> 32 == self.generation
                        or 0 <= tag < ROW_BYTES // BURST_BYTES
                        and address - tag * BURST_BYTES in HISTORY_DIRECT_BASES.get(lane, ()))
                        for kind, cycle, lane, tag, address in events if kind in ("admit", "return"))
                    and self.fabric.last_response > self.cycle, "external DMA edges do not follow the weight scope")
            self._restore_serial_cursors(events)
            self.previous_issues = [0, 0]
        # Strict writes do not change the typed arbiter, but cannot be
        # revisited on the core timeline after updating the shared device.
        writes = getattr(self.ddr, "write_events", ())
        write_return = writes[-1][1] if writes else -1
        self.cycle = max(self.cycle, self.fabric.last_response, write_return)
        self.event_count = len(self.ddr.events)

    @property
    def idle(self):
        """Report drained transport, even if the consumer still owns a filled bank."""
        return not (self.occupied or any(self.locked.values()) or any(
            record.issued < record.beats for banks in self.records.values() for record in banks.values()))

    def install_record(self, cycle, address, bank, generation, *, epoch=0, beats=17, client=9):
        """Schedule the M table's successful ALLOC-ACK edge."""
        require(type(cycle) is int and cycle > self.cycle and client in CLIENTS
                and type(bank) is int and 0 <= bank < BANKS and type(generation) is int
                and 0 < generation < 1 << 16 and type(epoch) is int and 0 <= epoch < 1 << 9
                and type(beats) is int and beats in (17, 18) and type(address) is int
                and 0 <= address <= (1 << 34) - beats * BURST_BYTES and address % BURST_BYTES == 0,
                "invalid M weight table install")
        key = client, bank, generation, epoch
        require(key not in self.history and (cycle, client) not in self.installs, "duplicate M weight table install")
        record = _WeightRecord(address, beats, generation, epoch)
        self.history[key] = record
        self.installs[cycle, client] = (bank, record)

    def release_record(self, cycle, bank, *, client=9):
        """Schedule the edge when the M table samples its bank's free mask."""
        require(type(cycle) is int and cycle > self.cycle and client in CLIENTS
                and type(bank) is int and 0 <= bank < BANKS
                and (cycle, client, bank) not in self.releases, "invalid M weight bank release")
        self.releases[cycle, client, bank] = None

    def record_result(self, bank, generation, *, epoch=0, client=9):
        """Return the per-beat timeline of a filled record."""
        record = self.history.get((client, bank, generation, epoch))
        require(record is not None and record.received == record.beats, "weight record has not filled")
        return {"address": record.address, "client_accepts": record.accepts[:],
                **{key: cycles[:] for key, cycles in record.timings.items()}}

    def _plan_accepts(self):
        require(not any(serial == 65535 and slot not in self.occupied
                        for slot, serial in enumerate(self.fabric.serials)), "M transport namespace needs a fence")
        accepts = {}
        for channel, cursor in enumerate(self.request_cursor):
            first = channel * SLOTS_PER_CHANNEL
            slots = [slot for slot in range(first, first + SLOTS_PER_CHANNEL) if slot not in self.occupied]
            applicants = [request for request in self.locked.values() if request is not None
                          and request.record.channel == channel and self.outstanding[request.client] < M_CREDITS]
            applicants.sort(key=lambda request: (request.client - cursor) % 12)
            for slot, request in zip(slots[:2], applicants):
                accepts[request.client] = slot
        return accepts

    def _consume_skids(self, cycle):
        fills = []
        for client in CLIENTS:
            eligible = [index for index, pending in self.skids.items() if pending.request.client == client]
            if not eligible:
                continue
            index = min(eligible, key=lambda index: (index - self.response_cursor[client]) % TOTAL_SKIDS)
            pending = self.skids.pop(index)
            request = pending.request
            record = request.record
            record.timings["client_responses"][request.index] = cycle
            record.received += 1
            self.response_cursor[client] = (index + 1) % TOTAL_SKIDS
            del self.occupied[pending.slot]
            fills.append(WeightFill(cycle, client, request.bank, record.generation, record.epoch, request.index,
                                    request.address, request.index + 1 == record.beats,
                                    record.received == record.beats))
        if fills:
            self.fabric.last_response = cycle
        return fills

    def _physical_edge(self, cycle):
        issues = [0, 0]
        for lane, queue in enumerate(self.lane_queues):
            channel = lane // LANES_PER_CHANNEL
            ready = len(queue) < LANE_DEPTH and (not self.ddr.mode or (cycle + lane) % 5 != 0)
            if queue and queue[0].completed:
                first = channel * SKIDS_PER_CHANNEL
                skid = next((index for index in range(first, first + SKIDS_PER_CHANNEL)
                             if index not in self.skids), None)
                if skid is not None:
                    pending = queue.popleft()
                    request = pending.request
                    self.skids[skid] = pending
                    request.record.timings["phy_returns"][request.index] = cycle
                    self.ddr.events.append(("return", cycle, lane, pending.tag, request.address))
            if ready and lane in self.offered:
                pending = self.offered.pop(lane)
                queue.append(pending)
                request = pending.request
                request.record.timings["phy_admits"][request.index] = cycle
                request.record.timings["lanes"][request.index] = lane
                issues[channel] += 1
                self.ddr.events.append(("admit", cycle, lane, pending.tag, request.address))
        return issues

    def _replace_offers(self, issues):
        for channel, issue_count in enumerate(issues):
            first_lane = channel * LANES_PER_CHANNEL
            lanes = range(first_lane, first_lane + LANES_PER_CHANNEL)
            held = sum(lane in self.offered for lane in lanes)
            budget = ISSUE_WINDOW_CREDITS - self.previous_issues[channel] - issue_count - held
            require(budget >= 0, "typed transport overran its issue budget")
            candidates = [slot for slot in self.reserved if slot // SLOTS_PER_CHANNEL == channel]
            candidates.sort(key=lambda slot: (slot - self.issue_cursor[channel]) % SLOTS_PER_CHANNEL)
            for lane, slot in zip((lane for lane in lanes if lane not in self.offered), candidates[:budget]):
                self.offered[lane] = self.occupied[slot]
                self.reserved.remove(slot)
                self.issue_cursor[channel] = (slot + 1) % SLOTS_PER_CHANNEL
        self.previous_issues = issues

    def _step_sources(self, cycle, accepts, fills):
        fill_clients = {fill.client for fill in fills}
        for client, banks in self.records.items():
            fired = client in accepts
            if fired:
                request = self.locked[client]
                slot = accepts[client]
                tag = self.fabric._allocate(slot, client)
                self.occupied[slot] = _Pending(slot, request, tag)
                self.reserved.add(slot)
                record = request.record
                record.issued += 1
                require(record.issued == request.index + 1, "M source accepted out of record order")
                record.accepts.append(cycle)
                record.timings["global_tags"][request.index] = tag
                self.request_cursor[record.channel] = (client + 1) % 12
                self.bank_cursor[client] = (request.bank + 1) % BANKS
                self.locked[client] = None
            if self.locked[client] is None and self.outstanding[client] + fired < M_CREDITS:
                candidates = [bank for bank, record in banks.items() if record.issued < record.beats]
                cursor = self.bank_cursor[client]
                bank = min(candidates, key=lambda bank: (bank - cursor) % BANKS, default=None)
                if bank is not None:
                    record = banks[bank]
                    self.locked[client] = _Request(client, bank, record.issued, record)
            self.outstanding[client] += fired - (client in fill_clients)
            install = self.installs.pop((cycle, client), None)
            if install is not None:
                bank, record = install
                require(bank not in banks, "M installed a weight record in an occupied bank")
                banks[bank] = record
            for bank in range(BANKS):
                key = cycle, client, bank
                if key in self.releases:
                    require(bank in banks and banks[bank].received == banks[bank].beats,
                            "M released a weight bank before its fills")
                    del banks[bank]
                    del self.releases[key]

    def _advance_ddr(self, cycle):
        target = (cycle + 1) * CORE_PS // DDR_PS
        for channel, device in enumerate(self.ddr.dram):
            first = channel * LANES_PER_CHANNEL
            current = cycle * CORE_PS // DDR_PS
            tick = self.ddr.tick[channel]
            require(tick <= current and (tick == current or device.idle),
                    "missing DDR advancement while weight transactions are live")
            require(not device.completions(current), "unexpected DDR callback before weight edge")
            tick = current
            lane_queues = self.lane_queues[first:first + LANES_PER_CHANNEL]
            by_tag = {pending.tag: pending for queue in lane_queues for pending in queue}
            while tick < target:
                waiting = False
                for lane in (first + tick % 2, first + 1 - tick % 2):
                    pending = next((entry for entry in self.lane_queues[lane] if not entry.submitted), None)
                    if pending is None:
                        continue
                    waiting = True
                    request = pending.request
                    beat = Beat((lane, pending.tag), request.address, False, None)
                    require(not any(other is not pending and other.submitted and not other.completed
                                    and other.request.address == request.address for other in by_tag.values()),
                            "live DDR weight model does not support simultaneous same-address reads")
                    if device.can_accept(tick, beat):
                        device.submit(tick, beat)
                        pending.submitted = True
                        self.ddr.events.append(("ddr_accept", tick, lane, pending.tag, request.address))
                tick = target if device.idle and not waiting else tick + 1
                for lane, tag in device.completions(tick):
                    pending = by_tag.get(tag)
                    require(pending is not None and pending.submitted and not pending.completed,
                            "unexpected weight DDR callback")
                    pending.completed = True
                    self.ddr.events.append(("callback", tick, lane, tag, pending.request.address))
            self.ddr.tick[channel] = tick

    def step(self, cycle):
        """Apply one pre-edge cycle and return all M client fills on it."""
        require(type(cycle) is int and cycle > self.cycle, "weight pipeline requires increasing core edges")
        require(len(self.ddr.events) == self.event_count and self.fabric.generation == self.generation,
                "weight pipeline must resume after external DDR traffic")
        if cycle != self.cycle + 1:
            require(self.idle and all(edge >= cycle for edge, _ in self.installs)
                    and all(edge >= cycle for edge, _, _ in self.releases),
                    "weight pipeline cannot skip a live or scheduled edge")
        accepts = self._plan_accepts()
        fills = self._consume_skids(cycle)
        issues = self._physical_edge(cycle)
        self._replace_offers(issues)
        self._step_sources(cycle, accepts, fills)
        self._advance_ddr(cycle)
        self.cycle = cycle
        self.event_count = len(self.ddr.events)
        return tuple(fills)
