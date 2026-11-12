"""COPY and private A loads through the #251 narrow SRAM ports."""
from collections import defaultdict, deque
from dataclasses import dataclass, field

from ffn_scatter import s_pressure


P_COUNT = 3
WORDS = 16
A_BASE = 880
COPY, A_READ, AUX = 1, 2, 3
EVENTS = ('start', 'source', 'returned', 'done', 'load', 'read', 'response', 'copy', 'ack', 'prefix')


@dataclass
class Port:
    """Two ordered response owners and a four-client round-robin cursor."""

    cursor: int = 0
    owners: deque = field(default_factory=deque)

    def step(self, tick, offers, request_ready, response_ready):
        response = request = None
        if response_ready and self.owners and self.owners[0][0] <= tick:
            _, response = self.owners.popleft()
        if request_ready and len(self.owners) < 2:
            for offset in range(4):
                client = (self.cursor + offset) % 4
                if client in offers:
                    request = client, offers[client]
                    self.owners.append((tick + 2, request))
                    self.cursor = (client + 1) % 4
                    break
        return request, response


def open_at(tick, window):
    return (tick + window['offset']) % window['period'] >= window['closed']


def replay_tile(mode, start, scope, k, generation, ticket, loads, a_generation, *, down):
    """Return expected handshakes and the common edge that takes all A proofs.

    The programmed fixture closes the previous COPY and its A reads before
    starting the next COPY. Its first request establishes each port's cursor.
    """
    ports = [Port() for _ in range(P_COUNT)]
    req_windows = [s_pressure(p, False) for p in range(P_COUNT)]
    rsp_windows = [s_pressure(p, True) for p in range(P_COUNT)]
    tile = k // 128
    slot = tile % 2
    if down:
        source = tile % P_COUNT
        source_base = 256 + WORDS * (tile // P_COUNT)
    else:
        source = P_COUNT
        source_base = 512 + WORDS * tile
    events = defaultdict(list)
    events['start'].append((start, scope, k, generation, ticket))
    for p, load in enumerate(loads):
        events['load'].append((load, p, scope, k, a_generation, slot, A_BASE))

    copied = [[] for _ in range(P_COUNT)]
    read = [0] * P_COUNT
    read_pending = [False] * P_COUNT
    next_read = [load + 2 for load in loads]
    source_word, source_offer = 0, start + 2
    source_due = write_offer = done = None
    write_sent = set()

    # Bound a bad replay separately from the functional proof condition.
    # Each word needs one source transfer and three concurrent writes, with
    # periodic READY and at most one older response ahead of each transfer.
    deadline = max(start, *loads) + WORDS * 64
    for tick in range(start, deadline):
        tag = (generation << 16) | source_word
        if source == P_COUNT and tick == source_offer:
            events['source'].append((tick, source, source_base + source_word, tag))
            source_offer, source_due = None, tick + 2
        if tick == source_due:
            events['returned'].append((tick, source, tag))
            source_due, write_offer = None, tick + 1

        for p, port in enumerate(ports):
            offers = {}
            if write_offer is not None and tick >= write_offer and p not in write_sent:
                offers[COPY] = A_BASE + source_word, tag
            word = read[p]
            if (not read_pending[p] and word < len(copied[p])
                    and tick >= max(next_read[p], copied[p][word] + 2)):
                offers[A_READ] = A_BASE + word, (a_generation << 16) | (slot << 15) | (word << 11)
            if p == source and source_offer is not None and tick >= source_offer:
                offers[AUX] = source_base + source_word, tag

            request, response = port.step(tick, offers, not mode or open_at(tick, req_windows[p]),
                                          not mode or open_at(tick, rsp_windows[p]))
            if request:
                client, (address, request_tag) = request
                if client == COPY:
                    write_sent.add(p)
                    events['copy'].append((tick, p, address, request_tag))
                elif client == A_READ:
                    read_pending[p] = True
                    events['read'].append((tick, p, address, request_tag))
                else:
                    source_offer = None
                    events['source'].append((tick, p, address, request_tag))
            if response:
                client, (_, response_tag) = response
                if client == COPY:
                    copied[p].append(tick)
                    events['ack'].append((tick, p, response_tag))
                elif client == A_READ:
                    read[p] += 1
                    read_pending[p] = False
                    next_read[p] = tick + 2
                    events['response'].append((tick, p, response_tag))
                else:
                    write_offer = tick + 1
                    events['returned'].append((tick, p, response_tag))

        if write_offer is not None and all(len(acks) > source_word for acks in copied):
            write_offer = None
            write_sent.clear()
            source_word += 1
            if source_word == WORDS:
                done = tick + 2
                events['done'].append((done, generation, 0))
            else:
                source_offer = tick + 2
        if done is not None and all(count == WORDS for count in read):
            proof = max(done + 1, *next_read)
            for p, load in enumerate(loads):
                visible = sum(ack < load for ack in copied[p])
                events['prefix'].append((load, p, generation, visible))
                events['prefix'].extend((ack + 1, p, generation, word)
                                        for word, ack in enumerate(copied[p][visible:], visible + 1))
                events['prefix'].append((proof + 2, p, generation, 0))
            return events, proof
    raise ValueError(f'COPY or A read stalled in scope {scope}, K={k}')
