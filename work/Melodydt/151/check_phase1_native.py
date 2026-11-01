#!/usr/bin/env python3
"""Source-derived opcode/port/trace cross-checks; no RTL simulation."""
import argparse
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
from build_phase1_native import TOPS, contract_errors, parse_ports, port_signature, read_json, sha, write_json


def command_labels(source, selector):
    body = source.split("case(" + selector + ")", 1)[1].split("endcase", 1)[0]
    labels = re.findall(r"^\s*(\d+(?:,\d+)*)\s*:", body, re.M)
    return set(int(code) for label in labels for code in label.split(","))


def check(root, contract_path):
    root, contract_path = Path(root), Path(contract_path)
    c = read_json(contract_path)
    errors = contract_errors(root, c)
    assert not errors, errors
    required_macros = set("MNEGRST")
    assert set(c["macros"]) == required_macros
    total_ports = 0
    channel_checks = 0
    for macro, (path, module) in TOPS.items():
        raw = (root / path).read_text(encoding="utf-8")
        native = parse_ports(raw, module)
        recorded = c["macros"][macro]["ports"]
        assert port_signature(native) == port_signature(recorded)
        assert [p["declaration_line"] for p in native] == [p["declaration_line"] for p in recorded]
        ports = {p["name"]: p for p in recorded}
        for name in ("clk", "reset"):
            assert ports[name]["direction"] == "input" and ports[name]["width"] == 1
        for p in recorded:
            assert p["unique_driving_owner_contract"]
        for channel in c["macros"][macro]["channels"]:
            for field in ("valid_or_request", "ready_or_take"):
                name = channel[field]
                assert name in ports and ports[name]["width"] == 1, (macro, channel["name"], name)
            channel_checks += 1
        if macro in ("M", "N", "R"):
            labels = command_labels(raw, "cmd_op")
            assert set(int(k) for k in c["macros"][macro]["operations"]) == labels
        if macro == "E":
            labels = command_labels(raw, "op")
            assert labels == set(range(12)) | {13}
            assert "if(op==12)begin" in raw and "if(in_op>13)begin" in raw
            assert set(int(k) for k in c["macros"][macro]["operations"]) == set(range(14))
        total_ports += len(recorded)
    assert total_ports == 149
    # Separate endpoint-level consequences, independently stated from protocols.
    ps = {m: {p["name"]: p for p in c["macros"][m]["ports"]} for m in TOPS}
    assert ps["M"]["a_data"]["width"] == 128 and ps["M"]["b_data"]["width"] == 512
    assert ps["M"]["rsp_data"]["width"] == 128
    assert ps["N"]["cmd_count"]["width"] == 4
    for m in ("E", "G"):
        assert not any("count" in name or "mask" in name for name in ps[m])
        assert c["macros"][m]["count_port"] is False
    assert ps["E"]["out_data"]["width"] == 128 and ps["G"]["out_data"]["width"] == 32
    assert "original same-group S16 score" in c["macros"]["N"]["operations"]["3"]["input_schema"]
    assert "exact U16 EXP" in c["macros"]["N"]["operations"]["6"]["input_schema"]
    assert c["macros"]["G"]["functions"]["1"]["ungated_output_F"] == 14
    assert c["macros"]["G"]["functions"]["1"]["gated_output_F"] == 10
    assert c["macros"]["R"]["identity"]["native_width_bits"] == 32
    assert c["macros"]["R"]["commit_barrier"]["post_commit_revoke_rolls_back"] is False
    assert "rsp_saturated" not in ps["R"]
    assert ps["T"]["begin_owner"]["width"] == 2
    assert c["macros"]["T"]["identity"]["native_authentication"] is False
    assert "commit_error" not in ps["T"] and "rsp_valid" not in ps["T"]
    assert c["macros"]["T"]["responses"]["commit_error"] is False
    assert "rsp_error" not in ps["S"] and "done_error" in ps["S"]
    assert c["macros"]["S"]["loader"]["completion_is_compute_done"] is False
    assert c["scope"]["common_base_frozen"] is False
    assert c["scope"]["RTL_combination_verified"] is False

    trace_refs = 0
    def check_traces(node):
        nonlocal trace_refs
        if isinstance(node, dict):
            if "trace_ids" in node:
                for name in node["trace_ids"]:
                    assert name in c["source_traces"], name
                    trace_refs += 1
            for value in node.values():
                check_traces(value)
        elif isinstance(node, list):
            for value in node:
                check_traces(value)
    check_traces(c["macros"])
    for anchor in c["source_anchors"].values():
        lines = (root / anchor["path"]).read_text(encoding="utf-8").splitlines()
        assert anchor["literal"] in lines[anchor["line"] - 1]
    for f in contract_path.parent.iterdir():
        if f.is_file() and f.suffix in (".json", ".md", ".py"):
            assert b"\r\n" not in f.read_bytes(), str(f)
            f.read_bytes().decode("utf-8")
    return {"result": "PASS", "scope": "native source/contract static consistency, not temporal/numeric RTL verification",
            "port_count": total_ports, "macro_count": 7, "channels_checked": channel_checks,
            "opcode_tables_from_source_checked": ["M", "N", "R", "E"],
            "source_anchor_count": len(c["source_anchors"]), "trace_references_checked": trace_refs,
            "core_source_files": len(c["source_provenance"]),
            "contract_sha256": sha(contract_path), "checker_sha256": sha(Path(__file__)),
            "new_system_RTL": 0, "RTL_simulations": 0, "physical_experiments": 0}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    result = check(args.root, args.contract)
    write_json(args.output, result)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
