"""Run protocol admission cases on Slurm; outputs are protocol evidence only."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import time
from pathlib import Path

from audit_protocol import Violation, admit_header, check_contract, load_contract, replay


IDENTITY = {"generation": 1, "job": 250, "epoch": 1, "object_version": 1}


def event(op: str, **fields) -> dict:
    return {"op": op, "identity": IDENTITY.copy(), **fields}


def prefix(plans=(2, 1, 1)) -> list[dict]:
    return [
        event("BEGIN", words=16, pool_epoch=1, planned_loads=list(plans)),
        event("FILL_ACCEPT", transaction=10, base=0, words=4),
        event("FILL_ACCEPT", transaction=11, base=4, words=4),
        event("FILL_ACK", transaction=11, actual_commit=True),
        event("FILL_ACK", transaction=10, actual_commit=True),
        event("FILL_ACCEPT", transaction=12, base=8, words=4),
        event("FILL_ACCEPT", transaction=13, base=12, words=4),
        event("FILL_ACK", transaction=12, actual_commit=True),
        event("FILL_ACK", transaction=13, actual_commit=True),
        event("SEAL"),
    ]


def load(reader: int, sequence: int, *, finish=True) -> list[dict]:
    trace = [
        event("LOAD_PREPARE", reader=reader, sequence=sequence, pool_epoch=1, base=0, words=16, B_required=True),
        event("LOAD_ACCEPT", reader=reader, sequence=sequence),
    ]
    trace += [event("READ_RESERVE", reader=reader, sequence=sequence, beat=beat) for beat in range(4)]
    trace += [event("READ_ARRIVE", reader=reader, sequence=sequence, beat=beat) for beat in range(4)]
    trace += [event("A_COPY", reader=reader, sequence=sequence, beat=beat, half=half, words=2, actual_handshake=True) for beat in range(4) for half in range(2)]
    trace += [event("B_COMMITTED", reader=reader, sequence=sequence, actual_commit=True)]
    if finish:
        trace += [event("LOAD_DONE", reader=reader, sequence=sequence), event("LOAD_TAKE", reader=reader, sequence=sequence)]
    return trace


def positive(contract: dict) -> list[dict]:
    trace = prefix()
    trace += load(0, 1) + load(1, 1) + load(2, 1)
    trace += [event("END_READ", reader=1, last_sequence=1), event("END_READ", reader=2, last_sequence=1)]
    # P0 reads the same immutable object again, e.g. another projection/tile.
    trace += load(0, 2, finish=False)
    trace += [event("END_READ", reader=0, last_sequence=2), event("RELEASE_REQUEST")]
    # Closing the session does not erase the held LOAD completion.
    trace += [event("LOAD_DONE", reader=0, sequence=2), event("LOAD_TAKE", reader=0, sequence=2)]
    trace += [event("M_ACCEPT", reader=0, context=15, group=0, first=True, final=False, numeric_profile=contract["numeric"]["profile"])]
    # Shared A may be released during M arithmetic: the operand copy is local.
    trace += [event("RELEASE_DONE"), event("GROUP_RNE", reader=0, format="S32_Q16"), event("M_DONE", reader=0)]
    trace += [event("M_ACCEPT", reader=0, context=15, group=1, first=False, final=True, numeric_profile=contract["numeric"]["profile"])]
    trace += [event("GROUP_RNE", reader=0, format="S32_Q16"), event("M_DONE", reader=0)]
    trace += [event("STORE_ACCEPT", reader=0, context=15, transaction=20, words=2)]
    trace += [event("STORE_ACK", transaction=20, word=1, actual_commit=True), event("STORE_ACK", transaction=20, word=0, actual_commit=True)]
    trace += [event("CONTEXT_RELEASE", reader=0, context=15)]
    return trace


def insert_before(trace: list[dict], op: str, item: dict) -> list[dict]:
    out = copy.deepcopy(trace)
    out.insert(next(i for i, e in enumerate(out) if e["op"] == op), item)
    return out


def cases(contract: dict):
    good = positive(contract)
    yield "three_readers_repeated_load_early_A_release_two_S_ACKs", good, None
    fresh = event("BEGIN", words=4, pool_epoch=2, planned_loads=[0, 0, 0])
    fresh["identity"]["object_version"] = 2
    overlap = copy.deepcopy(good)
    overlap.insert(next(i for i, e in enumerate(overlap) if e["op"] == "RELEASE_DONE") + 1, fresh)
    for op, fields in [("FILL_ACCEPT", {"transaction": 10, "base": 0, "words": 4}), ("FILL_ACK", {"transaction": 10, "actual_commit": True}), ("SEAL", {}), ("RELEASE_REQUEST", {}), ("RELEASE_DONE", {})]:
        overlap.append({"op": op, "identity": fresh["identity"].copy(), **fields})
    yield "pool_refill_may_overlap_old_M_and_result_ACKs", overlap, None
    yield "SEAL_before_fill_ACK", prefix()[:3] + [event("SEAL")], "SEAL before every write ACK"
    bad = prefix()[:3] + [event("FILL_ACK", transaction=10, actual_commit=False)]
    yield "request_ready_is_not_fill_ACK", bad, "ready is not SRAM commit ACK"
    bad = prefix()[:3] + [event("FILL_ACCEPT", transaction=12, base=8, words=1)]
    yield "fill_outstanding_credit", bad, "fill credit exceeded"
    bad = prefix() + load(0, 1) + [event("END_READ", reader=0, last_sequence=1)]
    yield "first_read_does_not_end_repeated_use", bad, "END_READ hides unissued use"
    bad = prefix() + load(0, 1) + load(0, 2) + [event("END_READ", reader=0, last_sequence=2), event("RELEASE_REQUEST")]
    yield "idle_unstarted_P1_P2_not_drained", bad, "RELEASE before all reader end declarations"
    bad = good[:next(i for i, e in enumerate(good) if e["op"] == "RELEASE_REQUEST") + 1] + [event("RELEASE_DONE")]
    yield "release_must_wait_held_LOAD_terminal", bad, "RELEASE before source-read/FIFO/terminal drain"
    bad = prefix((1, 0, 0)) + load(0, 1) + [event("END_READ", reader=0, last_sequence=1)]
    bad += [event("LOAD_ACCEPT", reader=0, sequence=2, pool_epoch=1, base=0, words=2, B_required=False)]
    yield "LOAD_after_END_READ", bad, "reader is closed"
    bad = prefix() + load(0, 1)[:2] + [event("LOAD_DONE", reader=0, sequence=1)]
    yield "A_done_without_B_ACK_is_not_LOAD_done", bad, "LOAD join before A/B completion"
    bad = prefix() + [event("LOAD_PREPARE", reader=0, sequence=1, pool_epoch=1, base=15, words=2, B_required=True)]
    yield "LOAD_full_width_range_check", bad, "LOAD range"
    bad = prefix() + load(0, 1)[:2]
    bad += [event("READ_RESERVE", reader=0, sequence=1, beat=0), event("READ_ARRIVE", reader=0, sequence=1, beat=0)]
    bad += [event("A_COPY", reader=0, sequence=1, beat=0, half=0, words=2, actual_handshake=False)]
    yield "A_ready_is_not_operand_copy", bad, "A ready is not copy"
    pending = prefix() + load(0, 1)[:2]
    next_cmd = event("LOAD_PREPARE", reader=0, sequence=2, pool_epoch=1, base=0, words=16, B_required=True)
    yield "one_active_one_prepared_is_legal", pending + [next_cmd], None
    yield "no_third_command_slot", pending + [next_cmd, copy.deepcopy(next_cmd)], "prepared command slot exceeded"
    yield "prepared_command_cannot_accept_before_previous_retirement", pending + [next_cmd, event("LOAD_ACCEPT", reader=0, sequence=2)], "reader LOAD credit exceeded"
    reserved = pending + [event("READ_RESERVE", reader=0, sequence=1, beat=b) for b in range(4)]
    yield "inflight_reads_already_reserve_all_four_FIFO_slots", reserved + [event("READ_RESERVE", reader=0, sequence=1, beat=4)], "FIFO credit includes inflight reads"
    yield "prepare_does_not_reserve_SRAM_read_credit", pending + [next_cmd] + [event("READ_RESERVE", reader=0, sequence=1, beat=b) for b in range(4)], None
    bad = pending + [event("READ_RESERVE", reader=0, sequence=1, beat=0), event("READ_ARRIVE", reader=0, sequence=1, beat=0), event("A_COPY", reader=0, sequence=1, beat=0, half=1, words=2, actual_handshake=True)]
    yield "K16_even_odd_half_order", bad, "same-row K16 half/tag order"
    bad = copy.deepcopy(good)
    next(e for e in bad if e["op"] == "LOAD_ACCEPT")["identity"]["epoch"] = 257
    yield "same_low8_epoch_foreign_full_identity", bad, "stale/foreign full identity"
    bad = insert_before(good, "M_DONE", event("M_DONE", reader=0))
    # Remove the preceding RNE so the spurious completion really is premature.
    bad.pop(next(i for i, e in enumerate(bad) if e["op"] == "GROUP_RNE"))
    yield "M_done_requires_per_group_RNE", bad, "M done before group scale/RNE"
    bad = copy.deepcopy(good)
    next(e for e in bad if e["op"] == "M_ACCEPT" and not e["first"])["group"] = 2
    yield "continue_group_must_be_contiguous", bad, "group order/lifetime"
    bad = copy.deepcopy(good)
    bad.insert(next(i for i, e in enumerate(bad) if e["op"] == "STORE_ACK") + 1, event("CONTEXT_RELEASE", reader=0, context=15))
    yield "source_result_requires_second_S_ACK", bad, "release before every destination ACK"
    bad = copy.deepcopy(good)
    next(e for e in bad if e["op"] == "STORE_ACK")["actual_commit"] = False
    yield "destination_ready_is_not_commit", bad, "write acceptance is not ACK"
    # Cancellation retains accepted traffic and refuses a reset/forced timeout free.
    cancel = prefix()[:2] + [event("CANCEL")]
    yield "reset_before_accepted_fill_commit", cancel + [event("RESET")], "reset before complete transport drain"
    yield "halt_rejects_new_fill", cancel + [event("FILL_ACCEPT", transaction=11, base=4, words=4)], "accept after halt/quarantine"
    drained = cancel + [event("TIMEOUT"), event("FILL_ACK", transaction=10, actual_commit=True)]
    yield "timeout_cannot_force_reset", drained + [event("RESET")], "reset before complete transport drain"
    fresh = event("BEGIN", words=1, pool_epoch=1, planned_loads=[0, 0, 0])
    fresh["identity"] = {"generation": 2, "job": 250, "epoch": 1, "object_version": 1}
    yield "cancel_drain_retry_reset_refill_new_generation", drained + [event("DRAIN_RETRY"), event("RESET"), fresh], None
    yield "reset_does_not_allow_identity_reuse", cancel + [event("FILL_ACK", transaction=10, actual_commit=True), event("RESET")] + prefix()[:1], "identity generation/epoch reuse"
    pending_load = prefix((1, 0, 0)) + load(0, 1)[:2] + [event("CANCEL")]
    yield "cancel_preserves_accepted_LOAD_obligation", pending_load + [event("RESET")], "reset before complete transport drain"
    yield "cancel_drains_accepted_A_B_and_LOAD_terminal", pending_load + load(0, 1)[2:] + [event("RESET")], None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        raise SystemExit("Run protocol simulations through sbatch, per project rules.")
    if not 0 <= args.shard < args.shards:
        raise SystemExit("invalid shard")
    started, cpu_started = time.perf_counter(), time.process_time()
    c = load_contract()
    check_contract(c)
    results = []
    d = c["deployment"]
    header = {"native_abi_id": d["native_abi_id_candidate"], "topology_version": d["topology_version_candidate"], "capacity_version": d["capacity_version_candidate"], "numeric_profile": c["numeric"]["profile"], "layout_id": d["layout_id_candidate"]}
    admission_cases = [("candidate_header", header, False)]
    for field, value in [("native_abi_id", 65537), ("capacity_version", 0), ("numeric_profile", "legacy_S128"), ("layout_id", "old_tiles4")]:
        admission_cases.append(("reject_header_" + field, {**header, field: value}, True))
    for i, (name, candidate, must_reject) in enumerate(admission_cases):
        if i % args.shards != args.shard:
            continue
        rejection = None
        try:
            admit_header(candidate, c)
        except Violation as exc:
            rejection = str(exc)
        results.append({"name": name, "passed": (rejection is not None) == must_reject, "actual_rejection": rejection, "scope": "candidate_header_admission_not_binary_codec"})
    for i, (name, trace, expected) in enumerate(cases(c)):
        if i % args.shards != args.shard:
            continue
        try:
            result = replay(c, trace)
            actual = None
            counts = result.counts
        except Violation as exc:
            actual, counts = str(exc), None
        passed = actual is None if expected is None else actual is not None and expected in actual
        results.append({"name": name, "passed": passed, "expected_rejection": expected, "actual_rejection": actual, "trace_sha256": hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest(), "counters_if_admitted": counts})
    here = Path(__file__).parent
    report = {
        "schema": "shared-x-control-audit/1", "passed": all(r["passed"] for r in results),
        "coverage": "abstract_transaction_protocol_only_not_RTL_numeric_timing_or_physical",
        "slurm_job_id": os.environ["SLURM_JOB_ID"], "slurm_cpus_per_task": os.environ.get("SLURM_CPUS_PER_TASK"),
        "slurm_node": os.environ.get("SLURMD_NODENAME"), "shard": args.shard, "shards": args.shards,
        "python": platform.python_version(), "elapsed_seconds": time.perf_counter() - started,
        "process_CPU_seconds": time.process_time() - cpu_started,
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(here.glob("*.py"))},
        "contract_sha256": hashlib.sha256(here.joinpath("contract.json").read_bytes()).hexdigest(), "cases": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "cases": len(results), "shard": args.shard}))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
