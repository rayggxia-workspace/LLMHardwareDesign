"""Mother CALL and local terminal timing for the programmed FFN."""
from dataclasses import dataclass


FIRST_CALL_DELAY = 58
CALL_SPACING = 16
WAIT_TO_CALL = 18
CALL_TO_FETCH = 46
DESCRIPTOR_CHECK_TICKS = 125
LAST_RECORD_TO_DONE = 2
DONE_TO_TERMINAL_FRAME = 5
TERMINAL_FRAME_WITH_BUBBLE = 5
TERMINAL_EOP_OFFSET = 3
GATE_UP_STRIPES = 58
DOWN_GROUPS = 6
GATE_UP_COLUMNS = 11008
STRIPE_COLUMNS = 192
MID_COLUMNS = 128


@dataclass(frozen=True, slots=True)
class ScopeGroup:
    owner: int
    last_records: tuple[int, ...]
    synchronized_done: bool


class MotherController:
    """Advance WAIT, grouped CALLs and the single shared terminal receiver."""

    def __init__(self, start, groups, lanes):
        self.groups = groups
        self.lanes = lanes
        self.clients = tuple(sorted(lanes))
        self.group = 0
        self.next_call = start + FIRST_CALL_DELAY
        self.call_lane = 0
        self.local_done = {}
        self.awaiting = set(self.clients)
        self.done = {}
        self.rx_open = start
        self.rx_frame = None

    def advance(self, tick):
        if self.group == len(self.groups):
            return (), ()
        group = self.groups[self.group]
        calls = ()
        if tick == self.next_call:
            calls = (self.clients[self.call_lane],)
            self.call_lane += 1
            self.next_call = tick + CALL_SPACING if self.call_lane < len(group.last_records) else None

        for client in self.awaiting:
            if client in self.local_done:
                continue
            retired = self.lanes[client].retired.get(group.last_records[client])
            if retired is not None:
                self.local_done[client] = retired + LAST_RECORD_TO_DONE
                if not group.synchronized_done:
                    self.done[group.owner, client] = self.local_done[client]
        if group.synchronized_done and len(self.local_done) == len(group.last_records):
            if (group.owner, 0) not in self.done:
                done = max(self.local_done.values())
                self.done.update(((group.owner, client), done) for client in self.local_done)

        if self.rx_frame is not None:
            client, eop = self.rx_frame
            if tick == eop:
                self.rx_frame = None
                self.awaiting.remove(client)
                if not self.awaiting:
                    self.group += 1
                    if self.group < len(self.groups):
                        self.next_call = tick + WAIT_TO_CALL
                        self.call_lane = 0
                        self.awaiting = set(self.clients)
                        self.local_done.clear()
                return calls, (client,)
        elif tick >= self.rx_open:
            for client in self.clients:
                if client not in self.awaiting:
                    continue
                done = self.done.get((group.owner, client))
                if done is not None and tick >= done + DONE_TO_TERMINAL_FRAME:
                    self.rx_frame = client, tick + TERMINAL_EOP_OFFSET
                    self.rx_open = tick + TERMINAL_FRAME_WITH_BUBBLE
                    break
        return calls, ()

    def validate(self):
        if self.group != len(self.groups) or self.next_call is not None or self.rx_frame is not None:
            raise ValueError('mother controller stopped with pending calls or terminals')
