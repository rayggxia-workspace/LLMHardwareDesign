"""Read all bytes, validate complete paired evidence, and optionally replay."""
import argparse
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
from study import (ARMS, HERE, WORKLOADS, assert_contract, check, classify_group, demands,
                   digest, make_inventory, materialize, route, seeded_mapping, summarize,
                   validate, validate_mapping)
from run_ablation import check_config, expected_keys, oracle_records

ROOT = HERE.parents[2]


def verify_cut(base, nets, certificate):
    """Check a closed cut directly, without the producer's traversal algorithm."""
    net = next(n for n in nets if n["driver"] == certificate["driver"])
    driver, sinks = net["driver"], set(net["sinks"])
    blocked = {c for c, info in base["components"].items()
               if (info["driver"] is not None and c != driver)
               or (info["kind"] == "input" and c not in sinks)}
    region = set(certificate["reachable_components"])
    assert driver in region and region <= set(base["components"]) and not region & blocked
    missing = sinks - region
    assert missing and sorted(missing) == certificate["unreachable_sinks"]
    for connector in base["connectors"].values():
        a, b = [base["taps"][connector[key]]["component"] for key in ("a", "b")]
        if a not in blocked and b not in blocked:
            assert (a in region) == (b in region), "certificate is not a closed cut"


def verify(folder, replay=False):
    folder = Path(folder).resolve()
    manifest = json.loads((folder / "manifest.json").read_bytes())
    assert not manifest["source_dirty"], "dirty development run is not formal evidence"
    assert {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()} == {
        *manifest["files"], "manifest.json"}, "unindexed or missing output"
    for name, info in manifest["files"].items():
        path = (folder / name).resolve()
        assert path.is_relative_to(folder)
        data = path.read_bytes()
        assert len(data) == info["bytes"] and hashlib.sha256(data).hexdigest() == info["sha256"], name
    for name, expected in manifest["source_sha256"].items():
        path = (ROOT / name).resolve()
        assert path.is_relative_to(ROOT)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
        committed = subprocess.check_output(["git", "show", manifest["source_commit"] + ":" + name], cwd=ROOT)
        assert hashlib.sha256(committed).hexdigest() == expected, "source is not from declared commit: " + name
    cfg_bytes = (folder / "campaign.json").read_bytes()
    cfg = json.loads(cfg_bytes)
    check_config(cfg)
    assert hashlib.sha256(cfg_bytes).hexdigest() == manifest["config_sha256"]
    assert cfg_bytes == (HERE / "campaign.json").read_bytes()
    assert manifest["input_version"] == cfg["input_version"]
    assert digest(json.loads((folder / "workloads.json").read_bytes())) == digest(WORKLOADS) == manifest["workloads_sha256"]
    rows, checks, cuts, seen_keys = [], 0, 0, set()
    for tracks, span, access in itertools.product(cfg["tracks"], cfg["spans"], cfg["original_access"]):
        variant = f"t{tracks}-s{span}-a{access}"
        saved = json.loads((folder / "inventories" / (variant + ".json")).read_bytes())
        master, overlays = make_inventory(tracks, span, access, cfg["wire_capacity"], cfg["access_multiplier"])
        assert saved == {"master": master, "overlays": overlays}
        bases = assert_contract(master, overlays)
        per_variant = [json.loads(line) for line in (folder / (variant + "-cases.jsonl")).read_text(encoding="utf-8").splitlines()]
        by_group = {}
        for row in per_variant:
            key = (row["variant"], row["workload"], row["seed"], row["arm"])
            assert row["variant"] == variant and key in expected_keys(cfg) and key not in seen_keys
            seen_keys.add(key)
            arm, name, seed = row["arm"], row["workload"], row["seed"]
            workload, base = WORKLOADS[name], bases[arm]
            assert row["prior_split_label"] == workload["split"]
            assert row["mapping"] == seeded_mapping(workload, seed)
            assert validate_mapping(base, workload, row["mapping"])["valid"]
            assert row["master_sha256"] == digest(master)
            assert row["overlay_sha256"] == digest(overlays[arm])
            assert row["effective_sha256"] == digest(base)
            assert row["method"] == cfg["method"] and row["route_attempt_budget"] == 14
            assert row["runtime_seconds"] >= 0
            nets = demands(workload, row["mapping"])
            if row["raw_solution"] is not None:
                assert row["knowledge"] == "routed" and row["imported_witness"] is None
                assert validate(base, nets, row["raw_solution"]) == row["validation"] and row["validation"]["valid"]
                assert check(name, workload, row["mapping"], base, row["raw_solution"], seed) == row["numeric"]
                checks += 1
            else:
                assert "validation" not in row and "numeric" not in row
            for certificate in row["no_path_certificates"]:
                verify_cut(base, nets, certificate)
                cuts += 1
            if row["imported_witness"]:
                witness = row["imported_witness"]
                assert row["raw_solution"] is None and row["knowledge"] == "known_feasible_heuristic_miss"
                assert validate(base, nets, witness["solution"]) == witness["validation"] and witness["validation"]["valid"]
                assert check(name, workload, row["mapping"], base, witness["solution"], seed) == witness["numeric"]
                checks += 1
            if replay:
                assert route(base, nets, cfg["method"], seed, cfg["random_order_trials"]) == row["raw_solution"], key
            by_group.setdefault((name, seed), []).append(row)
        assert set(by_group) == set(itertools.product(cfg["workloads"], cfg["seeds"]))
        for group in by_group.values():
            assert len(group) == 4 and {r["arm"] for r in group} == set(ARMS)
            assert all(r["mapping"] == group[0]["mapping"] for r in group)
            by_arm = {r["arm"]: r for r in group}
            for row in group:
                if row["imported_witness"]:
                    imported = row["imported_witness"]
                    source = by_arm[imported["source_arm"]]
                    assert source["raw_solution"] is not None
                    assert imported["solution"]["connectors"] == source["raw_solution"]["connectors"]
                    assert imported["source_effective_sha256"] == source["effective_sha256"]
            assert classify_group(deepcopy(group), bases) == group
        rows.extend(per_variant)
    assert seen_keys == expected_keys(cfg) and len(rows) == len(seen_keys) == 384
    oracle_rows = json.loads((folder / "oracle.json").read_bytes())
    assert oracle_rows == oracle_records(), "exact controls or witness costs changed"
    actual = json.loads((folder / "summary.json").read_bytes())
    calculated = summarize(rows, oracle_rows)
    assert actual.pop("elapsed_seconds") >= 0 and actual == calculated
    assert calculated["numeric_checks"] == checks
    return {"status": "PASS", "files": len(manifest["files"]), "cases": len(rows),
            "paired_groups": calculated["paired_groups"], "numeric_checks": checks,
            "cut_certificates": cuts, "oracle_rows": len(oracle_rows),
            "deterministic_replay": replay, "source_commit": manifest["source_commit"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.run_dir, args.replay), indent=2))
