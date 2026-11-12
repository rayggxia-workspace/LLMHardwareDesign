"""Timing of the accepted K128 EXEC and its replies in the #251 FFN."""

from dataclasses import dataclass

from event_replay import Operation, Phase, replay
from ffn_result import sram_word_phases


# Eight consecutive K16 operands, three raw pipeline edges, and three
# scale/accumulate edges. INPUT becomes ready after the last operand.
FIRST_OPERAND = 1
LAST_OPERAND = 8
RAW_READY = LAST_OPERAND + 3
INPUT_READY = LAST_OPERAND + 1
RF_READY = RAW_READY + 3
ALLOC = 1
FILL = 2
INPUT = 3
RF = 4
BEGIN = 11
REPLY_PRIORITY = {source: priority for priority, source in enumerate((BEGIN, 9, INPUT, RF, ALLOC, FILL))}


@dataclass(frozen=True, slots=True)
class Reply:
    ready: int
    source: int
    session: int
    sequence: int
    words: int


@dataclass(frozen=True, slots=True)
class Record:
    sequence: int
    dispatch: int
    scope: int
    k: int
    context: int
    stores: bool
    retire_delay: int


def execution_replies(start, session, sequence, stores):
    return (Reply(start + INPUT_READY, INPUT, session, sequence, 2),
            Reply(start + RF_READY, RF, session, sequence, 4 if stores else 2))


def reply_phase(client, source, words):
    # Selection registers the frame; its first flit transfers the following
    # edge. The output mux cannot select the next owner until after EOP.
    return Phase('reply frame', words + 1, ((f'P{client}.M.reply', 1),), REPLY_PRIORITY[source])


def replay_replies(client, intents):
    operations = [Operation((reply_phase(client, reply.source, reply.words),), release=reply.ready)
                  for reply in intents]
    grants = replay(operations, {f'P{client}.M.reply': 1})
    return sorted(((grant[0].start, reply) for grant, reply in zip(grants, intents)), key=lambda item: item[0])


def commit_phases(client, mode, stores):
    store = tuple(Phase.from_spec(phase['kind'], phase['ticks'], phase)
                  for word in range(2)
                  for phase in sram_word_phases(client, mode, f'word{word}')) if stores else ()
    return (Phase('select guard head', 1), *store, Phase('retire guard head', 1))


def replay_commits(client, mode, records):
    """Release each guard slot only after its own matched terminal ACK."""
    phases = {stores: commit_phases(client, mode, stores) for stores in (False, True)}
    operations = [Operation(phases[stores], after=frozenset({index - 1}) if index else frozenset(),
                            release=rf_eop + 1)
                  for index, (rf_eop, stores) in enumerate(records)]
    ports = {f'P{client}.S.request': 1, f'P{client}.S.response': 1}
    return replay(operations, ports)
