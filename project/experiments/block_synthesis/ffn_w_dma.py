"""Live W clients sharing the programmed FFN descriptor and DDR fabric."""
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from dma_read import Profile, Read, ReadEdge, ReadFabric, ReadRecord
from ffn_m_issue import WeightCompletion
from ffn_w import BEATS


@dataclass(frozen=True, slots=True)
class WeightOwner:
    client: int
    session: int
    sequence: int
    bank: int
    generation: int


@dataclass(slots=True)
class WeightPort:
    banks: list = field(default_factory=lambda: [None] * 4)
    cursor: int = 0
    locked: ReadRecord | None = None
    offered_at: int = -1
    outstanding: int = 0

    def advance(self, tick, accepted, returned):
        if accepted:
            self.cursor = (self.locked.key.bank + 1) % 4
            self.locked = None
        # The request register reserves a credit against the old count.
        # A response on this edge only changes next edge's count.
        if self.locked is None and self.outstanding + accepted < 32:
            for offset in range(4):
                record = self.banks[(self.cursor + offset) % 4]
                if record is not None and record.sent < record.length:
                    self.locked = record
                    self.offered_at = tick + 1
                    break
        self.outstanding += accepted - returned


def local_tag(record, address):
    beat = (address - record.address) // 64
    if record.client < 9:
        return 2 * record.key[1] + beat
    return (record.key.bank << 21) | (record.key.generation << 5) | beat


class WeightDma:
    """A cycle step with bank installs and descriptor starts as its inputs."""

    def __init__(self, profile):
        self.fabric = ReadFabric(profile)
        self.ports = [WeightPort() for _ in range(3)]

    def submit_descriptor(self, client, serial, address):
        self.fabric.submit((client, serial), Read(client, address, 128, 2))

    def step(self, tick, installs):
        edge = ReadEdge({p + 9: port.locked for p, port in enumerate(self.ports) if port.locked is not None})
        completed = self.fabric.advance(tick, edge=edge)
        accepted = {record.client for record, _, _ in edge.accepted}
        delivered = {record.client for record, _ in edge.delivered}
        for p, port in enumerate(self.ports):
            port.advance(tick, p + 9 in accepted, p + 9 in delivered)
        for p, session, sequence, bank, generation, address in installs:
            if not 0 <= p < len(self.ports) or not 0 <= bank < 4:
                raise ValueError('invalid W DMA client or bank')
            port = self.ports[p]
            old = port.banks[bank]
            if old is not None and old.returned != old.length:
                raise ValueError('W bank installed over unread data')
            if generation != (1 if old is None else old.key.generation + 1):
                raise ValueError('invalid W DMA bank generation')
            key = WeightOwner(p, session, sequence, bank, generation)
            port.banks[bank] = self.fabric.open_native(key, Read(p + 9, address, BEATS * 64, BEATS))
        return edge, completed


class WeightCommandLinks:
    """Join P/M allocation and reply state to the shared W DMA edges."""

    def __init__(self, links, addresses):
        self.links = links
        self.addresses = addresses
        self.installs = defaultdict(list)
        self.ready = defaultdict(list)

    def advance(self, tick):
        installs = self.installs.pop(tick, ())
        for client, link in self.links.items():
            ready = self.ready.pop(client, ())
            if not ready and (link.resume is None or link.resume > tick):
                continue
            before = len(link.trace.bank_acks)
            trace = link.run((), (), (), until=tick + 1, weight_completions=ready)
            for edge, session, sequence, bank, generation in trace.bank_acks[before:]:
                if edge != tick + 1:
                    raise ValueError('W bank install was not produced at its registered edge')
                self.installs[edge].append((client, session, sequence, bank, generation,
                                            self.addresses[client][sequence]))
        return installs

    def complete(self, client, weight):
        self.ready[client].append(weight)

    def finish(self):
        if self.ready or self.installs:
            raise ValueError('W DMA and M link have pending handshakes')
        return {client: link.run((), (), ()) for client, link in self.links.items()}


class WeightDmaTrace:
    """Compare each modeled edge against both ends of the physical fabric."""

    def __init__(self, mode, seed, call_to_fetch, *, links=None):
        self.service = WeightDma(Profile.from_spec({'ffn_provider': {'mode': mode, 'seed': seed}}))
        self.call_to_fetch = call_to_fetch
        self.links = links
        self.issue = None
        self.descriptors = defaultdict(list)
        self.serial = [0] * 3
        self.call_count = 0
        self.installs = defaultdict(list)
        self.filled = defaultdict(list)
        self.completed = defaultdict(list)
        self.edge_events = defaultdict(list)
        self.clock = None
        self.global_tags = [0] * 64
        self.entry_serials = [0] * 64
        self.counts = Counter()

    def record(self, kind, tick, *fields):
        if self.clock is None:
            self.clock = tick
        if tick < self.clock:
            raise ValueError(f'DMA trace went backward at tick {tick}')
        while self.clock < tick:
            self.verify_edge()
            self.clock += 1
        if kind == 'call':
            p, = fields
            self.serial[p] += 1
            address = 4096 + 128 * self.call_count
            self.call_count += 1
            self.descriptors[tick + self.call_to_fetch].append((p, self.serial[p], address))
        elif kind == 'filled':
            p, *identity = fields
            self.filled[p].append((tick, *identity))
        elif kind != 'result':
            self.edge_events[kind].append(fields)

    def verify_edge(self):
        tick = self.clock
        if self.links is not None:
            installs = self.links.advance(tick)
        else:
            installs = self.edge_events.pop('install', ())
        if not installs and not self.edge_events and not self.service.fabric.active and tick not in self.descriptors:
            return
        for descriptor in self.descriptors.pop(tick, ()):
            self.service.submit_descriptor(*descriptor)
        expected = defaultdict(list)
        for p, port in enumerate(self.service.ports):
            if port.offered_at == tick:
                record = port.locked
                address = record.address + 64 * record.sent
                expected['offer'].append((p, address, local_tag(record, address), record.channel, BEATS))
        if self.links is not None:
            expected['install'].extend(installs)
        for p, session, sequence, bank, generation, _ in installs:
            self.installs[p].append((tick, session, sequence, bank, generation))
        edge, completed = self.service.step(tick, installs)
        expected['backend_req'].extend((lane, address, self.global_tags[entry]) for lane, address, entry in edge.issued)
        expected['backend_rsp'].extend((lane, self.global_tags[entry]) for lane, entry in edge.captured)
        for record, address, entry in edge.accepted:
            tag = local_tag(record, address)
            if record.client < 9:
                expected['fetch'].append((record.client, tag, address))
            else:
                expected['request'].append((record.client - 9, address, tag))
            self.entry_serials[entry] += 1
            # The fixture completes its reset purge before the first CALL.
            self.global_tags[entry] = (2 << 32) | (self.entry_serials[entry] << 16) | (entry << 10) | (record.client << 6)
        for record, address in edge.delivered:
            tag = local_tag(record, address)
            if record.client < 9:
                expected['fetch_return'].append((record.client, tag))
            else:
                expected['returned'].append((record.client - 9, tag))
        for owner, _ in completed:
            if isinstance(owner, WeightOwner):
                completion = WeightCompletion(tick + 1, owner.session, owner.sequence, owner.bank, owner.generation)
                self.completed[owner.client].append(completion)
                if self.links is not None:
                    self.links.complete(owner.client, completion)
        for kind in expected.keys() | self.edge_events.keys():
            wanted = sorted(expected[kind])
            observed = sorted(self.edge_events.get(kind, ()))
            if wanted != observed:
                raise ValueError(f'DMA {kind} differs at tick {tick}, replay {wanted}, trace {observed}')
            self.counts[kind] += len(wanted)
        self.edge_events.clear()

    def validate(self):
        if self.clock is None:
            raise ValueError('missing shared W DMA trace')
        self.verify_edge()
        if self.descriptors or self.service.fabric.active or not self.counts['returned']:
            raise ValueError('shared W DMA trace did not retire every record')
        if self.links is not None:
            self.issue = self.links.finish()
