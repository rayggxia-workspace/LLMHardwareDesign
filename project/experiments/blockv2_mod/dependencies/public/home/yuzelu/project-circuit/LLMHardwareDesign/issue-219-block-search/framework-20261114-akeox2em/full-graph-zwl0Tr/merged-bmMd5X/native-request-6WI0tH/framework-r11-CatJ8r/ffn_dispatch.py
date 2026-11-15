"""Live scope admission, Gate/Up publication and Down readback."""
from collections import defaultdict

from event_replay import Operation, Phase, replay
from ffn_a import P_COUNT
from ffn_control import (DESCRIPTOR_CHECK_TICKS, DOWN_GROUPS, GATE_UP_COLUMNS, GATE_UP_STRIPES,
                         MID_COLUMNS, STRIPE_COLUMNS)
from ffn_mid import MidTile
from ffn_result import down_readback_words, mid_readback_words, readback_service
from ffn_scatter import scatter_service, stripe_fragments


def service_grants(service, tick):
    phases = tuple(Phase.from_spec(item['kind'], item['ticks'], item) for item in service['phases'])
    holds = tuple(service.get('hold_claims', {}).items())
    resources = {resource: 1 for phase in phases for resource, _ in phase.claims}
    resources.update(holds)
    grants, = replay((Operation(phases, release=tick, holds=holds),), resources)
    return grants


def readback_acks(words, mode, start):
    # The SRAM service exposes one request, pipeline edge and ACK per word.
    return [grant.start for grant in service_grants(readback_service(words, mode), start)[2::3]]


class ScopeAdmission:
    """Admit validated descriptors against live FFN producer and P readiness."""

    def __init__(self, start, mode, mother, p):
        self.mode = mode
        self.mother = mother
        self.p = p
        self.producing = self.admitting = 1
        self.mid_columns = 0
        self.done_at = None
        self.releases = {1: start + 4}
        self.producers = [('start', start + 1)]
        self.offers = {}
        self.offer_edges = defaultdict(list)
        self.dispatches = {}
        self.result = None
        self.write_bytes = sum(32 for lane in p.lanes.values() for record in lane.records if record.stores)

    def descriptor_returned(self, tick, client, owner):
        key = owner, client
        if key in self.offers:
            raise ValueError('scope descriptor completed twice')
        # CRC begins after the final DMA beat retires.
        ready = tick + 1 + DESCRIPTOR_CHECK_TICKS
        self.offers[key] = ready
        self.offer_edges[ready].append((client, owner))

    def advance_producers(self, tick):
        owner = self.producing
        if owner > GATE_UP_STRIPES + DOWN_GROUPS:
            return
        if self.done_at is None:
            ticks = [self.mother.done.get((owner, p)) for p in range(P_COUNT)]
            if None in ticks:
                return
            self.done_at = max(ticks)
        if tick < self.done_at:
            return
        done = self.done_at
        self.done_at = None
        self.producing += 1
        if owner > GATE_UP_STRIPES:
            self.producers.append(('down_done', done))
            if owner == GATE_UP_STRIPES + DOWN_GROUPS:
                acks = readback_acks(down_readback_words(DOWN_GROUPS, P_COUNT), self.mode, done + 1)
                self.result = acks[-1] + 1
            else:
                self.releases[owner + 1] = done + 1
            return

        first = STRIPE_COLUMNS * (owner - 1)
        width = min(STRIPE_COLUMNS, GATE_UP_COLUMNS - first)
        scatter = scatter_service(stripe_fragments(first, width), self.mode)
        published = service_grants(scatter, done + 1)[-1].start
        self.producers.append(('scatter', published))
        while self.mid_columns + MID_COLUMNS <= first + width:
            tile = MidTile(self.mode, self.mid_columns)
            published = tile.end(published + 2) - 1
            self.producers.append(('mid', published))
            self.mid_columns += MID_COLUMNS
        if owner == GATE_UP_STRIPES:
            words = mid_readback_words(GATE_UP_COLUMNS // MID_COLUMNS)
            acks = readback_acks(words, self.mode, published + 3)
            self.producers.extend(('mid_read', ack) for ack in acks)
            self.releases[owner + 1] = acks[-1] + 2
        else:
            self.releases[owner + 1] = published + 3

    def advance(self, tick):
        self.advance_producers(tick)
        offers = self.offer_edges.pop(tick, ())
        owner = self.admitting
        release = self.releases.get(owner)
        if release is None or tick < release:
            return offers, ()
        waiting = [p for p in range(P_COUNT) if (owner, p) not in self.dispatches]
        ready = [p for p in waiting
                 if self.offers.get((owner, p), tick + 1) <= tick
                 and self.p.scope_ready(p, owner, tick, self.mother.done)]
        if owner > GATE_UP_STRIPES and len(ready) != len(waiting):
            return offers, ()
        for p in ready:
            self.p.admit(p, owner, tick)
            self.dispatches[owner, p] = tick
        if len(ready) == len(waiting):
            self.admitting += 1
        return offers, tuple((p, owner) for p in ready)

    def validate(self):
        total = GATE_UP_STRIPES + DOWN_GROUPS
        if (self.admitting != total + 1 or self.producing != total + 1 or self.offer_edges
                or len(self.dispatches) != total * P_COUNT or self.result is None):
            raise ValueError('scope admission stopped before the FFN retired')
