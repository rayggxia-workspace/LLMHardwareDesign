"""Protocol-only audit for alternative two-slot PRIVATE_S128 A prefetch.

One P, one shared native S port, two bounded A256B slots. It does not implement
the production front-end FSM or assign a cycle cost to a phase switch.
"""
from audit_protocol import Violation, require


class PrivateA:
    def __init__(self):
        self.slots = {}
        self.slot_generation = [-1, -1]
        self.pending = None
        self.phase = None
        self.phase_switches = 0
        self.halted = False
        self.planned, self.issued = 2, 0
        self.source_closed = False

    def step(self, e):
        op = e["op"]
        if op == "A_PREPARE":
            require(not self.halted and not self.source_closed, "A prepare after halt/source close")
            slot = e["slot"]
            require(slot in (0, 1) and slot not in self.slots, "two A slots exhausted")
            require(e["generation"] > self.slot_generation[slot], "stale A slot generation")
            require(self.issued < self.planned and 0 <= e["source_base"] <= 1008, "A plan/source range")
            self.slot_generation[slot] = e["generation"]
            self.slots[slot] = {"tag": e["tag"], "generation": e["generation"], "state": "PREPARED", "returned": 0, "consumed": 0, "W": False}
        elif op == "A_LOAD_ACCEPT":
            require(not self.halted, "new A load after halt")
            s = self.slots[e["slot"]]
            require(s["state"] == "PREPARED", "A load state")
            s["state"] = "LOADING"
            self.issued += 1
        elif op in ("S_A_REQUEST", "S_OTHER_REQUEST"):
            require(self.pending is None, "native S port double-booked")
            if op == "S_A_REQUEST":
                s = self.slots[e["slot"]]
                require(s["state"] == "LOADING" and e["word"] == s["returned"], "A read order/state")
                require(e["tag"] == s["tag"] and e["generation"] == s["generation"], "A read identity mismatch")
                phase = "A"
            else:
                require(not self.halted, "new unrelated S service after halt")
                phase = "OTHER"
            if self.phase is not None and phase != self.phase:
                self.phase_switches += 1
            self.phase = phase
            self.pending = e.copy()
        elif op == "S_RETURN":
            require(self.pending is not None and e["request_id"] == self.pending["request_id"], "foreign/duplicate S response")
            if self.pending["op"] == "S_A_REQUEST":
                s = self.slots[self.pending["slot"]]
                s["returned"] += 1
                if s["returned"] == 16:
                    s["state"] = "READY"
            self.pending = None
        elif op == "W_READY":
            s = self.slots[e["slot"]]
            require(e["tag"] == s["tag"] and e["generation"] == s["generation"], "W/A identity mismatch")
            s["W"] = True
        elif op == "M_JOIN":
            s = self.slots[e["slot"]]
            require(s["state"] == "READY" and s["W"], "M started before tagged A/W join")
            require(not any(x["state"] == "CONSUMING" for x in self.slots.values()), "M operand consumer already busy")
            s["state"] = "CONSUMING"
        elif op == "M_A_ACCEPT":
            s = self.slots[e["slot"]]
            require(e.get("actual_handshake") is True and s["state"] == "CONSUMING", "no real M operand acceptance")
            require(e["tag"] == s["tag"] and e["generation"] == s["generation"], "M/A identity mismatch")
            require(e["K16_step"] == s["consumed"], "M K16 pairing order")
            s["consumed"] += 1
            if s["consumed"] == 8:
                s["state"] = "DRAINED"
        elif op == "A_RELEASE":
            require(self.slots[e["slot"]]["state"] == "DRAINED", "A release before last actual M consumption")
            del self.slots[e["slot"]]
        elif op == "X_END_READ":
            require(self.issued == self.planned and self.pending is None and all(s["state"] not in ("PREPARED", "LOADING") for s in self.slots.values()), "X close before all planned real S reads")
            self.source_closed = True
        elif op == "CANCEL":
            self.halted = True
        elif op == "RESET":
            require(self.halted and self.pending is None and not any(s["state"] == "CONSUMING" for s in self.slots.values()), "reset discards accepted S/M obligation")
            self.slots.clear()
        else:
            raise Violation("unknown private-A event")


def private_cases():
    tag0, tag1 = "job250/epoch1/object1/kk0", "job250/epoch1/object1/kk1"
    prep = lambda slot, tag: {"op": "A_PREPARE", "slot": slot, "generation": 1, "source_base": slot * 16, "tag": tag}
    load = lambda slot: {"op": "A_LOAD_ACCEPT", "slot": slot}
    def reads(slot, tag):
        trace = []
        for word in range(16):
            trace += [{"op": "S_A_REQUEST", "slot": slot, "word": word, "generation": 1, "tag": tag, "request_id": slot * 16 + word}, {"op": "S_RETURN", "request_id": slot * 16 + word}]
        return trace
    start = [prep(0, tag0), load(0)] + reads(0, tag0)
    start += [prep(1, tag1), load(1)]
    start += [{"op": "S_OTHER_REQUEST", "request_id": 100}, {"op": "S_RETURN", "request_id": 100}]
    start += reads(1, tag1)
    start += [{"op": "X_END_READ"}, {"op": "W_READY", "slot": 0, "generation": 1, "tag": tag0}, {"op": "M_JOIN", "slot": 0}]
    consume = [{"op": "M_A_ACCEPT", "slot": 0, "generation": 1, "tag": tag0, "K16_step": step, "actual_handshake": True} for step in range(8)]
    good = start + consume + [{"op": "A_RELEASE", "slot": 0}]
    yield "private_A_prefetch_before_W_and_shared_S_phase", good, None
    yield "private_no_third_A_slot", [prep(0, tag0), prep(1, tag1), prep(0, tag0)], "two A slots exhausted"
    yield "private_A_READY_without_W_not_M_ready", [prep(0, tag0), load(0)] + reads(0, tag0) + [{"op": "M_JOIN", "slot": 0}], "M started before tagged A/W join"
    yield "private_W_wrong_kk_cannot_join", start[:-2] + [{"op": "W_READY", "slot": 0, "generation": 1, "tag": tag1}], "W/A identity mismatch"
    yield "private_A_waits_last_M_accept", start + consume[:7] + [{"op": "A_RELEASE", "slot": 0}], "A release before last actual M consumption"
    first_read = [prep(0, tag0), load(0)] + reads(0, tag0)[:1]
    yield "private_S_port_is_one_calendar", first_read + [{"op": "S_OTHER_REQUEST", "request_id": 100}], "native S port double-booked"
    yield "private_X_source_close_not_only_first_tile", [prep(0, tag0), load(0)] + reads(0, tag0) + [{"op": "X_END_READ"}], "X close before all planned real S reads"
    yield "private_cancel_keeps_pending_S_read", first_read + [{"op": "CANCEL"}, {"op": "RESET"}], "reset discards accepted S/M obligation"
    yield "private_cancel_drains_then_invalidates_partial_A", first_read + [{"op": "CANCEL"}, {"op": "S_RETURN", "request_id": 0}, {"op": "RESET"}], None


def replay_private(events):
    state = PrivateA()
    for i, e in enumerate(events):
        try:
            state.step(e)
        except (Violation, KeyError, TypeError) as exc:
            raise Violation(f"event {i} {e.get('op')}: {exc}") from exc
    return {"phase_switches_unpriced": state.phase_switches, "live_A_slots": len(state.slots)}
