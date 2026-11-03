#!/usr/bin/env python3
"""Independent bounded checks for the static planner. No RTL/model execution."""
import argparse
import collections
from fractions import Fraction
import json
from pathlib import Path
import sys

from lower_static_connection import COUNTS, digest, make_contract, read_json, rne, run_probes, write_json


def verify(root, output_dir):
    root, output_dir = Path(root), Path(output_dir)
    ledger = read_json(root / "work/Melodydt/151/edge-ledger.json")
    contract = make_contract(root)
    assert contract["coverage_denominators"] == COUNTS
    refs = contract["slot_source_references"]
    original = ledger["data_slots"] + ledger["controlled_parameter_slots"]
    assert len(refs) == 1081
    for a, b in zip(refs, original):
        for new, old in (("id", "id"), ("src", "src"), ("dst", "dst"),
                         ("recipe_id", "recipe_id"), ("source_status", "status"),
                         ("source_condition_ids", "condition_ids"),
                         ("source_extra_guard_ids", "extra_guard_ids"),
                         ("source_gap_ids", "gap_ids")):
            assert a[new] == b[old], (a["id"], new)
    assert len(contract["recipe_action_mapping"]) == 153
    assert len(contract["action_families"]) == 16
    for rid, mapping in contract["recipe_action_mapping"].items():
        for guard in ("semantic_guards", "state_guards", "mapping_guards"):
            assert mapping["retained_source_guards"][guard] == ledger["recipes"][rid][guard]
        assert "MISSING_NUMERIC" not in mapping["required_action_families"]
        assert set(mapping["required_action_families"]) <= set(contract["action_families"])
    # Check from destination semantics in the original slot catalog, independently
    # of the planner's mode branch. Raw score replay computes EXP using N3;
    # exact EXP replay normalizes using N6. A shared "replay" word is not enough.
    expected_target_ops = {"N.exp_score": 3, "N.soft_replay": 6}
    checked_native_recipes = set()
    replay_slot_checks = 0
    for slot in ledger["data_slots"]:
        if slot["dst"] not in expected_target_ops:
            continue
        mapping = contract["recipe_action_mapping"][slot["recipe_id"]]
        native = mapping["native_op_constraints"]
        assert len(native) == 1
        assert native[0]["macro"] == "N"
        assert native[0]["destination_role"] == slot["dst"]
        assert native[0]["op"] == expected_target_ops[slot["dst"]]
        assert "NATIVE_OP" in mapping["required_action_families"]
        if slot["dst"] == "N.exp_score":
            assert "EXP_REPLAY" not in mapping["required_action_families"]
        else:
            assert "EXP_REPLAY" in mapping["required_action_families"]
        checked_native_recipes.add(slot["recipe_id"])
        replay_slot_checks += 1
    assert len(checked_native_recipes) == 18  # Nine source schema classes for each target.
    assert replay_slot_checks == 46  # All23 source roles into each of the two targets.
    assert len(contract["sample_obligation_classification"]) == 96
    assert not any(x["model_compiled"] for x in contract["sample_obligation_classification"])
    assert all(contract["implementation_counts"][k] == 0 for k in contract["implementation_counts"])
    assert contract["scope"]["system_has_external_memory"] is True
    assert contract["scope"]["roles"] == "compile_time_only_not_generic_runtime_tags"

    # Fraction/__round__ is an independent exact-rational ties-even reference,
    # including negative halfway cases; not a second copy of bit-level formula.
    arithmetic_cases = 0
    for shift in range(11):
        for value in range(-1025, 1026):
            assert rne(value, shift) == round(Fraction(value, 1 << shift)), (value, shift)
            arithmetic_cases += 1
    assert [rne(x, 4) for x in (-40, -24, -8, 8, 24, 40)] == [-2, -2, 0, 0, 2, 2]
    assert 32768 - (1 << 16) == -32768  # Why EXP U16 cannot be signed probability bitcast.

    cases = read_json(Path(__file__).with_name("verification-cases.json"))["cases"]
    probes = run_probes(cases)
    assert probes["passed"] == probes["count"] == 37
    statuses = collections.Counter(x["plan"]["result"] for x in probes["results"])
    assert statuses["STATE_PENDING"] and statuses["MAPPING_PENDING"] and statuses["DATA_PENDING"]
    assert statuses["INSTANCE_REJECTED"] and statuses["ACTION_PLAN_CANDIDATE"]
    for row in probes["results"]:
        plan = row["plan"]
        assert plan["model_compiled"] is False and plan["system_RTL_implemented"] is False
        if plan["result"] == "INSTANCE_REJECTED":
            assert plan["pair_permanently_illegal"] is False

    saved = read_json(output_dir / "compile-lowering-contract.json")
    assert saved == contract, "Generated contract is stale; rerun planner"
    receipt = read_json(output_dir / "verification-receipt.json")
    for item in receipt["inputs"]:
        assert digest(root / item["path"]) == item["sha256"], "Source input changed"
    for item in receipt["artifacts"]:
        assert digest(output_dir / item["path"]) == item["sha256"], "Generated output changed"
    assert receipt["tool_sha256"] == digest(Path(__file__).with_name("lower_static_connection.py"))
    assert receipt["probe_cases_sha256"] == digest(Path(__file__).with_name("verification-cases.json"))
    for path in Path(__file__).parent.iterdir():
        if path.is_file() and path.suffix in (".py", ".json", ".md"):
            assert b"\r\n" not in path.read_bytes(), "Expected UTF8 LF: " + str(path)
    return {"result": "PASS", "scope": "static catalog/action/provenance and software integer checks only",
            "source_counts": COUNTS, "original_slot_refs_and_guards_checked": 1081,
            "recipe_guard_sets_checked": 153, "sample_refs_checked": 96,
            "native_N_replay_recipe_op_constraints_checked": len(checked_native_recipes),
            "native_N_replay_slot_destination_op_checks": replay_slot_checks,
            "bounded_probe_cases": 37, "probe_status_counts": dict(statuses),
            "exact_rational_rounding_cases": arithmetic_cases,
            "RTL_simulation": "NOT_EXECUTED", "physical_verification": "NOT_EXECUTED",
            "model_compilation": "NOT_PERFORMED"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    result = verify(args.root, args.output_dir)
    write_json(Path(args.output_dir) / "independent-check-results.json", result)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
