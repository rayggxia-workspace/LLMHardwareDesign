"""Receipts at the W DMA client boundary of the programmed FFN."""
from collections import defaultdict
from dataclasses import dataclass

from ffn_m_issue import WeightCompletion


BEATS = 17
RECORD_MASK = (1 << BEATS) - 1


@dataclass(slots=True)
class Record:
    tick: int
    session: int
    sequence: int
    address: int
    sent: int = 0
    last_request: int = -1
    epoch: int | None = None
    received: int = 0


class WeightTrace:
    """Rebuild completed W records from the installation and beat handshakes."""

    def __init__(self):
        self.records = {}
        self.installs = defaultdict(list)
        self.filled = defaultdict(list)
        self.completed = defaultdict(list)
        self.ticks = [-1] * 3

    def record(self, kind, tick, client, *fields):
        if not 0 <= client < 3:
            raise ValueError(f'invalid W client P{client}')
        if tick < self.ticks[client]:
            raise ValueError(f'W events went backward at tick {tick}')
        self.ticks[client] = tick
        if kind == 'install':
            session, sequence, bank, generation, address = fields
            key = client, bank, generation
            if key in self.records or not 0 <= bank < 4 or not 0 < generation < 65536 or address < 0 or address % 64:
                raise ValueError(f'invalid W bank install {key}')
            self.records[key] = Record(tick, session, sequence, address)
            self.installs[client].append((tick, session, sequence, bank, generation))
        elif kind == 'filled':
            self.filled[client].append((tick, *fields))
        else:
            self.beat(kind, tick, client, fields)

    def beat(self, kind, tick, client, fields):
        tag = fields[-1]
        epoch, bank, generation, beat = tag >> 23, (tag >> 21) & 3, (tag >> 5) & 65535, tag & 31
        record = self.records.get((client, bank, generation))
        if (record is None or not 0 <= tag < 1 << 32 or tick <= record.tick
                or beat >= BEATS or record.epoch not in (None, epoch)):
            raise ValueError(f'W {kind} did not match a live bank at tick {tick}')
        if kind == 'request':
            address, _ = fields
            if beat != record.sent or address != record.address + 64 * beat:
                raise ValueError(f'W request address or beat differs at tick {tick}')
            record.sent += 1
            record.last_request = tick
            record.epoch = epoch
            return
        bit = 1 << beat
        if beat >= record.sent or (beat == record.sent - 1 and tick == record.last_request) or record.received & bit:
            raise ValueError(f'W return was unissued or repeated at tick {tick}')
        record.received |= bit
        if record.received == RECORD_MASK:
            self.completed[client].append(WeightCompletion(tick + 1, record.session, record.sequence, bank, generation))

    def validate(self):
        if not self.records or any(record.received != RECORD_MASK for record in self.records.values()):
            raise ValueError('W beat receipt coverage differs')
