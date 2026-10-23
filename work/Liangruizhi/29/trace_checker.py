"""External pre-edge trace checker; no RTL arbitration algorithm is imported.

Only accepted request handshakes drive an independent byte-addressed memory and
per-endpoint expected-response FIFO. It proves the recorded finite execution's
data/protocol safety, not unbounded liveness, RR optimality, or silicon SRAM timing.
"""
from collections import Counter, deque
import argparse
import hashlib
import json
from pathlib import Path


def _hex(value, bits):
    if not isinstance(value, str):
        raise ValueError("hex payload must be a string")
    digits = value[2:] if value.startswith(("0x", "0X")) else value
    if not digits or len(digits) > bits // 4 or any(c not in "0123456789abcdefABCDEF" for c in digits):
        raise ValueError("invalid/oversized hex payload")
    return int(digits, 16)


def _bit(value):
    if type(value) is bool:
        return value
    if type(value) is int and value in (0, 1):
        return bool(value)
    raise ValueError("expected Boolean or integer 0/1")


def _uint(value, bits):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError("invalid unsigned field")
    return value


class Checker:
    def __init__(self, config, require_known_reads=False, external_min_gap=0):
        if config.get("type") != "config" or type(config.get("mode")) is not int or config["mode"] not in (0, 1, 2):
            raise ValueError("first record must configure mode 0/1/2")
        if type(config.get("depth")) is not int or config["depth"] not in (1, 2, 4):
            raise ValueError("response depth must be 1/2/4")
        _uint(config.get("mask"), 6)
        self.config, self.require_known = config, require_known_reads
        self.memory = [[bytearray(64) for _ in range(1024)] for _ in range(2)]
        self.known = [[0] * 1024 for _ in range(2)]
        self.origin = [[[None] * 64 for _ in range(1024)] for _ in range(2)]
        self.queues = [deque() for _ in range(3)]
        self.previous_request, self.previous_response = [None] * 3, [None] * 3
        self.counts, self.errors = Counter(), []
        self.error_count = 0
        self.last_cycle = None
        self.peak = [0] * 3
        self.req_stall = [0] * 3
        self.max_req_stall = [0] * 3
        if type(external_min_gap) is not int or external_min_gap < 0:
            raise ValueError("external minimum data gap must be a nonnegative integer")
        self.external_min_gap, self.last_external_data = external_min_gap, None

    def external_data(self, cycle, direction):
        if self.external_min_gap and self.last_external_data is not None:
            self.check(cycle - self.last_external_data >= self.external_min_gap,
                       "external_data_service_gap", cycle, 2, direction=direction,
                       previous_cycle=self.last_external_data, minimum_gap=self.external_min_gap)
        self.last_external_data = cycle
        self.counts["external_data_beats"] += 1

    def check(self, condition, code, cycle, endpoint=None, **details):
        self.counts["checks"] += 1
        if not condition:
            self.error_count += 1
            self.counts["error:" + code] += 1
            if len(self.errors) < 100:
                self.errors.append({"code": code, "cycle": cycle, "endpoint": endpoint, **details})

    def process(self, row):
        cycle = row["cycle"]
        if type(cycle) is not int or cycle < 0:
            raise ValueError("cycle must be a nonnegative integer")
        self.check(self.last_cycle is None or cycle == self.last_cycle + 1, "noncontiguous_cycle", cycle)
        self.last_cycle = cycle
        if len(row["req"]) != 3 or len(row["rsp"]) != 3:
            raise ValueError("exactly three endpoint records required")
        self.counts["cycles"] += 1
        if _bit(row.get("reset", False)):
            self.counts["reset_cycles"] += 1
            self.counts["responses_cancelled_by_reset"] += sum(map(len, self.queues))
            for q in self.queues:
                q.clear()
            self.previous_request, self.previous_response = [None] * 3, [None] * 3
            self.req_stall = [0] * 3
            return  # Reset cancels control state, not bank contents.
        parsed_requests, accepted = [], []
        # Compare OLD responses before adding any accepted request from this edge:
        # there is no zero-cycle response bypass, even at depth 1.
        for ep, (request, response) in enumerate(zip(row["req"], row["rsp"])):
            rv, rr = _bit(response["valid"]), _bit(response["ready"])
            queue = self.queues[ep]
            self.check(rv == bool(queue), "response_valid_or_latency", cycle, ep, expected=bool(queue), actual=rv)
            rp = None
            if rv:
                rw, tag = _bit(response["write"]), _uint(response["tag"], 32)
                data = _hex(response["data_hex"], 512) if not rw else None
                rp = (rw, tag, data)
                if queue:
                    expected = queue[0]
                    self.check((rw, tag) == (expected["write"], expected["tag"]), "response_type_tag_order", cycle, ep)
                    if not expected["write"] and not rw:
                        actual_bytes = data.to_bytes(64, "little")
                        self.check(all(not (expected["known"] >> i & 1) or actual_bytes[i] == expected["data"][i]
                                       for i in range(64)), "read_data", cycle, ep,
                                   bank=expected["bank"], addr=expected["addr"], tag=expected["tag"])
            if self.previous_response[ep] is not None:
                self.check(rv and rp == self.previous_response[ep], "response_changed_while_stalled", cycle, ep)
            self.previous_response[ep] = rp if rv and not rr else None
            if rv and rr:
                if ep == 2 and not rp[0]:
                    self.external_data(cycle, "read_sink")
                self.counts["responses_consumed"] += 1
                self.counts["write_acks_consumed" if rp[0] else "read_responses_consumed"] += 1
                if queue:
                    queue.popleft()
            qv, qr = _bit(request["valid"]), _bit(request["ready"])
            qp = None
            if qv:
                bank, write, addr, tag = _uint(request["bank"], 1), _bit(request["write"]), _uint(request["addr"], 10), _uint(request["tag"], 32)
                wdata = _hex(request["wdata_hex"], 512) if write else None
                wstrb = _hex(request["wstrb_hex"], 64) if "wstrb_hex" in request else ((1 << 64) - 1)
                generation = request.get("generation", -1)
                offset = request.get("generation_offset", 0)
                if type(generation) is not int or generation < -1 or type(offset) is not int or offset < 0:
                    raise ValueError("invalid generation metadata")
                qp = (bank, write, addr, tag, wdata, wstrb, generation, offset)
            if self.previous_request[ep] is not None:
                self.check(qv and qp == self.previous_request[ep], "request_changed_while_stalled", cycle, ep)
            self.previous_request[ep] = qp if qv and not qr else None
            self.req_stall[ep] = self.req_stall[ep] + 1 if qv and not qr else 0
            self.max_req_stall[ep] = max(self.max_req_stall[ep], self.req_stall[ep])
            parsed_requests.append(qp)
            if qv and qr:
                bank, write, addr, tag, wdata, wstrb, generation, offset = qp
                self.check(bool(self.config["mask"] & (1 << (ep * 2 + bank))), "disabled_link_accepted", cycle, ep)
                self.check(len(queue) < self.config["depth"], "response_credit_overflow", cycle, ep,
                           occupancy_after_pop=len(queue), depth=self.config["depth"])
                self.check(not (write and rv and not rp[0]), "half_duplex_write_during_read_response", cycle, ep)
                accepted.append((ep, qp))
        for bank in (0, 1):
            grants = [q for _, q in accepted if q[0] == bank]
            reads, writes = sum(not q[1] for q in grants), sum(q[1] for q in grants)
            mode = self.config["mode"]
            legal = len(grants) <= (1 if mode == 0 else 2)
            if mode == 1:
                legal = legal and reads <= 1 and writes <= 1
            self.check(legal, "bank_port_contract", cycle, bank=bank, reads=reads, writes=writes)
            self.check(len({q[2] for q in grants}) == len(grants), "same_row_double_grant", cycle, bank=bank)
        # Snapshot all reads from pre-edge memory, then commit accepted writes.
        additions = []
        for ep, (bank, write, addr, tag, wdata, wstrb, generation, offset) in accepted:
            packet = {"write": write, "tag": tag, "bank": bank, "addr": addr, "accepted_cycle": cycle}
            if not write:
                packet.update(data=bytes(self.memory[bank][addr]), known=self.known[bank][addr])
                known_count = packet["known"].bit_count()
                self.counts["read_bytes_known"] += known_count
                self.counts["read_bytes_unknown"] += 64 - known_count
                self.counts["fully_known_read_beats"] += known_count == 64
                if self.require_known:
                    self.check(known_count == 64, "read_before_full_byte_initialization", cycle, ep, bank=bank, addr=addr)
                if generation >= 0:
                    requested = [i for i in range(64) if wstrb >> i & 1]
                    self.check(all(self.known[bank][addr] >> i & 1 for i in requested),
                               "uninitialized_semantic_read_bytes", cycle, ep, bank=bank, addr=addr)
                    self.check(all(self.origin[bank][addr][i] == (generation, offset + i) for i in requested),
                               "graph_read_generation_or_offset", cycle, ep, bank=bank, addr=addr,
                               expected_generation=generation, expected_offset=offset)
                    self.counts["versioned_read_bytes"] += len(requested)
            additions.append((ep, packet))
            self.counts["requests_accepted"] += 1
            self.counts["writes_accepted" if write else "reads_accepted"] += 1
        for ep, (bank, write, addr, tag, wdata, wstrb, generation, offset) in accepted:
            if write:
                if ep == 2:
                    self.external_data(cycle, "write_source")
                payload = wdata.to_bytes(64, "little")
                for byte in range(64):
                    if wstrb >> byte & 1:
                        self.memory[bank][addr][byte] = payload[byte]
                        self.origin[bank][addr][byte] = (generation, offset + byte) if generation >= 0 else None
                self.known[bank][addr] |= wstrb
                self.counts["write_bytes_committed"] += wstrb.bit_count()
                self.counts["zero_strobe_writes"] += wstrb == 0
        for ep, packet in additions:
            self.queues[ep].append(packet)
            self.peak[ep] = max(self.peak[ep], len(self.queues[ep]))

    def finish(self):
        outstanding = sum(map(len, self.queues))
        self.check(outstanding == 0, "undrained_response_queues", self.last_cycle, outstanding=outstanding)
        self.check(self.counts["requests_accepted"] == self.counts["responses_consumed"]
                   + self.counts["responses_cancelled_by_reset"] + outstanding,
                   "request_response_conservation", self.last_cycle)
        if "expected_accepts" in self.config:
            self.check(self.counts["requests_accepted"] == self.config["expected_accepts"],
                       "expected_request_count", self.last_cycle)
        return {"status": "PASS" if not self.error_count else "FAIL", "config": self.config,
                "require_fully_initialized_reads": self.require_known,
                "external_minimum_data_beat_gap": self.external_min_gap,
                "counts": dict(self.counts), "response_queue_peak": self.peak,
                "max_contiguous_request_stall_cycles": self.max_req_stall,
                "unaccepted_request_valid_at_end": sum(x is not None for x in self.previous_request),
                "errors": self.errors, "error_count": self.error_count,
                "scope": "Finite trace safety/data/order/credits; unknown read bytes unverified unless strict mode; not an RR implementation oracle or unbounded liveness proof."}


def audit_trace(path, require_known_reads=False, external_min_gap=0):
    path = Path(path)
    h = hashlib.sha256()
    checker = None
    with path.open("rb") as stream:
        for line_number, raw in enumerate(stream, 1):
            h.update(raw)
            if not raw.strip():
                continue
            row = json.loads(raw)
            try:
                if checker is None:
                    checker = Checker(row, require_known_reads, external_min_gap)
                else:
                    checker.process(row)
            except Exception as exc:
                raise ValueError(f"{path}:{line_number}: {type(exc).__name__}: {exc}") from exc
    if checker is None:
        raise ValueError("empty trace")
    result = checker.finish()
    result["trace"] = {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": h.hexdigest()}
    result["checker_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("traces", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-known-reads", action="store_true")
    parser.add_argument("--external-min-gap", type=int, default=0,
                        help="program-only combined EP2 write-accept/read-consume beat spacing; stress uses 0")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("refusing to overwrite report")
    records = []
    for trace in args.traces:
        try:
            records.append(audit_trace(trace, args.require_known_reads, args.external_min_gap))
        except Exception as exc:
            records.append({"status": "ERROR", "trace": str(trace), "error": f"{type(exc).__name__}: {exc}"})
    report = {"status": "PASS" if all(r["status"] == "PASS" for r in records) else "FAIL", "records": records}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "traces": len(records),
                      "errors": sum(r.get("error_count", 1 if r["status"] == "ERROR" else 0) for r in records)}))
    return report["status"] == "PASS"


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
