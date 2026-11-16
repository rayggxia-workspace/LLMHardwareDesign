"""Summarize actual RTL handshake timelines; never estimate model token/s."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path


def summarize(path):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for name in ("cycle", "slot", "generation", "kk", "use", "detail", "tag", "match"):
            row[name] = int(row[name])
    report = {"trace": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "events": dict(Counter(r["event"] for r in rows)), "last_observed_cycle": max(r["cycle"] for r in rows)}
    loads, uses, pending, rtts = {}, {}, {}, {"S128_read": [], "copy_P_write": [], "U_read": [], "result_S_write": []}
    for r in rows:
        key = (r["object_key"], r["slot"], r["generation"])
        use_key = (*key, r["use"])
        event = r["event"]
        if event == "CMD" and path.name.startswith("private_a_copy"):
            loads[key] = {"key": key[0], "slot": key[1], "generation": key[2], "kk": r["kk"], "planned_M_uses": r["use"], "accepted_cycle": r["cycle"], "S_request_cycles": [], "S_response_cycles": []}
        if event == "SREQ":
            loads[key]["S_request_cycles"].append(r["cycle"])
        if event == "SRSP" and r["match"]:
            loads[key]["S_response_cycles"].append(r["cycle"])
        if event == "LOAD_DONE":
            loads[key]["terminal_taken_cycle"] = r["cycle"]
            loads[key]["error"] = bool(r["detail"])
        if event == "MUSE":
            uses[use_key] = {"key": key[0], "slot": key[1], "generation": key[2], "kk": r["kk"], "use_sequence": r["use"], "use_accepted_cycle": r["cycle"], "A_accept_cycles": [], "A_steps": []}
        if event == "AVALID":
            uses[use_key]["first_A_valid_cycle"] = r["cycle"]
        if event == "ASTEP":
            uses[use_key]["A_accept_cycles"].append(r["cycle"])
            uses[use_key]["A_steps"].append(r["detail"])
        family = {"SREQ": "S128_read", "PWRITE": "copy_P_write", "UREQ": "U_read", "SWRITE": "result_S_write"}.get(event)
        if family:
            pending[(family, r["object_key"], r["slot"], r["tag"], r["detail"] if event == "SWRITE" else 0)] = r["cycle"]
        family = {"SRSP": "S128_read", "PACK": "copy_P_write", "URSP": "U_read", "SACK": "result_S_write"}.get(event)
        if family and r["match"]:
            ticket = (family, r["object_key"], r["slot"], r["tag"], r["detail"] if event == "SACK" else 0)
            assert ticket in pending, (path, "response without request", r)
            rtts[family].append(r["cycle"] - pending.pop(ticket))
    for load in loads.values():
        load["actual_words128_returned"] = len(load["S_response_cycles"])
        if not load.get("error", True):
            assert load["actual_words128_returned"] == 16
        if load["S_response_cycles"]:
            load["last_S_response_minus_command_cycles"] = load["S_response_cycles"][-1] - load["accepted_cycle"]
            load["S_service_span_cycles"] = load["S_response_cycles"][-1] - load["S_request_cycles"][0] + 1
    for use in uses.values():
        assert use["A_steps"] == list(range(8)), (path, "missing/reordered K16 step")
        use["first_A_valid_minus_use_accept_cycles"] = use["first_A_valid_cycle"] - use["use_accepted_cycle"]
        use["last_A_accept_minus_use_accept_cycles"] = use["A_accept_cycles"][-1] - use["use_accepted_cycle"]
        use["A_bytes"] = 256
        use["includes_testbench_backpressure"] = True
    report["loads"] = list(loads.values())
    report["M_uses"] = list(uses.values())
    report["actual_request_to_response_cycles"] = rtts
    report["rejected_response_events"] = dict(Counter(r["event"] for r in rows if r["event"] in ("SRSP", "PACK", "URSP", "NRSP", "SACK") and not r["match"]))
    if path.name.startswith("bounded_service_guard"):
        report["max_actual_result_slots_occupied"] = max(r["detail"] for r in rows if r["event"] == "RESULT_OCC")
        assert report["max_actual_result_slots_occupied"] == 2
    copies = []
    for key in sorted({r["object_key"] for r in rows if r["event"] == "UREQ"}):
        reqs = [r["cycle"] for r in rows if r["event"] == "UREQ" and r["object_key"] == key]
        commits = [r["cycle"] for r in rows if r["event"] == "PACK" and r["match"] and r["object_key"] == key]
        span = max(commits) - min(reqs) + 1
        copies.append({"key": key, "source_reads128": len(reqs), "destination_actual_ACKs": len(commits), "observed_span_cycles": span, "observed_source_bytes_per_cycle": len(reqs)*16/span, "native_source_port_upper_bound_bytes_per_cycle": 16, "includes_arbitration_and_testbench_S_latency": True})
    report["copy_objects"] = copies
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        raise SystemExit("produce protocol timing reports inside the allocated Slurm job")
    reports = [summarize(p) for p in sorted(args.root.glob("*.csv"))]
    assert reports, "no RTL timelines"
    out = {"schema": "issue250-native-control-cycle-timelines/1", "Slurm_job": os.environ["SLURM_JOB_ID"], "scope": "actual_candidate_RTL_handshakes_with_conservative_single_transaction_behavioral_S_test_fixture_not_MC_LC_real_SRAM_or_whole_model", "functional_clock_period_ns": 2, "STA_300MHz_proof": False, "nominal_frequency_if_used_later_Hz": 300000000, "conversion_to_token_s_or_energy": None, "traces": reports}
    args.output.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"timeline_reports": len(reports), "passed": True}))


if __name__ == "__main__":
    main()
