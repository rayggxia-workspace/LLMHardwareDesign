"""Predict the frozen two-U_64 compact control program and stored-link timing."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from dual_u_images import read_images
from dual_u_services import Services, seed_memory


HISTORICAL_EVENTS = {"START", "MCPM", "LCPM", "WRITE", "COMMIT", "RELEASE"}
PROBED_EVENTS = HISTORICAL_EVENTS | {"CALL", "MC_RETURN", "RESULT", "LC_ISSUE", "LC_RETURN",
                                     "S_GRANT", "S_SEND", "S_RSP", "S_CONTEND", "E_ISSUE",
                                     "E_RETURN", "E_BEAT", "E_RESULT", "TX_READ"}
RUNTIME_PREFIXES = ("FETCH ", "DUAL ", "WRITE ", "COMMIT ", "RELEASE ")


class Controller:
    def __init__(self, image, stall=0, block=None):
        self.image = image
        self.stall, self.block = stall, block
        self.pc, self.ready, self.beat, self.service_index = 0, 0, 0, 0
        self.state = "idle"
        self.active_descriptor = None
        self.active_token = None
        self.token_complete = False
        self.live = {}
        self.completed = set()
        self.read_bytes, self.write_bytes = 0, 0

    def fetch(self, cycle, address, resume, emit):
        if self.block is not None and self.stall and cycle % 5:
            self.ready = cycle + (-cycle % 5)
            return False
        if self.block is None:
            emit(cycle, "MCPM", addr=address)
            delay = 4
        else:
            emit(cycle, "LCPM", block=self.block, addr=address)
            delay = 3 + self.stall
        self.state, self.ready = resume, cycle + delay + 1
        return True

    def word(self):
        return self.image["instructions"][self.pc]

    def advance(self, cycle):
        self.pc += 1
        self.state, self.ready = "fetch", cycle + 1

    def start(self, cycle):
        self.state, self.ready = ("fetch" if self.block is None else "task"), cycle + 1

    def step(self, cycle, emit):
        if cycle < self.ready:
            return
        if self.state == "fetch":
            self.fetch(cycle, self.word()["address"], "decode", emit)
        elif self.state == "task":
            if self.fetch(cycle, self.image["task_offset"] + 16 * self.beat,
                          "task" if self.beat < 3 else "task_loaded", emit):
                self.beat += 1
        elif self.state == "task_loaded":
            self.beat = 0
            self.state, self.ready = "fetch", cycle + 1
        elif self.state == "descriptor":
            address = self.image["execution_offset"] + 128 * self.word()["c"] + 16 * self.beat
            if self.fetch(cycle, address, "descriptor" if self.beat < 7 else "descriptor_loaded", emit):
                self.beat += 1
        elif self.state == "descriptor_loaded":
            self.active_descriptor = self.image["execution"][self.word()["c"]]
            self.beat = 0
            self.state, self.ready = "offer", cycle + 1
        elif self.state == "decode":
            word = self.word()
            op = word["op"]
            if op == "G_CALL":
                self.state, self.ready = "call", cycle + 1
            elif op == "G_WAIT":
                mask = sum(1 << token for token in self.live.values())
                if word["x"] != mask:
                    raise ValueError("MC WAIT mask disagrees with live target tokens")
                if self.completed == self.live.keys():
                    self.live.clear()
                    self.advance(cycle)
            elif op == "G_END":
                if self.live:
                    raise ValueError("MC END with live target")
                self.state, self.ready = "result", cycle + 1
            elif op == "L_EXEC":
                self.state, self.ready = "descriptor", cycle + 1
            elif op == "L_WAIT":
                self.state, self.ready = "wait", cycle + 1
            elif op == "L_END":
                if self.active_descriptor is not None:
                    raise ValueError("LC END with live service")
                self.state, self.ready = "terminal", cycle + 1
            else:
                raise ValueError("unsupported instruction: " + op)
        elif self.state == "wait" and self.token_complete:
            self.token_complete, self.active_descriptor, self.active_token = False, None, None
            self.advance(cycle)


def predict(images, inputs, start, stall, request_phase=1, ack_phase=3, limit=10000, skip_idle=True):
    if type(start) is not int or start < 0 or type(stall) is not int or stall not in (0, 1):
        raise ValueError("invalid START edge or backpressure mode")
    if (type(request_phase) is not int or not 0 <= request_phase < 7
            or type(ack_phase) is not int or not 0 <= ack_phase < 11):
        raise ValueError("invalid ready phase")
    services = Services(seed_memory(inputs), request_period=7 if stall else 1,
                        request_phase=request_phase if stall else 0,
                        ack_period=11 if stall else 1, ack_phase=ack_phase if stall else 0)
    mc = Controller(images["mc"])
    locals_ = [Controller(img, stall, block) for block, img in enumerate(images["locals"])]
    events = []
    job = {"job": 7, "epoch": 1, "seq": 1}

    def emit(cycle, kind, **fields):
        events.append((cycle, kind, fields))

    mc.start(start)
    emit(start, "START")
    cycle = start + 1
    while cycle <= start + limit:
        # Handshakes sample the old control state. A newly decoded CALL, local
        # service or terminal cannot be accepted on the same edge.
        call = mc.word() if mc.state == "call" and cycle >= mc.ready else None
        terminal = next((lc for lc in locals_ if lc.state == "terminal" and cycle >= lc.ready), None)
        offered = {lc.block: lc.active_descriptor for lc in locals_ if lc.state == "offer" and cycle >= lc.ready}
        response_ready = {lc.block: lc.active_descriptor is not None and lc.state != "offer"
                          and not lc.token_complete for lc in locals_}
        if mc.state == "result" and cycle >= mc.ready:
            emit(cycle, "RESULT", status=0, reads=mc.read_bytes, writes=mc.write_bytes, **job)
            return events + [(row["cycle"], row["kind"], {key: value for key, value in row.items()
                              if key not in ("cycle", "kind")}) for row in services.events], cycle

        accepted, returned = services.step(cycle, offered, response_ready)
        mc.step(cycle, emit)
        for lc in locals_:
            lc.step(cycle, emit)

        if call is not None:
            block, token = call["a"], call["b"]
            if locals_[block].state != "idle" or block in mc.live or token in mc.live.values():
                raise ValueError("MC CALL reuses a live target or token")
            mc.live[block] = token
            locals_[block].start(cycle)
            emit(cycle, "CALL", block=block, token=token, **job)
            mc.advance(cycle)
        if terminal is not None:
            block = terminal.block
            if block not in mc.live or block in mc.completed:
                raise ValueError("unexpected MC terminal")
            mc.completed.add(block)
            mc.read_bytes += terminal.read_bytes
            mc.write_bytes += terminal.write_bytes
            emit(cycle, "MC_RETURN", block=block, token=mc.live[block], status=0,
                 reads=terminal.read_bytes, writes=terminal.write_bytes, **job)
            terminal.state = "idle"
        for block in accepted:
            lc = locals_[block]
            word = lc.word()
            row = lc.active_descriptor
            lc.active_token = word["b"]
            emit(cycle, "LC_ISSUE", block=block, pc=lc.pc, seq=lc.service_index, token=lc.active_token,
                 op=row["native_op"], n0=row["native0"], n1=row["native1"], n2=row["native2"], n3=0)
            lc.advance(cycle)
        for block, response in returned.items():
            lc = locals_[block]
            if response["status"] or response["saturated"]:
                raise ValueError("unsupported native service failure")
            read_bytes, write_bytes = response["read_bytes"], response["write_bytes"]
            emit(cycle, "LC_RETURN", block=block, seq=lc.service_index, token=lc.active_token,
                 status=0, reads=read_bytes, writes=write_bytes)
            lc.service_index += 1
            lc.read_bytes += read_bytes
            lc.write_bytes += write_bytes
            lc.token_complete = True
        # PM waits have a known wake-up edge. Only advance one edge when a
        # native service or a runnable controller must sample the next edge.
        ready = [controller.ready for controller in (mc, *locals_)
                 if controller.state != "idle" and controller.ready > cycle
                 and (controller.state != "wait" or controller.token_complete)]
        parked = all(controller.state == "idle" or controller.state == "wait" and not controller.token_complete
                     or controller.ready > cycle
                     or controller is mc and controller.state == "decode" and controller.word()["op"] == "G_WAIT"
                     and controller.completed != controller.live.keys()
                     for controller in (mc, *locals_))
        if skip_idle and not services.active and not offered and parked and ready:
            cycle = min(ready)
        else:
            cycle += 1
    raise ValueError("dual U_64 runtime exceeded {} cycles (MC {}, LC {})".format(
        limit, mc.state, [lc.state for lc in locals_]))


def freeze(event):
    cycle, kind, fields = event
    return cycle, kind, tuple(sorted(fields.items()))


def log_events(log, allow_restart=False):
    if "%Fatal" in log or "%Error" in log:
        raise ValueError("RTL log contains errors")
    summaries = re.findall(r"^GENERATED_CONTROL_PASS cycles=(\d+) commits=3 confirmed_bytes=80 pm_requests=4$",
                           log, re.M)
    if len(summaries) != 1:
        raise ValueError("missing or duplicate RTL completion summary")
    start, events, reset_seen, config, after_summary = None, [], False, None, False
    last_edge = -1
    for line in log.splitlines():
        if line.startswith("GENERATED_CONTROL_PASS "):
            if start is None or reset_seen or events[-1][0] >= int(summaries[0]):
                raise ValueError("out-of-order RTL completion summary")
            after_summary = True
        elif after_summary and line.startswith((*RUNTIME_PREFIXES, "START ", "DUAL_CONFIG ", "EPOCH_BEGIN ")):
            raise ValueError("RTL event appears after completion summary")
        elif line.startswith("DUAL_CONFIG "):
            if config is not None:
                raise ValueError("duplicate RTL backpressure configuration")
            config = {key: int(value) for key, value in parse_fields(line.split()[1:]).items()}
        elif line.startswith("EPOCH_BEGIN cycle="):
            edge = int(line.split("=")[1])
            if edge < last_edge or reset_seen:
                raise ValueError("RTL epoch edges are out of order")
            last_edge = edge
            reset_seen = start is not None
        elif line.startswith("START cycle="):
            if start is not None and not (allow_restart and reset_seen):
                raise ValueError("duplicate START without an admitted reset boundary")
            # A reset trial abandons the first epoch. Compare the final START.
            start = int(line.split("=")[1])
            if start < last_edge:
                raise ValueError("RTL START edges are out of order")
            last_edge = start
            events = [(start, "START", {})]
            reset_seen = False
        elif not line.startswith(RUNTIME_PREFIXES):
            continue
        elif start is None or reset_seen:
            raise ValueError("RTL event outside a START window")
        elif line.startswith("FETCH "):
            fields = parse_fields(line.split()[1:])
            cycle = int(fields.pop("cycle"))
            kind = fields.pop("kind") + "PM"
            events.append((cycle, kind, {name: int(value) for name, value in fields.items()}))
        elif line.startswith(("WRITE ", "COMMIT ", "RELEASE ")):
            kind, *tokens = line.split()
            fields = parse_fields(tokens)
            cycle = int(fields.pop("cycle"))
            events.append((cycle, kind, {name: int(value, 16 if name == "data" else 10)
                                         for name, value in fields.items()}))
        else:
            fields = parse_fields(line.split()[1:])
            cycle, kind = int(fields.pop("cycle")), fields.pop("kind")
            events.append((cycle, kind, {name: int(value) for name, value in fields.items()}))
        if events and not reset_seen:
            edge = events[-1][0]
            if edge < last_edge:
                raise ValueError("RTL cycles out of order")
            last_edge = edge
    if start is None or reset_seen:
        raise ValueError("RTL log has no accepted START")
    return start, int(summaries[0]), events, config


def parse_fields(tokens):
    fields = {}
    for token in tokens:
        key, value = token.split("=", 1)
        if key in fields:
            raise ValueError("duplicate RTL event field: " + key)
        fields[key] = value
    return fields


def compare(directory, log, stall, request_phase=1, ack_phase=3, historical=False):
    images = read_images(directory, frozen=True)
    raw_inputs = (directory / "input-data.json").read_bytes()
    if hashlib.sha256(raw_inputs).hexdigest() != "2fbddab261072be1abce1af5427838ea578f3fdf2875096d16b616b4a73ecbac":
        raise ValueError("input data SHA-256 does not match the frozen U_64 case")
    data = log.read_bytes()
    start, pass_cycle, observed, config = log_events(data.decode("ascii"), allow_restart=historical)
    if not historical and config != {"stall": stall, "write_phase": request_phase, "ack_phase": ack_phase}:
        raise ValueError("RTL ready configuration disagrees with requested model input")
    events, result = predict(images, json.loads(raw_inputs), start, stall, request_phase, ack_phase)
    scope = HISTORICAL_EVENTS if historical else PROBED_EVENTS
    unknown = {kind for _, kind, _ in observed} - scope
    if unknown:
        raise ValueError("unexpected RTL event types: " + ", ".join(sorted(unknown)))
    pred, rtl = (Counter(freeze(event) for event in rows if event[1] in scope) for rows in (events, observed))
    diff = (pred - rtl) + (rtl - pred)
    if diff:
        edge = min(row[0] for row in diff)
        raise ValueError("first mismatch at edge {}: predicted {}; RTL {}".format(
            edge, [row[1:] for row in pred if row[0] == edge], [row[1:] for row in rtl if row[0] == edge]))
    if result + 1 != pass_cycle:
        raise ValueError("predicted result acceptance {} disagrees with post-edge RTL summary {}".format(
            result, pass_cycle))
    return {"start": start, "result": result, "post_edge_summary": pass_cycle, "cycles": result - start,
            "matched_events": sum(pred.values()), "max_cycle_error": 0,
            "log_sha256": hashlib.sha256(data).hexdigest(), "event_counts": dict(Counter(
                kind for _, kind, _ in pred.elements()))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", type=Path)
    parser.add_argument("log", type=Path)
    parser.add_argument("--stall", type=int, choices=(0, 1), required=True)
    parser.add_argument("--request-phase", type=int, default=1)
    parser.add_argument("--ack-phase", type=int, default=3)
    parser.add_argument("--historical", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(compare(args.images, args.log, args.stall, args.request_phase,
                                 args.ack_phase, args.historical), indent=2))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, "dual U_64 comparison failed: {}\n".format(error))
