"""Independent transaction-trace checker for a NON-DEPLOYABLE candidate contract.

No cycle, numeric, RTL, power or physical model is provided. Events describe actual
handshakes/commits, never request-ready guesses. This checker is deliberately
separate from the existing compiler and production control implementations.
"""
from __future__ import annotations

import json
from pathlib import Path


class Violation(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Violation(message)


def check_contract(c: dict) -> None:
    require(c["schema"] == "shared-x-control-candidate/1", "wrong schema")
    require(not c["production_rtl_modified"], "preparation cannot claim production RTL")
    require(c["deployment"]["execution_instruction_bits"] == 64, "ISA width changed")
    require(c["storage"]["true_private_RW"] == 0, "unqualified private RW")
    require(c["storage"]["independent_full_X_bytes_per_P"] == 0, "duplicated X")
    require(not c["numeric"]["persistent_S128_or_S64"], "wide persistent state")
    require(c["pool"]["readers"] == 3, "candidate needs three readers")
    require(len(c["groups"]) == 9, "wrong compute-group count")
    require({g["kind"] for g in c["groups"]} == {"P", "U", "C", "F", "J"}, "wrong kinds")
    require(len({g["id"] for g in c["groups"]}) == 9, "duplicate group identity")
    services = c["services"]
    require(len({(s["resource"], s["service"], s["native_op"]) for s in services}) == len(services), "duplicate service")
    require(all(0 <= s["resource"] < 256 and 0 <= s["service"] < 256 and 0 <= s["native_op"] < 65536 for s in services), "descriptor field width")
    require(c["parameter_record"]["header_bytes"] + c["parameter_record"]["identity_bytes"] + c["parameter_record"]["service_payload_bytes"] == c["deployment"]["parameter_record_bytes"], "parameter size")


def admit_header(header: dict, contract: dict) -> None:
    """Candidate deployment admission only; not an instruction byte decoder."""
    d = contract["deployment"]
    expected = {"native_abi_id": d["native_abi_id_candidate"], "topology_version": d["topology_version_candidate"], "capacity_version": d["capacity_version_candidate"], "numeric_profile": contract["numeric"]["profile"], "layout_id": d["layout_id_candidate"]}
    require(header == expected, "ABI/topology/capacity/numeric/layout mismatch")


class Replay:
    """Bounded protocol obligations, not the proposed hardware implementation.

    Repeated LOADs are counted separately. END_READ is an explicit end-of-epoch
    declaration; seeing an idle reader or one completed LOAD never closes it.
    Result/destination-ACK lifetime is independent of shared-A read lifetime.
    """

    def __init__(self, contract: dict):
        check_contract(contract)
        self.c = contract
        self.state = "EMPTY"
        self.identity = None
        self.watermark = (-1, -1, -1)
        self.halted = False
        self.quarantine = False
        self.pending_fill = {}
        self.seen_fill = set()
        self.loads = {}
        self.prepared = {}
        self.contexts = {}
        self.busy = {}
        self.stores = {}
        self.seen_stores = set()
        self.bank_valid = [False] * 3
        self.bank_identity = [None] * 3
        self.counts = {"fill_commits": 0, "A_words_copied": 0, "S_commits": 0, "events": 0}

    def idle_transport(self) -> bool:
        return not (self.pending_fill or self.loads or self.busy or self.stores)

    def accept(self) -> None:
        require(not self.halted and not self.quarantine, "accept after halt/quarantine")

    def matching(self, e: dict) -> None:
        op = e["op"]
        expected = self.identity
        if op == "M_ACCEPT":
            expected = self.bank_identity[e["reader"]]
        elif op in ("GROUP_RNE", "M_DONE") and e["reader"] in self.busy:
            expected = self.busy[e["reader"]]["identity"]
        elif op in ("STORE_ACCEPT", "CONTEXT_RELEASE") and (e["reader"], e["context"]) in self.contexts:
            expected = self.contexts[(e["reader"], e["context"])]["identity"]
        elif op == "STORE_ACK" and e["transaction"] in self.stores:
            expected = self.stores[e["transaction"]]["identity"]
        require(e.get("identity") == expected, "stale/foreign full identity")

    def load(self, e: dict) -> dict:
        key = (e["reader"], e["sequence"])
        require(key in self.loads, "unknown LOAD")
        return self.loads[key]

    def step(self, e: dict) -> None:
        op = e["op"]
        if op == "BEGIN":
            self.accept()
            require(self.state == "EMPTY", "BEGIN on live object")
            ident = e["identity"]
            require(set(ident) == set(self.c["identity"]["full_fields"]), "incomplete identity")
            require(all(type(v) is int and 0 <= v < 2**32 for v in ident.values()), "identity width")
            watermark = (ident["generation"], ident["epoch"], ident["object_version"])
            require(watermark > self.watermark, "identity generation/epoch reuse")
            if self.busy or self.stores or self.contexts:
                require(all(ident[k] == self.identity[k] for k in ("generation", "job", "epoch")), "new job while old result lives")
            require(0 <= e["pool_epoch"] < 256, "pool epoch width")
            require(1 <= e["words"] <= self.c["pool"]["object_words128_max"], "object range")
            plans = e["planned_loads"]
            require(len(plans) == 3 and all(type(n) is int and 0 <= n <= 65535 for n in plans), "reader plans")
            self.identity = ident.copy()
            self.watermark = watermark
            self.pool_epoch = e["pool_epoch"]
            self.words, self.accepted_words, self.committed_words = e["words"], 0, 0
            self.seen_fill.clear()
            self.planned, self.issued = plans.copy(), [0] * 3
            self.closed = [n == 0 for n in plans]
            self.state = "FILL"
        else:
            self.matching(e)
            if op == "FILL_ACCEPT":
                self.accept()
                require(self.state == "FILL", "fill outside FILL")
                require(len(self.pending_fill) < self.c["pool"]["fill_outstanding_credit"], "fill credit exceeded")
                require(e["transaction"] not in self.seen_fill, "duplicate fill transaction")
                require(e["base"] == self.accepted_words, "nonsequential fill")
                require(1 <= e["words"] <= 4 and self.accepted_words + e["words"] <= self.words, "fill extent")
                self.pending_fill[e["transaction"]] = e["words"]
                self.seen_fill.add(e["transaction"])
                self.accepted_words += e["words"]
            elif op == "FILL_ACK":
                require(e.get("actual_commit") is True, "ready is not SRAM commit ACK")
                require(e["transaction"] in self.pending_fill, "unknown/duplicate fill ACK")
                words = self.pending_fill.pop(e["transaction"])
                self.committed_words += words
                self.counts["fill_commits"] += words
            elif op == "SEAL":
                self.accept()
                require(self.state == "FILL", "SEAL outside FILL")
                require(self.committed_words == self.words and not self.pending_fill, "SEAL before every write ACK")
                self.state = "SEALED"
            elif op == "LOAD_PREPARE":
                self.accept()
                r = e["reader"]
                require(self.state in ("FILL", "SEALED"), "prepare outside live object")
                require(0 <= r < 3 and not self.closed[r], "reader is closed")
                require(e["pool_epoch"] == self.pool_epoch, "pool epoch mismatch")
                require(e["sequence"] == self.issued[r] + 1 <= self.planned[r], "LOAD count/sequence")
                require(r not in self.prepared, "prepared command slot exceeded")
                require(0 <= e["base"] and 1 <= e["words"] and e["base"] + e["words"] <= self.words, "LOAD range")
                self.prepared[r] = {k: e[k] for k in ("sequence", "base", "words", "B_required")}
            elif op == "LOAD_ACCEPT":
                self.accept()
                r = e["reader"]
                require(self.state == "SEALED", "LOAD outside SEALED")
                require(0 <= r < 3 and not self.closed[r], "reader is closed")
                require(r in self.prepared and e["sequence"] == self.prepared[r]["sequence"], "LOAD not prepared")
                require(not any(k[0] == r for k in self.loads), "reader LOAD credit exceeded")
                require(r not in self.busy, "checker single abstract operand bank is in use")
                cmd = self.prepared.pop(r)
                self.loads[(r, e["sequence"])] = {"remaining": cmd["words"], "total": cmd["words"], "b": not cmd["B_required"], "terminal": False, "fifo": {}, "read_beats_seen": set()}
                self.issued[r] += 1
                self.bank_valid[r] = False
            elif op == "READ_RESERVE":
                # Reads belong to an already accepted LOAD. Halt stops new
                # LOAD acceptance, not the bounded provider work needed to
                # drain an existing service.
                load = self.load(e)
                require(len(load["fifo"]) < self.c["pool"]["reader_fifo_slots_candidate"], "FIFO credit includes inflight reads")
                beat = e["beat"]
                require(0 <= beat < (load["total"] + 3) // 4 and beat not in load["read_beats_seen"], "read beat identity/range")
                load["read_beats_seen"].add(beat)
                load["fifo"][beat] = {"arrived": False, "remaining": min(4, load["total"] - beat * 4), "next_half": 0}
            elif op == "READ_ARRIVE":
                load = self.load(e)
                require(e["beat"] in load["fifo"] and not load["fifo"][e["beat"]]["arrived"], "unreserved/duplicate read response")
                load["fifo"][e["beat"]]["arrived"] = True
            elif op == "A_COPY":
                load = self.load(e)
                require(not load["terminal"], "A after terminal")
                require(e["beat"] in load["fifo"] and load["fifo"][e["beat"]]["arrived"], "A before reserved read response")
                slot = load["fifo"][e["beat"]]
                require(e["half"] == slot["next_half"], "same-row K16 half/tag order")
                require(1 <= e["words"] <= 2 and e["words"] <= load["remaining"], "A beat/range")
                require(e["words"] == min(2, slot["remaining"]), "A pair incomplete")
                require(e.get("actual_handshake") is True, "A ready is not copy")
                slot["remaining"] -= e["words"]
                slot["next_half"] += 1
                if not slot["remaining"]:
                    del load["fifo"][e["beat"]]
                load["remaining"] -= e["words"]
                self.counts["A_words_copied"] += e["words"]
            elif op == "B_COMMITTED":
                load = self.load(e)
                require(not load["b"] and e.get("actual_commit") is True, "B duplicate/false commit")
                load["b"] = True
            elif op == "LOAD_DONE":
                load = self.load(e)
                require(not load["remaining"] and not load["fifo"] and load["b"], "LOAD join before A/B completion")
                require(not load["terminal"], "duplicate LOAD terminal")
                load["terminal"] = True
            elif op == "LOAD_TAKE":
                load = self.load(e)
                require(load["terminal"], "take before LOAD terminal")
                del self.loads[(e["reader"], e["sequence"])]
                self.bank_valid[e["reader"]] = True
                self.bank_identity[e["reader"]] = e["identity"].copy()
            elif op == "END_READ":
                r = e["reader"]
                require(0 <= r < 3 and not self.closed[r], "duplicate/invalid END_READ")
                require(e["last_sequence"] == self.issued[r] == self.planned[r], "END_READ hides unissued use")
                self.closed[r] = True
            elif op == "RELEASE_REQUEST":
                require(self.state == "SEALED" and all(self.closed), "RELEASE before all reader end declarations")
                self.state = "RELEASING"
            elif op == "RELEASE_DONE":
                require(self.state == "RELEASING" and not self.loads and not self.pending_fill and not self.prepared, "RELEASE before source-read/FIFO/terminal drain")
                self.state = "EMPTY"
            elif op == "M_ACCEPT":
                self.accept()
                r, ctx = e["reader"], e["context"]
                require(0 <= r < 3 and 0 <= ctx < self.c["storage"]["projection_contexts_per_P_candidate"], "M context range")
                require(self.bank_valid[r] and r not in self.busy, "M operands invalid or arithmetic busy")
                key = (r, ctx)
                old = self.contexts.get(key)
                if e["first"]:
                    require(old is None and e["group"] == 0, "first on live context")
                    old = {"next_group": 0, "final": False, "held": False, "identity": e["identity"].copy()}
                    self.contexts[key] = old
                require(old is not None and not old["final"] and e["group"] == old["next_group"], "group order/lifetime")
                require(all(old["identity"][k] == e["identity"][k] for k in ("generation", "job", "epoch")), "context belongs to another job")
                require(e["numeric_profile"] == self.c["numeric"]["profile"], "numeric profile mismatch")
                old["identity"] = e["identity"].copy()
                self.busy[r] = {"key": key, "final": e["final"], "rne": False, "identity": e["identity"].copy()}
            elif op == "GROUP_RNE":
                require(e["reader"] in self.busy and e["format"] == "S32_Q16", "missing group or wrong state format")
                self.busy[e["reader"]]["rne"] = True
            elif op == "M_DONE":
                require(e["reader"] in self.busy, "unknown M completion")
                b = self.busy[e["reader"]]
                require(b["rne"], "M done before group scale/RNE")
                ctx = self.contexts[b["key"]]
                ctx["next_group"] += 1
                ctx["final"] = b["final"]
                ctx["held"] = b["final"]
                del self.busy[e["reader"]]
            elif op == "STORE_ACCEPT":
                self.accept()
                key = (e["reader"], e["context"])
                require(key in self.contexts and self.contexts[key]["held"], "no held final result")
                require(e["transaction"] not in self.seen_stores and e["words"] > 0, "store identity/range")
                require(not any(s["key"] == key for s in self.stores.values()), "result already has pending destination")
                self.stores[e["transaction"]] = {"key": key, "remaining": set(range(e["words"])), "identity": e["identity"].copy()}
                self.seen_stores.add(e["transaction"])
            elif op == "STORE_ACK":
                require(e.get("actual_commit") is True, "write acceptance is not ACK")
                require(e["transaction"] in self.stores, "unknown store ACK")
                s = self.stores[e["transaction"]]
                require(e["word"] in s["remaining"], "duplicate/out-of-range store ACK")
                s["remaining"].remove(e["word"])
                self.counts["S_commits"] += 1
                if not s["remaining"]:
                    self.contexts[s["key"]]["held"] = False
                    del self.stores[e["transaction"]]
            elif op == "CONTEXT_RELEASE":
                key = (e["reader"], e["context"])
                require(key in self.contexts and self.contexts[key]["final"], "release incomplete context")
                require(not self.contexts[key]["held"], "release before every destination ACK")
                require(e["reader"] not in self.busy, "release while arithmetic busy")
                del self.contexts[key]
            elif op == "CANCEL":
                self.halted = True
            elif op == "TIMEOUT":
                require(self.halted, "timeout outside cancellation")
                self.quarantine = True
            elif op == "DRAIN_RETRY":
                require(self.quarantine and self.idle_transport(), "retry without drained quarantine")
                self.quarantine = False
            elif op == "RESET":
                require(self.halted and not self.quarantine and self.idle_transport(), "reset before complete transport drain")
                self.contexts.clear()
                self.prepared.clear()
                self.seen_stores.clear()
                self.bank_valid = [False] * 3
                self.bank_identity = [None] * 3
                self.state = "EMPTY"
                self.halted = False
            else:
                raise Violation("unknown event: " + op)
        self.counts["events"] += 1


def replay(contract: dict, events: list[dict]) -> Replay:
    audit = Replay(contract)
    for number, event in enumerate(events):
        try:
            audit.step(event)
        except (Violation, KeyError, TypeError) as exc:
            raise Violation(f"event {number} {event.get('op')}: {exc}") from exc
    return audit


def load_contract() -> dict:
    return json.loads(Path(__file__).with_name("contract.json").read_text(encoding="utf-8"))
