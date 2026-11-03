# -*- coding: utf-8 -*-
"""Bounded integer/protocol reference for frozen 643c6012 M/S-loader/T.

Not a complete RTL model: M commands are atomic, loader is a layout/read-order
oracle (not a queue/arbitration model), and T alone has behavioral clock steps.
No floating point, model quantizer, system controller, or hardware qualification.
"""

S64_MIN, S64_MAX = -(1 << 63), (1 << 63) - 1


class ReferenceDomainError(ValueError):
    """The Python caller requested an unsupported/out-of-pin-domain instance."""


def pin(value, bits, name):
    if type(value) is not int or not 0 <= value < (1 << bits):
        raise ReferenceDomainError("PORT_DOMAIN: {} must be U{}".format(name, bits))
    return value


def signed(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def fits(value, bits):
    return -(1 << (bits - 1)) <= value < (1 << (bits - 1))


def rne_right(value, shift):
    """Arithmetic floor quotient plus ties-to-even increment, including negatives."""
    if type(value) is not int or not fits(value, 64):
        raise ReferenceDomainError("RNE input must be S64")
    pin(shift, 6, "right_shift")
    if shift == 0:
        return value
    divisor = 1 << shift
    quotient, remainder = divmod(value, divisor)
    half = divisor >> 1
    return quotient + int(remainder > half or (remainder == half and quotient & 1))


def pack_fields(values, bits):
    return sum((value & ((1 << bits) - 1)) << (bits * i)
               for i, value in enumerate(values))


def hex128(value):
    return "0x{:032x}".format(value)


def response(data=0, error=False, saturated=False):
    return {"data": data, "data_hex": hex128(data),
            "error": bool(error), "saturated": bool(saturated)}


def read_formatted(values, shift, width):
    """op5 arithmetic only: four S64 -> four sign-extended S32 containers."""
    if len(values) != 4 or width not in (0, 1, 2):
        raise ReferenceDomainError("op5 requires four lanes and width 0/1/2")
    bits = (8, 16, 32)[width]
    low, high = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    rounded = [rne_right(v, shift) for v in values]
    clamped = [max(low, min(high, v)) for v in rounded]
    result = response(pack_fields(clamped, 32), saturated=clamped != rounded)
    result.update({"lanes_s32": clamped, "rounded": rounded})
    return result


def digits(value, wide):
    """M's signed radix-128 decomposition, NOT two unsigned bytes."""
    if not fits(value, 16 if wide else 8):
        raise ReferenceDomainError("input does not fit selected signed format")
    if not wide:
        return [value]
    raw = value & 65535
    return [raw & 127, (raw >> 7) & 127, signed(raw >> 14, 2)]


def decode_exec(index, data):
    pin(index, 6, "cmd_index")
    pin(data, 64, "cmd_data")
    d = {"bank": index >> 5, "fmt_a": data & 1,
         "fmt_b": (data >> 1) & 1, "clear": (data >> 2) & 1,
         "last_k": (data >> 4) & 15, "active_n": (data >> 8) & 15,
         "tiles": (data >> 12) & 7, "rows": (data >> 15) & 15}
    d["legal"] = (index & 31 == 0 and data >> 19 == 0 and data & 8 == 0
                  and 1 <= d["last_k"] <= 8 and 1 <= d["active_n"] <= 8
                  and 1 <= d["tiles"] <= 4 and 1 <= d["rows"] <= 8)
    return d


def encode_exec(bank, fmt_a, fmt_b, clear, last_k, active_n, tiles, rows):
    for name, value, width in (("bank", bank, 1), ("fmt_a", fmt_a, 1),
                               ("fmt_b", fmt_b, 1), ("clear", clear, 1),
                               ("last_k", last_k, 4), ("active_n", active_n, 4),
                               ("tiles", tiles, 3), ("rows", rows, 4)):
        pin(value, width, name)
    return (bank << 5, fmt_a | (fmt_b << 1) | (clear << 2) | (last_k << 4)
            | (active_n << 8) | (tiles << 12) | (rows << 15))


class MReference:
    """Atomic M command oracle, with real A/B valid/format and one result set.

    No timing, bank-ready/cycle modeling, op12 diagnostics or partial-slot reuse.
    Values are unknown until loaded/committed; CLEAR invalidates, not zero-fills.
    """

    def __init__(self):
        self.a, self.b, self.b_valid = {}, {}, {}
        self.merged, self.result_n = {}, {}
        self.factor, self.left_shift = 1, 0
        self.last_partials = None

    def load_a(self, bank, row, tile, wide, data):
        for name, value, width in (("a_bank", bank, 1), ("a_row", row, 3),
                                   ("a_tile", tile, 2), ("a_wide", wide, 1),
                                   ("a_data", data, 128)):
            pin(value, width, name)
        bits = 16 if wide else 8
        self.a[(bank, row, tile)] = (wide, [signed(data >> (bits * i), bits) for i in range(8)])

    def load_b(self, bank, tile, wide, half, data):
        for name, value, width in (("b_bank", bank, 1), ("b_tile", tile, 2),
                                   ("b_wide", wide, 1), ("b_half", half, 1),
                                   ("b_data", data, 512)):
            pin(value, width, name)
        key = (bank, tile)
        if (not wide and half) or (wide and half and
                                  not (self.b_valid.get(key, 0) & 1 and self.b[key][0])):
            raise ReferenceDomainError("B_NOT_READY: S16 half1 needs accepted half0; S8 half must be 0")
        if not wide:
            self.b[key] = (wide, [signed(data >> (8 * i), 8) for i in range(64)])
            self.b_valid[key] = 3
        else:
            lanes = list(self.b[key][1]) if half else [None] * 64
            lanes[32 * half:32 * half + 32] = [signed(data >> (16 * i), 16) for i in range(32)]
            self.b[key] = (wide, lanes)
            self.b_valid[key] = 3 if half else 1

    def command(self, op, index=0, data=0):
        pin(op, 4, "cmd_op")
        pin(index, 6, "cmd_index")
        pin(data, 64, "cmd_data")
        if op == 4:
            if index or data >> 21:
                return response(error=True)
            self.factor, self.left_shift = signed(data, 16), (data >> 16) & 31
            return response()
        if op == 6:
            if index or data:
                return response(error=True)
            self.a.clear(); self.b_valid.clear(); self.merged.clear(); self.result_n.clear()
            self.last_partials = None
            return response()
        if op == 11:
            if index >> 1 or data:
                return response(error=True)
            self.a = {k: v for k, v in self.a.items() if k[0] != index}
            self.b_valid = {k: v for k, v in self.b_valid.items() if k[0] != index}
            return response()
        if op == 3:
            row, pair = index >> 3, index & 7
            if row not in self.merged or pair >= 4 or data:
                return response(error=True)
            return response(pack_fields(self.merged[row][2 * pair:2 * pair + 2], 64))
        if op == 5:
            row, half = index >> 3, index & 7
            if row not in self.merged or half >= 2 or data >> 10 or (data >> 8) & 3 == 3 or data & 192:
                return response(error=True)
            return read_formatted(self.merged[row][4 * half:4 * half + 4], data & 63, (data >> 8) & 3)
        if op == 10:
            return self.execute(index, data)
        if op == 12:
            raise ReferenceDomainError("NOT_MODELLED: op12 finite partial-slot ownership/timing")
        return response(error=True)

    def execute(self, index, data):
        d = decode_exec(index, data)
        legal = d["legal"]
        bank = d["bank"]
        for tile in range(min(d["tiles"], 4)):
            key = (bank, tile)
            legal = legal and self.b_valid.get(key) == 3 and self.b.get(key, (None,))[0] == d["fmt_b"]
            for row in range(min(d["rows"], 8)):
                legal = legal and self.a.get((bank, row, tile), (None,))[0] == d["fmt_a"]
        if not d["clear"]:
            for row in range(min(d["rows"], 8)):
                legal = legal and row in self.merged and self.result_n.get(row) == d["active_n"]
        if not legal:
            return response(error=True)
        fault_rows, partials, fault_reasons = 0, [], []
        for row in range(d["rows"]):
            partial, partial_fault = [0] * 8, False
            # Match the tile/a-digit/b-digit accumulation order, wrapping S40.
            for tile in range(d["tiles"]):
                k_count = d["last_k"] if tile + 1 == d["tiles"] else 8
                aa, bb = self.a[(bank, row, tile)][1], self.b[(bank, tile)][1]
                for ia in range(3 if d["fmt_a"] else 1):
                    for ib in range(3 if d["fmt_b"] else 1):
                        for n in range(8):
                            reduced = sum(digits(aa[k], d["fmt_a"])[ia] *
                                          digits(bb[8 * n + k], d["fmt_b"])[ib]
                                          for k in range(k_count)) if n < d["active_n"] else 0
                            next_value = partial[n] + (reduced << (7 * (ia + ib)))
                            partial_fault |= not fits(next_value, 40)
                            partial[n] = signed(next_value, 40)
            old = [0] * 8 if d["clear"] else self.merged[row]
            aligned = [v * self.factor * (1 << self.left_shift) for v in partial]
            alignment_fault = any(not fits(v, 64) for v in aligned)
            # RTL still adds the truncated aligned value before rejecting the row.
            added = [old[n] + signed(aligned[n], 64) for n in range(8)]
            addition_fault = any(not fits(v, 64) for v in added)
            reasons = [name for name, yes in (("partial_s40", partial_fault),
                       ("alignment_s64", alignment_fault), ("addition_s64", addition_fault)) if yes]
            partials.append(partial)
            fault_reasons.append(reasons)
            if reasons:
                fault_rows |= 1 << row
            else:
                self.merged[row] = added
                self.result_n[row] = d["active_n"]
        self.last_partials = partials  # Diagnostic Python trace, NOT native op12 availability.
        result = response(fault_rows, error=bool(fault_rows))
        result.update({"fault_rows": fault_rows, "partials_s40": partials, "fault_reasons": fault_reasons})
        return result


def loader_descriptor(d):
    """Port-domain validation, then native legal predicate. Does not test M B identity."""
    widths = {"bank": 1, "rows": 4, "tiles": 3, "a_wide": 1, "b_wide": 1,
              "reuse_b": 1, "a_base": 10, "b_base": 10}
    if set(d) != set(widths):
        raise ReferenceDomainError("descriptor must contain exactly the eight native fields")
    for name, width in widths.items():
        pin(d[name], width, name)
    a_words = d["tiles"] * (8 if d["rows"] > 4 else 4)
    b_words = d["tiles"] * (8 if d["b_wide"] else 4)
    legal = (1 <= d["rows"] <= 8 and 1 <= d["tiles"] <= 4 and
             d["a_base"] % 4 == 0 and d["b_base"] % 4 == 0 and
             d["a_base"] + a_words <= 1024 and
             (d["reuse_b"] or d["b_base"] + b_words <= 1024))
    return {"legal": bool(legal), "done_error": not bool(legal),
            "a_words": a_words, "b_words_read": 0 if d["reuse_b"] else b_words,
            "checks_weight_identity": False, "checks_overlap": False}


def pack_a_tile(rows, wide):
    """Complete A tile groups; each real row occupies one full S128 word."""
    if not 1 <= len(rows) <= 8:
        raise ReferenceDomainError("A rows must be 1..8")
    bits = 16 if wide else 8
    for row in rows:
        if len(row) != 8 or any(not fits(v, bits) for v in row):
            raise ReferenceDomainError("A tile row must contain eight selected-format values")
    words = [pack_fields(row, bits) for row in rows]
    return words + [0] * ((8 if len(rows) > 4 else 4) - len(rows))


def pack_b_tile(columns, wide):
    """Eight output columns, eight K values each, n-major across half0 then half1."""
    bits = 16 if wide else 8
    if len(columns) != 8 or any(len(col) != 8 or any(not fits(v, bits) for v in col) for col in columns):
        raise ReferenceDomainError("B tile must be 8 n-major columns of eight values")
    packed = pack_fields([v for col in columns for v in col], bits)
    return [(packed >> (128 * i)) & ((1 << 128) - 1) for i in range(8 if wide else 4)]


def loader_plan(memory, d):
    """Exact request order/beat layout, no assertion about A-vs-B retirement cycles."""
    check = loader_descriptor(d)
    if not check["legal"]:
        return {"done_error": True, "reads": [], "a_beats": [], "b_beats": []}
    reads, a_beats, b_beats = [], [], []

    def read_line(word_addr, kind, tile, half=0):
        words = []
        for address in range(word_addr, word_addr + 4):
            if address not in memory:
                raise ReferenceDomainError("UNINITIALIZED_FIXTURE: S word {}".format(address))
            words.append(pin(memory[address], 128, "S word"))
        reads.append({"kind": kind, "tile": tile, "half": half,
                      "word_base": word_addr, "wide_addr": word_addr // 4})
        return pack_fields(words, 128)

    for tile in range(d["tiles"]):
        if not d["reuse_b"]:
            for half in range(2 if d["b_wide"] else 1):
                word = d["b_base"] + tile * (8 if d["b_wide"] else 4) + 4 * half
                b_beats.append({"bank": d["bank"], "tile": tile, "wide": d["b_wide"],
                                "half": half, "data": read_line(word, "B", tile, half)})
        for group in range(2 if d["rows"] > 4 else 1):
            word = d["a_base"] + tile * (8 if d["rows"] > 4 else 4) + 4 * group
            data = read_line(word, "A", tile, group)
            for lane in range(min(4, d["rows"] - 4 * group)):
                a_beats.append({"bank": d["bank"], "row": 4 * group + lane, "tile": tile,
                                "wide": d["a_wide"], "data": (data >> (128 * lane)) & ((1 << 128) - 1)})
    return {"done_error": False, "reads": reads, "a_beats": a_beats, "b_beats": b_beats}


class TReference:
    """Selected native T clock semantics; tick returns BEFORE outputs and AFTER state.

    This is executable behavioral intent, not RTL simulation or cycle equivalence.
    Only native two checked error conditions set sticky protocol_error. Busy BEGIN,
    premature commit/release and post-commit revoke are ignored, not invented errors.
    """
    EMPTY, FILL, SEALED, READ_REQ, READ_HOLD, RELEASE = range(6)
    NAMES = ("EMPTY", "FILL", "SEALED", "READ_REQ", "READ_HOLD", "RELEASE")
    SIGNAL_WIDTHS = {"reset": 1, "begin_valid": 1, "begin_owner": 2,
                     "begin_generation": 32, "begin_words": 10, "write_valid": 1,
                     "write_index": 10, "write_data": 128, "commit_valid": 1,
                     "revoke_valid": 1, "read_take": 1, "release_valid": 1}

    def __init__(self):
        self.payload = [None] * 384
        self._reset()

    def _reset(self):
        self.state = self.EMPTY
        self.received = self.cursor = self.held = 0
        self.owner = self.generation = self.word_count = 0
        self.protocol_error = False

    def outputs(self, signals=None):
        s = {name: 0 for name in self.SIGNAL_WIDTHS}
        s.update(signals or {})
        if set(s) != set(self.SIGNAL_WIDTHS):
            raise ReferenceDomainError("unknown T signal")
        for name, width in self.SIGNAL_WIDTHS.items():
            pin(s[name], width, name)
        live = not s["reset"]
        legal_size = 1 <= s["begin_words"] <= 384
        out = {"begin_ready": live and self.state == self.EMPTY and legal_size,
               "revoke_ready": live and self.state in (self.FILL, self.SEALED),
               "write_ready": live and self.state == self.FILL and not s["revoke_valid"] and s["write_index"] == self.received,
               "commit_ready": live and self.state == self.SEALED and not s["revoke_valid"],
               "read_valid": live and self.state == self.READ_HOLD,
               "release_ready": live and self.state == self.RELEASE,
               "busy": self.state != self.EMPTY,  # RTL busy is not reset-gated.
               "sealed": live and self.state == self.SEALED,
               "committed": live and self.state in (self.READ_REQ, self.READ_HOLD, self.RELEASE),
               "read_index": self.cursor, "read_data": self.held,
               "owner": self.owner, "generation": self.generation,
               "word_count": self.word_count, "protocol_error": self.protocol_error,
               "state": self.NAMES[self.state]}
        out["read_last"] = out["read_valid"] and self.cursor + 1 == self.word_count
        return s, out

    def tick(self, **signals):
        s, before = self.outputs(signals)
        fires = {name: bool(s[name + "_valid"] and before[name + "_ready"])
                 for name in ("begin", "write", "commit", "revoke", "release")}
        fires["read"] = bool(s["read_take"] and before["read_valid"])
        if s["reset"]:
            self._reset()
        else:
            if s["begin_valid"] and self.state == self.EMPTY and not 1 <= s["begin_words"] <= 384:
                self.protocol_error = True
            if s["write_valid"] and self.state == self.FILL and not s["revoke_valid"] and s["write_index"] != self.received:
                self.protocol_error = True
            if fires["revoke"]:
                self.state, self.received, self.cursor = self.EMPTY, 0, 0
            elif self.state == self.EMPTY and fires["begin"]:
                self.state, self.received, self.cursor = self.FILL, 0, 0
                self.owner, self.generation, self.word_count = s["begin_owner"], s["begin_generation"], s["begin_words"]
            elif self.state == self.FILL and fires["write"]:
                self.payload[self.received] = s["write_data"]
                self.received += 1
                if self.received == self.word_count:
                    self.state = self.SEALED
            elif self.state == self.SEALED and fires["commit"]:
                self.state = self.READ_REQ
            elif self.state == self.READ_REQ:
                self.held, self.state = self.payload[self.cursor], self.READ_HOLD
            elif self.state == self.READ_HOLD and fires["read"]:
                if self.cursor + 1 == self.word_count:
                    self.state = self.RELEASE
                else:
                    self.cursor += 1
                    self.held = self.payload[self.cursor]
            elif self.state == self.RELEASE and fires["release"]:
                self.state = self.EMPTY
        _, after = self.outputs(signals)
        return {"before": before, "fires": fires, "after": after}
