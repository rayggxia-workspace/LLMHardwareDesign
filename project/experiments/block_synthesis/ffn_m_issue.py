"""Command receiver and weight-bank ownership for one #251 P/M pair."""

from collections import deque
from dataclasses import dataclass
from heapq import heappop, heappush

from ffn_m import ALLOC, BEGIN, FILL, INPUT, RF, REPLY_PRIORITY, Reply, execution_replies


BEGIN_CMD, ALLOC_CMD, EXEC_CMD, CONTEXT_CMD = 1, 2, 3, 4
SIDE_WORDS = {BEGIN_CMD: 8, ALLOC_CMD: 2, CONTEXT_CMD: 1}


@dataclass(frozen=True, slots=True)
class Command:
    ready: int
    opcode: int
    session: int
    sequence: int
    words: int


def join_schedule(records, proofs, eops, retirements, *, lookahead):
    """Schedule each A/W binding from registered P record and bank readiness."""
    joins = []
    for index, record in enumerate(records):
        sequence = record.sequence
        fill = eops[FILL, sequence]
        proof = proofs[record.scope, record.k]
        if record.context % 2:
            # The older record hands over at INPUT EOP. A younger FILL
            # accepted on that same edge can enter W_JOIN immediately.
            older_input = eops[INPUT, records[index - 1].sequence]
            tick = older_input + 1 if fill <= older_input else fill + 2
        else:
            tick = max(proof, fill) + 2
            younger = records[index + 1] if index + 1 < len(records) else None
            paired = (younger is not None and younger.scope == record.scope and younger.k == record.k
                      and younger.context == record.context + 1)
            if lookahead and record.k and record.context:
                # A filled queue head must become front before the two
                # records can be restored. The prior pair also has to retire.
                prior = retirements[records[index - 1].sequence]
                tick = max(tick, max(prior, fill) + (5 if paired else 3))
                if paired:
                    tick = max(tick, eops[FILL, younger.sequence] + 3)
            elif paired:
                # A direct pair waits for the second ALLOC acknowledgement
                # before restoring the older record, even if its W is ready.
                tick = max(tick, eops[ALLOC, younger.sequence] + 2)
        joins.append((tick, sequence))
    return joins


@dataclass(slots=True)
class IssueTrace:
    pushes: list
    commands: list
    allocations: list
    bank_acks: list
    executions: list
    controls: list
    replies: list
    bank_waits: set
    alloc_ack_waits: set


class CommandLink:
    """Replay independent command and reply wires with registered owner release."""

    def __init__(self, stores):
        self.stores = stores
        self.events = []
        self.serial = 0
        self.trace = IssueTrace([], [], [], [], [], [], [], set(), set())
        self.join = deque()
        self.side = deque()
        self.exec = deque()
        self.reply = []
        self.rx = None
        self.rx_open = self.tx_open = self.exec_open = 0
        self.prefer_exec = False
        self.begin_pending = self.alloc_pending = False
        self.last_session = 0
        self.last_reserved = 0
        self.side_open = 0
        self.banks = [None] * 4
        self.generation = [0] * 4
        self.cursor = 0
        self.owner_bank = {}
        self.alloc_acked = {}
        self.fill_seen = set()
        self.weight_ready = set()
        self.input_live = set()
        self.rf_live = set()
        self.clock = 0
        self.resume = None

    def schedule(self, tick, event, payload):
        heappush(self.events, (tick, self.serial, event, payload))
        self.serial += 1

    def ready_reply(self, reply):
        heappush(self.reply, (REPLY_PRIORITY[reply.source], reply.ready, self.serial, reply))
        self.serial += 1

    def control(self, tick, source, session, sequence):
        reply = Reply(tick, source, session, sequence, 2)
        self.trace.controls.append(reply)
        self.schedule(tick, 'reply', reply)

    def release_reply(self, reply, tick):
        if reply.source == BEGIN:
            self.begin_pending = False
        elif reply.source == ALLOC:
            self.alloc_pending = False
            self.alloc_acked[reply.sequence] = reply.session
        elif reply.source == FILL:
            self.weight_ready.add(reply.sequence)
        elif reply.source == INPUT:
            sequence = reply.sequence
            self.banks[self.owner_bank.pop(sequence)] = None
            del self.alloc_acked[sequence]
            self.weight_ready.remove(sequence)
            self.input_live.remove(sequence)
            self.exec_open = tick + 1
        elif reply.sequence:
            self.rf_live.remove(reply.sequence)

    def arrive(self, tick, event, payload):
        if event == 'side':
            self.side.append(payload)
        elif event == 'join':
            self.join.append(payload)
        elif event == 'exec':
            self.exec.append(payload)
        elif event == 'fill':
            if self.alloc_acked.get(payload.sequence) != payload.session or payload.sequence in self.fill_seen:
                raise ValueError('M FILL appeared without a matching ALLOC acknowledgement')
            self.fill_seen.add(payload.sequence)
            self.trace.controls.append(payload)
            self.ready_reply(payload)
        elif event == 'reply':
            self.ready_reply(payload)
        else:
            self.release_reply(payload, tick)

    def accept(self, tick):
        command, earliest = self.rx
        if tick < earliest:
            return
        opcode, session, sequence = command.opcode, command.session, command.sequence
        if opcode == ALLOC_CMD:
            if all(owner is not None for owner in self.banks):
                self.trace.bank_waits.add(sequence)
                return
            if self.alloc_pending:
                self.trace.alloc_ack_waits.add(sequence)
                return
            free = sum(1 << i for i, owner in enumerate(self.banks) if owner is None)
            bank = next((self.cursor + i) % 4 for i in range(4) if self.banks[(self.cursor + i) % 4] is None)
            if sequence in self.owner_bank:
                raise ValueError('M ALLOC duplicated a live W owner')
            self.banks[bank] = sequence
            self.owner_bank[sequence] = bank
            self.generation[bank] += 1
            self.cursor = (bank + 1) % 4
            self.alloc_pending = True
            self.trace.allocations.append((tick, session, sequence, free))
            self.trace.bank_acks.append((tick + 1, session, sequence, bank, self.generation[bank]))
            self.control(tick + 1, ALLOC, session, sequence)
        elif opcode == BEGIN_CMD:
            self.begin_pending = True
            self.control(tick + 1, BEGIN, session, sequence)
        elif opcode == CONTEXT_CMD:
            if self.input_live or self.rf_live:
                return
            self.control(tick + 1, RF, session, sequence)
        else:
            if sequence not in self.weight_ready:
                raise ValueError('M EXEC arrived before its own W FILL EOP')
            if self.input_live or len(self.rf_live) >= 2:
                return
            self.trace.executions.append((tick, session, sequence))
            self.input_live.add(sequence)
            self.rf_live.add(sequence)
            for reply in execution_replies(tick, session, sequence, self.stores[sequence]):
                self.schedule(reply.ready, 'reply', reply)
        self.rx = None
        self.rx_open = tick + 1

    def offer_command(self, tick):
        exec_ready = bool(self.exec and self.exec_open is not None and tick >= self.exec_open)
        choose_exec = exec_ready and (not self.side or self.prefer_exec)
        if choose_exec:
            command = self.exec.popleft()
            self.exec_open = None
        elif self.side:
            command = self.side.popleft()
        else:
            return
        if command.session != self.last_session + 1:
            raise ValueError('M command session skipped, reused, or overtaken')
        self.last_session = command.session
        self.prefer_exec = not choose_exec
        self.trace.commands.append((tick, command))
        self.rx = command, tick + command.words
        if not choose_exec:
            self.side_open = tick + command.words

    def run(self, joins, side, fills, *, until=None):
        """Optionally stop just before an edge, retaining both wires and their owners."""
        joins, side, fills = tuple(joins), tuple(side), tuple(fills)
        if ((until is not None and until < self.clock)
                or any(tick < self.clock for tick, _ in joins)
                or any(command.ready < self.clock for command in side)
                or any(reply.ready < self.clock for reply in fills)):
            raise ValueError('M intent predates the command-link snapshot')
        for tick, sequence in joins:
            self.schedule(tick + 1, 'join', sequence)
        for command in side:
            self.schedule(command.ready, 'side', command)
        for reply in fills:
            self.schedule(reply.ready, 'fill', reply)
        future = [self.events[0][0]] if self.events else []
        if self.resume is not None:
            future.append(self.resume)
        self.resume = None
        tick = min(future, default=self.clock)
        while self.events or self.join or self.side or self.exec or self.reply or self.rx:
            if until is not None and tick >= until:
                self.clock = until
                self.resume = tick
                return self.trace
            self.clock = tick
            while self.events and self.events[0][0] == tick:
                _, _, event, payload = heappop(self.events)
                self.arrive(tick, event, payload)
            if self.rx:
                self.accept(tick)
            if self.reply and tick >= self.tx_open:
                _, _, _, reply = heappop(self.reply)
                self.trace.replies.append((tick, reply))
                self.tx_open = tick + reply.words + 1
                self.schedule(self.tx_open, 'release reply', reply)
            if self.join and not self.side and tick >= self.side_open:
                sequence = self.join.popleft()
                session = max(self.last_session, self.last_reserved) + 1
                self.last_reserved = session
                self.trace.pushes.append((tick, session, sequence))
                self.schedule(tick + 2, 'exec', Command(tick + 2, EXEC_CMD, session, sequence, 2))
            if not self.rx and not self.begin_pending and tick >= self.rx_open:
                self.offer_command(tick)

            future = [self.events[0][0]] if self.events else []
            if self.rx and self.rx[1] > tick:
                future.append(self.rx[1])
            if self.reply and self.tx_open > tick:
                future.append(self.tx_open)
            if self.join and not self.side and self.side_open > tick:
                future.append(self.side_open)
            if not self.rx and not self.begin_pending:
                if self.side and self.rx_open > tick:
                    future.append(self.rx_open)
                if self.exec and self.exec_open is not None:
                    opens = max(self.rx_open, self.exec_open)
                    if opens > tick:
                        future.append(opens)
            if not future:
                if self.rx or self.join or self.side or self.exec or self.reply:
                    raise ValueError('M command or reply deadlocked with a live owner')
                self.clock = tick + 1
                break
            tick = min(future)
        if until is not None:
            self.clock = until
            return self.trace
        if self.owner_bank or self.alloc_acked or self.input_live or self.rf_live:
            raise ValueError('M completed with a live W or execution owner')
        return self.trace
