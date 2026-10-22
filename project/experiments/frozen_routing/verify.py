"""Read back a frozen run, verify hashes/electrical/function results, optionally replay."""
import argparse
import hashlib
import json
import itertools
from pathlib import Path
from model import WORKLOADS, demands, digest
from numeric import check
from oracle import solve
from router import route
from run import fixed_coverage
from validate import validate, validate_mapping


def verify(run_dir, replay=False):
    folder = Path(run_dir).resolve()
    manifest = json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
    for name, info in manifest["files"].items():
        path = (folder/name).resolve()
        if not path.is_relative_to(folder):
            raise AssertionError("output manifest path escapes run directory")
        data = path.read_bytes()
        assert len(data) == info["bytes"] and hashlib.sha256(data).hexdigest() == info["sha256"], name
    root = Path(__file__).resolve().parents[3]
    for name, expected in manifest["source_sha256"].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest() == expected, name
    assert manifest["workloads_sha256"] == digest(WORKLOADS)
    cfg = json.loads((folder/"campaign.json").read_text(encoding="utf-8"))
    rows, checks = [], 0
    for path in sorted(folder.glob("*-cases.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            rows.append(row)
            assert (row["status"] == "routed") == (row["solution"] is not None)
            base = json.loads((folder/"fabrics"/(row["variant"]+".json")).read_text(encoding="utf-8"))
            assert digest(base) == row["base_sha256"]
            w = WORKLOADS[row["workload"]]
            assert validate_mapping(base, w, row["mapping"])["valid"]
            nets = demands(w, row["mapping"])
            if row["solution"] is not None:
                actual = validate(base, nets, row["solution"], row["base_sha256"])
                assert actual == row["validation"] and actual["valid"]
                assert check(row["workload"], w, row["mapping"], base, row["solution"], row["seed"]) == row["numeric"]
                checks += 1
            if replay:
                again = route(base, nets, row["method"], row["seed"], cfg["multi_order_trials"])
                assert again == row["solution"], (row["variant"], row["workload"], row["seed"], row["method"])
    baseline = json.loads((folder/"fixed-baseline.json").read_text(encoding="utf-8"))
    selected = {}
    for row in baseline:
        base = json.loads((folder/"fabrics"/(row["variant"]+".json")).read_text(encoding="utf-8"))
        solution = row["solution"]
        assert selected.setdefault(row["variant"], solution) == solution  # one wiring for every graph
        assert validate(base, [], solution, row["base_sha256"])["valid"]
        covered = fixed_coverage(base, solution["connectors"], {row["workload"]: WORKLOADS[row["workload"]]})
        assert bool(covered) == (row["status"] == "supported")
        if covered:
            w = WORKLOADS[row["workload"]]
            assert validate_mapping(base, w, row["mapping"])["valid"]
            assert validate(base, demands(w, row["mapping"]), solution, row["base_sha256"]) == row["validation"]
            check(row["workload"], w, row["mapping"], base, solution, cfg["seeds"][0])
            checks += 1
    for variant, frozen_solution in selected.items():
        base = json.loads((folder/"fabrics"/(variant+".json")).read_text(encoding="utf-8"))
        candidates = {(): []}
        for row in rows:
            if row["variant"] == variant and row["workload"] in cfg["design_workloads"] and row["solution"]:
                keys = row["solution"]["connectors"]
                candidates[tuple(keys)] = keys
        singles = list(candidates.values())
        for a, b in itertools.combinations(singles, 2):
            joined = sorted(set(a) | set(b))
            if validate(base, [], {"base_sha256": digest(base), "connectors": joined})["valid"]:
                candidates[tuple(joined)] = joined
        design = {n: WORKLOADS[n] for n in cfg["design_workloads"]}
        scored = []
        for keys in candidates.values():
            covered = fixed_coverage(base, keys, design)
            cost = validate(base, [], {"base_sha256": digest(base), "connectors": keys})["custom_cost_units"]
            scored.append(((-len(covered), cost, tuple(keys)), keys, covered))
        _, best_keys, best_covered = min(scored, key=lambda s: s[0])
        assert best_keys == frozen_solution["connectors"], "fixed baseline not selected on design set"
        for row in baseline:
            if row["variant"] == variant:
                assert row["candidate_count"] == len(candidates)
                assert row["design_coverage"] == sorted(best_covered)
    exact_rows = json.loads((folder/"oracle.json").read_text(encoding="utf-8"))
    for row in exact_rows:
        result = solve(row["base"], row["nets"])
        assert (result is not None) == row["exact_feasible"]
        assert (result[0] if result else None) == row["exact_optimum"]
        assert (row["solution"] is not None) == row["heuristic_found"]
        if row["solution"]:
            val = validate(row["base"], row["nets"], row["solution"], digest(row["base"]))
            assert val["valid"] and val["custom_cost_units"] == row["cost"]
            assert result is not None and row["cost"] >= result[0]
        else:
            assert row["cost"] is None
        if replay:
            assert route(row["base"], row["nets"], row["method"], row["seed"],
                         cfg["multi_order_trials"]) == row["solution"]
    summary = json.loads((folder/"summary.json").read_text(encoding="utf-8"))
    assert summary["cases"] == len(rows) and summary["numeric_checks"] == checks
    assert summary["fixed_supported"] == sum(r["status"] == "supported" for r in baseline)
    assert summary["fixed_total"] == len(baseline)
    assert summary["oracle_instances"]*len(cfg["methods"]) == len(exact_rows)
    for method, stats in summary["oracle_by_method"].items():
        relevant = [r for r in exact_rows if r["method"] == method]
        assert stats["found"] == sum(r["heuristic_found"] for r in relevant)
        assert stats["missed_feasible"] == sum(r["exact_feasible"] and not r["heuristic_found"] for r in relevant)
    for method, stats in summary["by_method"].items():
        assert stats["total"] == sum(r["method"] == method for r in rows)
        assert stats["routed"] == sum(r["method"] == method and r["status"] == "routed" for r in rows)
    assert not manifest["source_dirty"], "development evidence cannot be promoted to clean source"
    return {"status": "PASS", "files": len(manifest["files"]), "cases": len(rows),
            "numeric_checks": checks, "oracle_rows": len(exact_rows), "deterministic_replay": replay,
            "source_commit": manifest["source_commit"]}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("run_dir")
    p.add_argument("--replay", action="store_true")
    a = p.parse_args()
    print(json.dumps(verify(a.run_dir, a.replay), indent=2))
