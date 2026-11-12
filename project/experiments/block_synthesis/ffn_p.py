"""Legal programmed FFN record admission and P-side command production."""
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto

from ffn_join import JoinController, Lane
from ffn_m import ALLOC, BEGIN, FILL, INPUT, RF
from ffn_m_issue import ALLOC_CMD, BEGIN_CMD, CONTEXT_CMD, EXEC_CMD, SIDE_WORDS, Command


class State(Enum):
    IDLE = auto()
    BEGIN_SEND = auto()
    BEGIN_WAIT = auto()
    CONTEXT_PUSH = auto()
    CONTEXT_SEND = auto()
    CONTEXT_WAIT = auto()
    ALLOC_SEND = auto()
    ALLOC_WAIT = auto()
    FILL_WAIT = auto()
    PAIR_ACCEPT = auto()
    W_JOIN = auto()
    EXEC_PUSH = auto()
    EXEC_ISSUE = auto()
    EXEC_WAIT = auto()
    A_CLOSE = auto()
    A_RELEASE = auto()
    COMPLETE = auto()


DIRECT = {State.BEGIN_SEND: (BEGIN_CMD, State.BEGIN_WAIT),
          State.CONTEXT_SEND: (CONTEXT_CMD, State.CONTEXT_WAIT),
          State.ALLOC_SEND: (ALLOC_CMD, State.ALLOC_WAIT)}
PREFETCH = {State.W_JOIN, State.EXEC_WAIT, State.COMPLETE}


@dataclass(slots=True)
class RecordController:
    lane: Lane
    state: State = State.IDLE
    next_record: int = 0
    completed: int = 0
    raw_valid: bool = False
    active: int | None = None
    partner: int | None = None
    preparing_second: bool = False
    first_pending: bool = False
    detached: int | None = None
    ahead: deque = field(default_factory=deque)
    ahead_sent: set = field(default_factory=set)
    ahead_offer: int | None = None
    pending_side: Command | None = None
    side_eop: int | None = None
    next_session: int = 1
    control_session: int = 0
    sides: list = field(default_factory=list)
    commands_seen: int = 0
    pushes_seen: int = 0
    executions_seen: int = 0

    @property
    def records(self):
        return self.lane.records

    def reply(self, source, index, tick):
        eop = self.lane.eops.get((source, self.records[index].sequence))
        return eop is not None and eop <= tick

    def control(self, source, tick):
        eop = self.lane.context_eops.get((source, self.control_session))
        return eop is not None and eop < tick

    def pair(self, index):
        record = self.records[index]
        if record.context % 2 or index + 1 == len(self.records):
            return False
        younger = self.records[index + 1]
        return (younger.scope, younger.k, younger.context) == (record.scope, record.k, record.context + 1)

    def finish_side(self, tick):
        if self.side_eop is None or self.side_eop >= tick:
            return
        self.control_session = self.pending_side.session
        self.next_session += 1
        self.pending_side = None
        self.side_eop = None
        if self.ahead_offer is not None:
            self.ahead_sent.add(self.ahead_offer)
            self.ahead_offer = None
        else:
            _, self.state = DIRECT[self.state]

    def offer_side(self, tick):
        if self.pending_side is not None:
            return ()
        index = self.ahead_offer
        if index is not None:
            opcode = ALLOC_CMD
        elif self.state in DIRECT:
            opcode, _ = DIRECT[self.state]
            index = self.active
        else:
            return ()
        sequence = self.records[index].sequence if opcode == ALLOC_CMD else 0
        self.pending_side = Command(tick, opcode, self.next_session, sequence, SIDE_WORDS[opcode])
        self.sides.append(self.pending_side)
        return (self.pending_side,)

    def advance(self, tick, windows, proofs, lookahead):
        self.finish_side(tick)
        side = self.offer_side(tick)
        while self.completed < self.next_record:
            retired = self.lane.retired.get(self.records[self.completed].sequence)
            if retired is None or retired >= tick:
                break
            self.completed += 1
        raw = self.next_record if self.raw_valid else None
        replay = bool(self.ahead)
        front = self.ahead[0] if replay else raw
        if replay and not self.reply(FILL, front, tick - 1):
            front = None
        record = self.records[front] if front is not None else None
        active = self.records[self.active] if self.active is not None else None
        accept = record is not None and (
            (self.state == State.IDLE and (record.context != 0 or windows[record.scope, record.k] <= tick))
            or (self.state == State.PAIR_ACCEPT and front == self.active + 1))

        # Both decisions use the registered queue before this edge's push/pop.
        offer = None
        if self.ahead_offer is None and (
                self.state in PREFETCH or (self.state == State.IDLE and front is None)
                or (self.state == State.FILL_WAIT and self.preparing_second)):
            offer = next((index for index in self.ahead if index not in self.ahead_sent), None)
        queue = (lookahead and raw is not None and len(self.ahead) < 2 and (replay or not accept)
                 and (self.preparing_second or self.first_pending or self.detached is not None)
                 and self.records[raw].scope == active.scope and self.records[raw].k == active.k
                 and active.k != 0 and self.records[raw].context != 0)
        join = self.advance_record(tick, front if accept else None, replay, proofs)
        if queue:
            self.ahead.append(raw)
        if queue or (accept and not replay):
            self.raw_valid = False
            self.next_record += 1
        elif raw is None and self.next_record < len(self.records):
            record = self.records[self.next_record]
            self.raw_valid = tick > record.dispatch and self.next_record - self.completed < 6
        if offer is not None:
            self.ahead_offer = offer
        if self.detached is not None and self.lane.retired.get(self.records[self.detached].sequence) == tick:
            self.detached = None
        return join, side

    def advance_record(self, tick, front, replay, proofs):
        if front is not None:
            if self.state == State.PAIR_ACCEPT:
                self.partner = self.active
                self.preparing_second = True
            self.active = front
            if replay:
                self.ahead.popleft()
                self.ahead_sent.remove(front)
                self.state = State.FILL_WAIT
            else:
                self.state = State.ALLOC_SEND if self.records[front].k else State.BEGIN_SEND
        elif self.state == State.BEGIN_WAIT and self.control(BEGIN, tick):
            self.state = State.CONTEXT_PUSH
        elif self.state == State.CONTEXT_PUSH:
            self.state = State.CONTEXT_SEND
        elif self.state == State.CONTEXT_WAIT and self.control(RF, tick):
            self.state = State.ALLOC_SEND
        elif self.state == State.ALLOC_WAIT and self.reply(ALLOC, self.active, tick - 1):
            self.state = State.FILL_WAIT
        elif self.state == State.FILL_WAIT:
            if not self.preparing_second and self.pair(self.active):
                self.state = State.PAIR_ACCEPT
            else:
                head = self.partner if self.preparing_second else self.active
                record = self.records[head]
                proof = proofs.get((record.scope, record.k))
                if proof is not None and proof < tick and self.reply(FILL, head, tick - 1):
                    if self.preparing_second:
                        self.active, self.partner = self.partner, self.active
                        self.preparing_second = False
                        self.first_pending = True
                    self.state = State.W_JOIN
        elif self.state == State.W_JOIN:
            intent = tick, self.records[self.active].sequence
            self.lane.joined.append(intent)
            self.state = State.EXEC_PUSH
            return (intent,)
        elif self.state == State.EXEC_WAIT:
            record = self.records[self.active]
            if self.first_pending and self.reply(INPUT, self.active, tick):
                self.detached, self.active = self.active, self.partner
                self.partner = None
                self.first_pending = False
                self.state = State.W_JOIN if self.reply(FILL, self.active, tick) else State.FILL_WAIT
            elif self.lane.retired.get(record.sequence) == tick + record.retire_delay:
                self.state = State.A_CLOSE if record.retire_delay == 3 else State.COMPLETE
        elif self.state == State.A_CLOSE:
            self.state = State.A_RELEASE
        elif self.state == State.A_RELEASE:
            self.state = State.COMPLETE
        elif self.state == State.COMPLETE and self.detached is None:
            self.state = State.IDLE
            self.active = None
        return ()

    def observe(self, trace):
        for tick, command in trace.commands[self.commands_seen:]:
            if command.opcode != EXEC_CMD:
                if command != self.pending_side or self.side_eop is not None:
                    raise ValueError('P side frame did not match its transmitter owner')
                self.side_eop = tick + command.words - 1
        self.commands_seen = len(trace.commands)
        for _, session, sequence in trace.pushes[self.pushes_seen:]:
            if (self.state != State.EXEC_PUSH or self.pending_side is not None
                    or (session, sequence) != (self.next_session, self.records[self.active].sequence)):
                raise ValueError('P EXEC reservation did not match its live record or session')
            self.next_session += 1
            self.state = State.EXEC_ISSUE
        self.pushes_seen = len(trace.pushes)
        for _, _, sequence in trace.executions[self.executions_seen:]:
            if self.state != State.EXEC_ISSUE or sequence != self.records[self.active].sequence:
                raise ValueError('P EXEC acceptance did not match its live record')
            self.state = State.EXEC_WAIT
        self.executions_seen = len(trace.executions)


class ProgrammedP(JoinController):
    """Generate side commands and bindings from range, A and M state."""

    def __init__(self, records, tiles, mode, *, lookahead, copy_delay_epoch):
        super().__init__(records, tiles, mode, lookahead=lookahead, copy_delay_epoch=copy_delay_epoch)
        # The fixture records header_cycle after taking the header DONE.
        # The P nodes see their registered window three edges earlier.
        self.windows = {(scope, k): header - 3 for scope, k, header, _ in tiles}
        self.dispatch = {p: RecordController(lane) for p, lane in self.lanes.items()}

    def advance(self, tick):
        self.publish_proofs(tick)
        joins, commands = {}, {}
        for p, state in self.dispatch.items():
            join, side = state.advance(tick, self.windows, self.proofs, self.lookahead)
            if join:
                joins[p] = join
            if side:
                commands[p] = side
        return joins, commands

    def observe(self, client, trace):
        super().observe(client, trace)
        self.dispatch[client].observe(trace)

    def validate(self):
        super().validate()
        for client, state in self.dispatch.items():
            if (state.state != State.IDLE or state.pending_side is not None or state.ahead
                    or state.completed != len(state.records)):
                raise ValueError(f'P{client} replay ended with a live range or side command')
