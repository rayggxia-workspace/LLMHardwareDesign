"""The #251 four-bank feeder, including request and response ownership."""
from collections import deque
from dataclasses import dataclass

from dma_read import ready_intervals, ready_mask


@dataclass(frozen=True)
class Access:
    site: str
    word: int
    words: int
    wide: bool
    write: bool

    def valid(self):
        width = 4 if self.wide else 1
        return (0 <= self.word < self.word + self.words <= 1024
                and self.word % width == self.words % width == 0
                and not (self.wide and self.write))


def profile(spec):
    if not isinstance(spec, dict) or spec.keys() - {'ready'}:
        raise ValueError('invalid SRAM feeder profile')
    return ready_intervals(spec.get('ready', ()), 3)


class SramFeeder:
    def __init__(self, ready):
        self.ready = ready
        self.requests = deque(), deque()
        self.responses = deque(), deque()
        self.receipts = {}

    @property
    def active(self):
        return bool(self.receipts)

    def next_edge(self, tick):
        future = []
        for port, (requests, responses) in enumerate(zip(self.requests, self.responses)):
            if requests and len(responses) < 2:
                return tick
            if responses:
                edge = max(tick, responses[0][0] + 2)
                for start, end, mask in self.ready:
                    if edge < start:
                        break
                    if edge < end and not mask & (1 << port):
                        edge = end
                future.append(edge)
        return min(future)

    def submit(self, key, access):
        width = 4 if access.wide else 1
        self.receipts[key] = []
        self.requests[access.wide].extend(
            (key, word, word + width == access.word + access.words)
            for word in range(access.word, access.word + access.words, width)
        )

    def advance(self, tick):
        ready = ready_mask(self.ready, tick, 3)
        completed = []
        for port, queue in enumerate(self.responses):
            if queue and queue[0][0] + 2 <= tick and ready & (1 << port):
                issue, key, word, last = queue.popleft()
                self.receipts[key].append((word, issue, tick))
                if last:
                    completed.append((key, tuple(self.receipts.pop(key))))
        # The wide mux takes all banks. The narrow mux selects word[1:0].
        # A slot released by a response pop can be reserved on this edge.
        for port in (1, 0):
            if self.requests[port] and len(self.responses[port]) < 2:
                self.responses[port].append((tick, *self.requests[port].popleft()))
                break
        return completed


def receipt_json(access, receipts):
    return [{'word': word, 'banks': [0, 1, 2, 3] if access.wide else [word & 3],
             'issue': issue, 'ack': ack} for word, issue, ack in receipts]
