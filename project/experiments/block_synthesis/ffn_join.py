"""Drive programmed FFN bindings from live A proofs and M replies."""
from collections import defaultdict
from dataclasses import dataclass, field

from ffn_a import P_COUNT, replay_tile
from ffn_m import ALLOC, FILL, INPUT, RF, replay_commits
from ffn_m_issue import join_tick


@dataclass(slots=True)
class Lane:
    records: list
    joined: list = field(default_factory=list)
    retired: dict = field(default_factory=dict)
    eops: dict = field(default_factory=dict)
    replies_seen: int = 0
    next_retire: int = 0
    guard_end: int = 0


class JoinController:
    """The A/W binding cursor and the P record ownership that feeds it."""

    def __init__(self, records, tiles, mode, *, lookahead, copy_delay_epoch):
        self.lanes = {p: Lane(rows) for p, rows in records.items()}
        self.tiles = tiles
        self.mode = mode
        self.lookahead = lookahead
        self.copy_delay_epoch = copy_delay_epoch
        self.tile_cursor = 0
        self.generations = [0, 0]
        self.proofs = {}
        self.last = defaultdict(dict)
        for p, lane in self.lanes.items():
            for record in lane.records:
                self.last[record.scope, record.k][p] = record.sequence

    def observe(self, client, replies):
        lane = self.lanes[client]
        for tick, reply in replies[lane.replies_seen:]:
            if reply.sequence and reply.source in (ALLOC, FILL, INPUT, RF):
                lane.eops[reply.source, reply.sequence] = tick + reply.words
        lane.replies_seen = len(replies)
        while lane.next_retire < len(lane.records):
            record = lane.records[lane.next_retire]
            eop = lane.eops.get((RF, record.sequence))
            if eop is None:
                break
            # The guard is ordered. Its next operation cannot reserve SRAM
            # until the prior head has released the terminal phase.
            commit, = replay_commits(client, self.mode, [(max(eop, lane.guard_end - 1), record.stores)])
            lane.guard_end = commit[-1].end
            lane.retired[record.sequence] = commit[-1].start + record.retire_delay
            lane.next_retire += 1

    def publish_proofs(self, tick):
        while self.tile_cursor < len(self.tiles):
            scope, k, header, down = self.tiles[self.tile_cursor]
            if tick < header:
                break
            loads = [header - 2] * P_COUNT
            if k:
                previous = self.last[scope, k - 128]
                if any(sequence not in self.lanes[p].retired for p, sequence in previous.items()):
                    break
                loads = [max(header - 2, self.lanes[p].retired[previous[p]] + 2) for p in range(P_COUNT)]
            epoch = self.tile_cursor + 1
            slot = (k // 128) % 2
            self.generations[slot] += 1
            start = header + int(epoch == self.copy_delay_epoch)
            _, proof = replay_tile(self.mode, start, scope, k, epoch, epoch, loads, self.generations[slot], down=down)
            if proof < tick:
                raise ValueError(f'A proof became known after its own acceptance in scope {scope}, K={k}')
            self.proofs[scope, k] = proof
            self.tile_cursor += 1

    def advance(self, tick):
        self.publish_proofs(tick)
        launches = {}
        for p, lane in self.lanes.items():
            index = len(lane.joined)
            if index == len(lane.records):
                continue
            try:
                ready = join_tick(lane.records, index, self.proofs, lane.eops, lane.retired, lookahead=self.lookahead)
            except KeyError:
                continue
            if ready < tick:
                raise ValueError(f'P{p} binding became known after its acceptance at tick {ready}')
            if ready == tick:
                intent = tick, lane.records[index].sequence
                lane.joined.append(intent)
                launches[p] = (intent,)
        return launches

    def validate(self):
        if self.tile_cursor != len(self.tiles):
            raise ValueError('live A proof did not cover every K tile')
        for client, lane in self.lanes.items():
            if len(lane.joined) != len(lane.records) or lane.next_retire != len(lane.records):
                raise ValueError(f'P{client} live A/W binding or retirement did not cover every record')
