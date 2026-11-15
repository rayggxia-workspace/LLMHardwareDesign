"""Timing of the isolated #251 Gate/Up activation and known-shift Mid pack."""
from collections import deque
from dataclasses import dataclass
from functools import lru_cache

from ffn_scatter import s_pressure


MIN_TICKS = 144  # Two G commands and one pack issue 48 serialized S requests each.


def ready(tick, client, mode, *, response=False):
    if not mode:
        return True
    gate = s_pressure(client, response)
    return (tick + gate['offset']) % gate['period'] >= gate['closed']


@dataclass(frozen=True)
class SRequest:
    kind: int
    word: int
    client: int = 0


class SPort:
    """Two ordered owner entries shared by the local adapter/router."""
    def __init__(self, mode):
        self.mode = mode
        self.owners = deque()

    def returning(self, tick):
        if self.owners:
            available, request = self.owners[0]
            if available <= tick and ready(tick, request.client, self.mode, response=True):
                return request
        return None

    def space(self, returning):
        return len(self.owners) < 2 or returning is not None

    def advance(self, tick, issued, returning):
        if returning is not None:
            self.owners.popleft()
        if issued is not None:
            self.owners.append((tick + 2, issued))


def g_run(start, mode, first, gate, up, mid, events):
    events.append(('g_start', start, first, gate, up, mid))
    s = SPort(mode)
    read_word = input_packets = output_packets = write_word = committed = 0
    phase = 0
    held = None
    input_busy, gate_returned, up_returned = set(), set(), set()
    output_busy, output_ready = set(), set()
    pipeline = [False] * 4

    for tick in range(start + 1, start + 1024):
        returning = s.returning(tick)
        read_slot = read_word % 2
        write_slot = write_word % 2
        input_slot = (input_packets // 2) % 2
        output_slot = (output_packets // 2) % 2
        out_ready = output_slot not in output_busy or output_packets % 2 == 1
        stages_ready = [False] * 4
        next_ready = out_ready
        for index in reversed(range(4)):
            next_ready = not pipeline[index] or next_ready
            stages_ready[index] = next_ready
        sending = (input_packets < 32 and stages_ready[0]
                   and input_slot in gate_returned and input_slot in up_returned)
        receiving = pipeline[-1] and out_ready

        request = held
        if request is None and s.space(returning):
            if phase == 0 and read_word < 16 and read_slot not in input_busy:
                request = SRequest(0, read_word)
            elif phase == 1 and read_word < 16 and read_slot in input_busy and read_slot not in up_returned:
                request = SRequest(1, read_word)
            elif phase == 2 and write_word < 16 and write_slot in output_ready:
                request = SRequest(2, write_word)
        issued = request if ready(tick, 0, mode) else None
        held = request if issued is None else None
        if held is None:
            phase = (phase + 1) % 3
        if issued is not None:
            events.append(('g_req', tick, int(issued.kind == 2), (gate, up, mid)[issued.kind] + issued.word))
            if issued.kind == 0:
                input_busy.add(read_slot)
            elif issued.kind == 1:
                read_word += 1
            else:
                output_ready.remove(write_slot)
                write_word += 1
        if returning is not None:
            events.append(('g_rsp', tick))
            slot = returning.word % 2
            if returning.kind == 0:
                gate_returned.add(slot)
            elif returning.kind == 1:
                up_returned.add(slot)
            else:
                output_busy.remove(slot)
                committed += 1
        if sending:
            events.append(('g_in', tick))
            if input_packets % 2:
                input_busy.remove(input_slot)
                gate_returned.remove(input_slot)
                up_returned.remove(input_slot)
            input_packets += 1
        if receiving:
            events.append(('g_out', tick))
            output_busy.add(output_slot)
            if output_packets % 2:
                output_ready.add(output_slot)
            output_packets += 1
        for index in reversed(range(4)):
            if stages_ready[index]:
                pipeline[index] = pipeline[index - 1] if index else sending
        s.advance(tick, issued, returning)
        if committed == 16:
            done = tick + 1
            events.append(('g_done', done))
            return done
    raise ValueError('FFN G service failed to drain')


def q_run(start, mode, first, destination, base, events):
    events.append(('q_start', start, first, destination, base))
    s = SPort(mode)
    reads = writes = committed = 0
    allocated, write_pending = set(), set()
    returned = [0, 0]
    generation = first // 128 + 1
    held = None

    def tag(request):
        return (generation << 16) | (request.kind << 14) | (request.word << 8)

    for tick in range(start + 1, start + 1024):
        returning = s.returning(tick)
        write_slot = writes % 2
        read_slot = (reads // 2) % 2
        request = held
        if request is None and s.space(returning):
            if writes < 16 and returned[write_slot] == 3 and write_slot not in write_pending:
                request = SRequest(3, writes, destination)
            elif reads < 32 and (reads % 2 or read_slot not in allocated):
                request = SRequest(2, reads)
        issued = request if request is not None and ready(tick, request.client, mode) else None
        held = request if issued is None else None
        if issued is not None:
            write = issued.kind == 3
            events.append(('q_req', tick, int(write), (base if write else 848) + issued.word, tag(issued)))
            if write:
                writes += 1
                write_pending.add(write_slot)
            else:
                if reads % 2 == 0:
                    allocated.add(read_slot)
                reads += 1
        if returning is not None:
            events.append(('q_rsp', tick, tag(returning)))
            if returning.kind == 3:
                slot = returning.word % 2
                allocated.remove(slot)
                write_pending.remove(slot)
                returned[slot] = 0
                committed += 1
            else:
                slot = (returning.word // 2) % 2
                returned[slot] |= 1 << (returning.word % 2)
        s.advance(tick, issued, returning)
        if committed == 16:
            # DONE is valid after the last write ACK and drain. The
            # directory publishes it at the first fixture READY edge.
            done = tick + 2
            if mode:
                done += max(0, 4 - done % 13)
            events.append(('q_done', done, committed))
            return done
    raise ValueError('FFN Mid quantizer failed to drain')


@dataclass(frozen=True)
class MidTile:
    mode: int
    first: int

    @classmethod
    def from_spec(cls, spec):
        if not isinstance(spec, dict) or spec.keys() != {'mode', 'first'}:
            raise ValueError('invalid FFN Mid tile')
        tile = cls(**spec)
        if not tile.valid():
            raise ValueError('invalid FFN Mid tile')
        return tile

    def valid(self):
        return (type(self.mode) is int and self.mode in (0, 1) and type(self.first) is int
                and 0 <= self.first < 11008 and self.first % 128 == 0)

    @property
    def destination(self):
        return (self.first // 128) % 3

    @property
    def destination_base(self):
        return 256 + 16 * (self.first // (128 * 3))

    def input_words(self):
        offset = (self.first % 256) // 4
        return {(0, base + offset + word) for base in (720, 784) for word in range(32)}

    def output_words(self):
        return {(self.destination, self.destination_base + word) for word in range(16)}

    def claims(self):
        resources = {'G', 'Mid.quant'}
        for client in (0, self.destination):
            resources.update((f'P{client}.S.request', f'P{client}.S.response'))
        return dict.fromkeys(sorted(resources), 1)

    def end(self, start):
        # The fixture readiness patterns repeat every 7*11*13 cycles.
        residue = start % 1001 if self.mode else 0
        return start + duration(self, residue)

    def run(self, start):
        events = []
        tick = start
        for half in range(2):
            offset = (self.first % 256) // 4 + 16 * half
            done = g_run(tick, self.mode, self.first, 720 + offset, 784 + offset, 848 + 16 * half, events)
            tick = done + 1
        commit = q_run(tick, self.mode, self.first, self.destination, self.destination_base, events)
        return commit + 1, tuple(events)


@lru_cache(maxsize=4096)
def duration(tile, residue):
    return tile.run(residue)[0] - residue
