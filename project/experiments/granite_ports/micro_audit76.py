"""Independent byte action/live-store replay for Issue76 micro qualification.

Only byte/S8 arithmetic appears in the replayed machine. Python integers in
oracle() are a separate mathematical checker, never a fee-free machine opcode.
"""
from collections import Counter
import hashlib
import json
import math

from audit_io76 import checked, divided_rne, need, shift_rne


FRAME = 512


def byte_action(op, a, b, c):
    need(all(type(v) is int and 0 <= v < 256 for v in (a, b, c)), "byte ALU input domain")
    if op in (0, 11):
        return a, 0
    if op == 1:
        value = a+b+(c % 2)
        return value % 256, value//256
    if op == 2:
        value = a-b-(c % 2)
        return value % 256, int(value < 0)
    if op == 3:
        left, right = (a if a < 128 else a-256), (b if b < 128 else b-256)
        value = left*right
        return value % 256, (value//256) % 256
    if op == 4:
        return (a*(1 << min(b, 8))) % 256, 0
    if op == 5:
        return a//(1 << min(b, 8)), 0
    if op == 6:
        return a | b, 0
    if op == 7:
        return a & b, 0
    if op == 8:
        return a ^ b, 0
    if op == 9:
        return int(a < b), int(a == b)
    if op == 10:
        return (a if c % 2 else b), 0
    raise ValueError("unknown restricted byte opcode")


def wrap(value, bits, signed):
    value %= 1 << bits
    return value-(1 << bits) if signed and value >= 1 << (bits-1) else value


def oracle(op, a, b=0, shift=0):
    """Separate exact arithmetic expectation, including rejection semantics."""
    need(all(type(v) is int for v in (a, b, shift)), "integer micro oracle")
    if op in ("mul_s32_s32", "mul_s64_s32", "mul_s32_u16"):
        abits = 64 if op == "mul_s64_s32" else 32
        checked(a, abits)
        if op == "mul_s32_u16":
            need(0 <= b < 1 << 16, "U16 gate domain")
        else:
            checked(b, 32)
        return {"value": a*b, "valid": True}
    if op in ("add_s64", "sub_s64", "add_u128"):
        bits, signed = (128, False) if op == "add_u128" else (64, True)
        if signed:
            checked(a, bits); checked(b, bits)
        else:
            need(0 <= a < 1 << bits and 0 <= b < 1 << bits, "U128 operands")
        value = a-b if op == "sub_s64" else a+b
        low, high = (-(1 << (bits-1)), (1 << (bits-1))-1) if signed else (0, (1 << bits)-1)
        return {"value": wrap(value, bits, signed), "valid": low <= value <= high}
    if op == "abs_s64":
        checked(a, 64)
        return {"value": abs(a), "valid": True}
    if op == "signextend_s16_i64":
        checked(a, 16)
        return {"value": a, "valid": True}
    if op == "cmp_s64":
        checked(a, 64); checked(b, 64)
        return {"less": a < b, "equal": a == b, "valid": True}
    if op == "max_s64":
        checked(a, 64); checked(b, 64)
        return {"value": max(a, b), "valid": True}
    if op in ("align_s32_i64", "shl_s64_s128", "shl_u128"):
        bits, outbits, signed, maximum = ((32, 64, True, 63) if op == "align_s32_i64" else
                                          (64, 128, True, 127) if op == "shl_s64_s128" else
                                          (128, 128, False, 127))
        need(0 <= shift <= maximum, "micro shift domain")
        checked(a, bits) if signed else need(0 <= a < 1 << bits, "U128 shift input")
        value = a << shift
        low, high = (-(1 << (outbits-1)), (1 << (outbits-1))-1) if signed else (0, (1 << outbits)-1)
        return {"value": wrap(value, outbits, signed), "valid": low <= value <= high}
    if op in ("rne_s64_i32", "rne_s128_i32"):
        bits = 64 if op == "rne_s64_i32" else 128
        checked(a, bits)
        need(0 <= shift <= 128, "RNE micro shift domain")
        value = shift_rne(a, shift)
        return {"value": value, "valid": -(1 << 31) <= value < 1 << 31}
    if op == "isqrt_u128":
        need(0 <= a < 1 << 128, "U128 sqrt input")
        return {"value": math.isqrt(a), "valid": True}
    if op == "udiv_u128":
        need(0 <= a < 1 << 128 and 0 <= b < 1 << 128, "U128 division input")
        return {"valid": False} if b == 0 else {"quotient": a//b, "remainder": a % b, "valid": True}
    if op == "div_rne_s128_u64_i32":
        checked(a, 128)
        need(0 <= b < 1 << 64, "unsigned denominator domain")
        if b == 0:
            return {"valid": False}
        value = divided_rne(a, b, 128)
        return {"value": value, "valid": -(1 << 31) <= value < 1 << 31}
    raise ValueError("uncalibrated micro operation")


class LiveReplay:
    def __init__(self):
        self.case = None
        self.completed = []

    def begin(self, case):
        need(self.case is None and case and case not in {v["case"] for v in self.completed}, "unique serial micro case")
        self.case, self.mem, self.live, self.allocations = case, [None]*FRAME, set(), {}
        self.actions, self.reads, self.writes, self.loads, self.peak = 0, 0, 0, 0, 0
        self.result_reads, self.outputs = 0, {}
        self.hist, self.topology = Counter(), hashlib.sha256()

    def topology_record(self, record):
        self.topology.update((" ".join(map(str, record))+"\n").encode())

    def value(self, ref):
        if ref < 0:
            need(-256 <= ref <= -1, "byte immediate domain")
            return -ref-1
        need(ref in self.live and self.mem[ref] is not None, "live initialized micro operand")
        return self.mem[ref]

    def line(self, line):
        fields = line.strip().split()
        need(bool(fields), "nonempty micro program line")
        kind = fields[0]
        if kind == "B":
            need(len(fields) == 2, "micro begin record")
            self.begin(fields[1]); self.topology_record([kind]); return
        need(self.case is not None, "micro action outside case")
        if kind == "M":
            need(len(fields) == 4, "micro allocation record")
            start, size = map(int, fields[1:3])
            need(start >= 0 and size > 0 and start+size <= FRAME and start not in self.allocations
                 and not (set(range(start, start+size)) & self.live), "finite nonalias micro allocation")
            self.allocations[start] = (size, fields[3])
            self.live.update(range(start, start+size))
            for i in range(start, start+size):
                self.mem[i] = None
            self.peak = max(self.peak, len(self.live))
            self.topology_record(fields); return
        if kind == "I":
            need(len(fields) == 3, "micro input record")
            address, value = map(int, fields[1:])
            need(address in self.live and self.mem[address] is None and 0 <= value < 256 and self.actions == 0,
                 "only initialized input bytes before arithmetic, no injected intermediate")
            self.mem[address] = value; self.loads += 1
            self.topology_record([kind, address]); return
        if kind == "F":
            need(len(fields) == 3, "micro free record")
            start, size = map(int, fields[1:])
            need(start in self.allocations and self.allocations[start][0] == size, "free complete live micro allocation")
            del self.allocations[start]
            for address in range(start, start+size):
                self.live.remove(address); self.mem[address] = None
            self.topology_record([kind, start, size]); return
        if kind == "A":
            need(len(fields) == 12, "complete restricted ALU action")
            op, ra, rb, rc, rd, rh, av, bv, cv, lo, hi = map(int, fields[1:])
            need((av, bv, cv) == (self.value(ra), self.value(rb), self.value(rc)), "actual live-store dependency, not expected-value injection")
            computed = byte_action(op, av, bv, cv)
            need(computed == (lo, hi), "independent restricted byte/S8 ALU result")
            for address, value in ((rd, computed[0]), (rh, computed[1])):
                if address != -1:
                    need(address in self.live, "micro output finite allocation")
                    self.mem[address] = value; self.writes += 1
            self.actions += 1; self.hist[str(op)] += 1
            self.reads += sum(ref >= 0 for ref in (ra, rb, rc))
            self.topology_record([kind, op, ra, rb, rc, rd, rh]); return
        if kind == "O":
            need(len(fields) == 5 and fields[1] not in self.outputs and fields[2] in ("0", "1"), "typed unique micro output")
            refs = list(map(int, fields[3].split(",")))
            wanted = list(map(int, fields[4].split(",")))
            need(refs and len(refs) == len(wanted) and all(v >= 0 for v in refs), "output live addresses")
            actual = [self.value(address) for address in refs]
            need(actual == wanted, "output reads actual causal live-store bytes")
            value = int.from_bytes(bytes(actual), "little", signed=fields[2] == "1")
            if fields[1] in ("valid", "less", "equal"):
                need(len(refs) == 1 and value in (0, 1), "published one-byte boolean")
                value = bool(value)
            self.outputs[fields[1]] = value
            self.result_reads += len(refs)
            self.topology_record(fields[:4]); return
        if kind == "E":
            need(len(fields) == 2 and fields[1] == self.case, "micro case terminator")
            self.topology_record([kind])
            record = {"case": self.case, "actions": self.actions, "byte_store_reads": self.reads,
                      "byte_store_writes": self.writes, "input_load_bytes": self.loads, "scratch_peak_bytes": self.peak,
                      "primitive_opcodes": dict(self.hist), "topology_sha256": self.topology.hexdigest(),
                      "result_read_bytes": self.result_reads, "outputs": self.outputs,
                      "live_final": {str(i): self.mem[i] for i in sorted(self.live)}}
            self.completed.append(record); self.case = None
            return record
        raise ValueError("unknown micro trace record")


def replay_lines(lines):
    replay = LiveReplay()
    for line in lines:
        replay.line(line)
    need(replay.case is None and bool(replay.completed), "complete finite micro trace")
    return replay.completed
