"""SHA-checked logical union of seven immutable Issue68 service shards.

No numerical/timing experiment is executed here. Scientific gzip bytes are
hardlinked unchanged; only deterministic metrics union and provenance are new.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import sys


ORGANIZATIONS = ("shared8", "shared2_6", "shared4_4", "shared6_2",
                 "split2_6", "split4_4", "split6_2")
GRID = {"ext_profiles": [1, 16], "tiles": [16, 32],
        "norm_routes": ["reread", "spill"], "strategies": ["fifo", "critical"]}
SCHEMA = "issue68-service/1"


def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for part in iter(lambda: f.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def descriptor(p):
    p = Path(p)
    return {"bytes": p.stat().st_size, "sha256": sha(p)}


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def checked_file(parent, name, desc):
    require(isinstance(name, str) and Path(name).name == name and "\\" not in name,
            "unsafe artifact name")
    p = parent / name
    require(p.is_file() and not p.is_symlink(), "missing/nonregular artifact: " + name)
    require(isinstance(desc, dict) and {"bytes", "sha256"} <= set(desc), "invalid descriptor")
    require(descriptor(p) == {k: desc[k] for k in ("bytes", "sha256")}, "artifact SHA/bytes mismatch: " + name)
    return p


def validate(root, suite, round_number):
    root = Path(root).resolve()
    require(root.is_dir(), "missing input root")
    require(suite in ("native", "legacy") and round_number in (1, 2), "suite/round")
    task_id = ("native.evaluation.S32.D31.guard_rescale" if suite == "native" else
               "legacy.layer0-end8192.S32.D31.guard_rescale")
    prefix, suffix = ("n" if suite == "native" else "l"), f"{round_number:02d}"
    records, artifacts, links, shard_receipts = [], {}, [], []
    common = None
    scientific = None
    shared_task = None
    seen_grid = set()
    for organization in ORGANIZATIONS:
        name = f"svc-{prefix}-{organization}-{suffix}"
        shard = root / name
        require(shard.is_dir() and shard.resolve().parent == root, "missing/unsafe shard: " + name)
        manifest_path = shard / "manifest.json"
        require(manifest_path.is_file() and not manifest_path.is_symlink(), "missing shard manifest")
        manifest = load(manifest_path)
        require(manifest.get("schema") == SCHEMA, "shard schema")
        config = manifest.get("config", {})
        expected_config = dict(GRID, lane_profiles=[organization])
        require(config == expected_config, "incomplete/unexpected shard grid: " + name)
        identity = {k: manifest.get(k) for k in ("source", "input_root", "range_root")}
        require(isinstance(identity["source"], dict) and identity["source"].get("commit") and
                identity["source"].get("service_sha256"), "missing service source binding")
        require(identity["input_root"] and identity["range_root"], "missing original input provenance")
        if common is None:
            common = identity
        else:
            require(canonical(identity) == canonical(common), "source/input root differs between shards")
        indexed = manifest.get("artifacts", {})
        require(isinstance(indexed, dict) and len(indexed) == 17 and "metrics.json" in indexed,
                "expected16 witnesses plus metrics per shard")
        paths = {n: checked_file(shard, n, d) for n, d in indexed.items()}
        metrics = load(paths["metrics.json"])
        require(metrics.get("schema") == SCHEMA and metrics.get("status") == "PASS_CONDITIONAL_SCHEDULE",
                "unaccepted shard execution")
        require(metrics.get("source") == common["source"], "metrics/service source mismatch")
        science_fields = {k: v for k, v in metrics.items() if k != "results"}
        if scientific is None:
            scientific = science_fields
        else:
            require(canonical(science_fields) == canonical(scientific), "scientific metadata differs")
        rows = metrics.get("results", [])
        require(isinstance(rows, list) and len(rows) == 8, "expected8 best-case records per shard")
        used_files = {"metrics.json"}
        for row in rows:
            require(row.get("organization") == organization, "directory/organization mismatch")
            require(row.get("task") == task_id and row.get("state_bits") == 32,
                    "unexpected task/precision")
            key = (organization, row.get("ext_ii"), row.get("tile"), row.get("norm_route"))
            require(key not in seen_grid, "duplicate case")
            seen_grid.add(key)
            require(key[1] in GRID["ext_profiles"] and key[2] in GRID["tiles"] and
                    key[3] in GRID["norm_routes"], "out-of-grid case")
            choices = row.get("strategies", [])
            require(len(choices) == 2 and {x.get("strategy") for x in choices} == set(GRID["strategies"]),
                    "incomplete strategy search")
            expected_best = min(choices, key=lambda x: (x["cycles"], x["strategy"]))
            require(row.get("best") == expected_best, "best strategy is not declared-search minimum")
            for choice in choices:
                filename = choice.get("witness")
                require(filename in indexed and filename.endswith(".json.gz"), "unindexed witness")
                require(filename not in used_files and filename not in artifacts, "duplicate witness name")
                used_files.add(filename)
                payload = gzip.decompress(paths[filename].read_bytes())
                witness = json.loads(payload)
                require(payload == canonical(witness), "witness is not canonical JSON")
                require(witness.get("schema") == SCHEMA, "witness schema")
                wc = witness.get("config", {})
                require(wc == {"organization": organization, "tile": row["tile"], "norm_route": row["norm_route"],
                               "ext_ii": row["ext_ii"], "strategy": choice["strategy"], "state_bits": 32},
                        "witness/case configuration differs")
                task = witness.get("task")
                require(isinstance(task, dict) and task.get("id") == task_id and
                        task.get("precision", {}).get("state_bits") == 32 and
                        task.get("precision", {}).get("decay_fraction") == 31,
                        "witness task/precision differs")
                fingerprint = hashlib.sha256(canonical(task)).hexdigest()
                require(row.get("task_fingerprint") == fingerprint == witness.get("task_fingerprint"),
                        "task fingerprint mismatch")
                require(row.get("commit_contract") == task.get("commit_contract"), "commit contract mismatch")
                if shared_task is None:
                    shared_task = task
                else:
                    require(canonical(task) == canonical(shared_task), "units/epoch/precision/task differs between cases")
                require(witness.get("makespan") == choice.get("cycles") and
                        len(witness.get("nodes", [])) == choice.get("nodes"), "witness/result summary differs")
                require(witness.get("producer_audit", {}).get("status") == "PASS", "producer schedule audit not PASS")
                # The independent receiver rechecks arithmetic/port legality.
                # This logical union checks source, complete coverage and bytes.
                artifacts[filename] = indexed[filename]
                links.append((paths[filename], filename))
            records.append(row)
        require(used_files == set(indexed), "unused or missing shard artifact")
        shard_receipts.append({"directory": name, "manifest": descriptor(manifest_path),
                               "metrics": indexed["metrics.json"], "cases": len(rows), "witnesses": 16})
    expected_grid = set(itertools.product(ORGANIZATIONS, GRID["ext_profiles"], GRID["tiles"], GRID["norm_routes"]))
    require(seen_grid == expected_grid and len(records) == 56 and len(links) == 112, "incomplete logical grid")
    org_order = {x: i for i, x in enumerate(ORGANIZATIONS)}
    records.sort(key=lambda x: (x["task"], x["ext_ii"], org_order[x["organization"]],
                                x["tile"], GRID["norm_routes"].index(x["norm_route"])))
    metrics = dict(scientific, results=records)
    return root, common, metrics, artifacts, links, shard_receipts


def aggregate(root, suite, round_number, out, binding):
    require(binding.get("aggregate_sha256") == sha(__file__) and binding.get("commit"),
            "aggregate source binding mismatch")
    root, common, metrics, artifacts, links, receipts = validate(root, suite, round_number)
    out = Path(out).resolve()
    require(out.parent == root and out.name == f"service-{suite}{round_number:02d}", "unexpected logical output path")
    require(not out.exists(), "output already exists")
    out.mkdir()
    try:
        for src, name in links:
            os.link(src, out / name)
        (out / "metrics.json").write_bytes(canonical(metrics))
        artifacts["metrics.json"] = descriptor(out / "metrics.json")
        manifest = {"schema": SCHEMA, "source": common["source"],
                    "config": dict(GRID, lane_profiles=list(ORGANIZATIONS)),
                    "input_root": common["input_root"], "range_root": common["range_root"],
                    "artifacts": artifacts,
                    "aggregation_source": {"binding": binding, "suite": suite, "round": round_number,
                                           "shards": receipts, "scientific_files": "112 unchanged hardlinked gzip witnesses and deterministic metrics union",
                                           "execution": "logical union of seven independent service jobs; no model/math/timing execution by aggregator",
                                           "environment": {"python": sys.version, "platform": platform.platform()}},
                    "input_validation": "all seven manifests, metrics and112 witness SHA/bytes; exact service binding, task/precision/units/epoch/contract and complete grid; independent schedule legality replay remains separate"}
        (out / "manifest.json").write_bytes(canonical(manifest))
    except Exception as exc:
        (out / "AGGREGATION_FAILED.json").write_bytes(canonical({"status": "FAIL", "type": type(exc).__name__, "error": str(exc)}))
        raise
    return {"status": "PASS_LOGICAL_UNION", "suite": suite, "round": round_number,
            "shards": 7, "cases": 56, "witnesses": 112,
            "manifest": descriptor(out / "manifest.json"), "metrics": descriptor(out / "metrics.json")}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--suite", required=True, choices=("native", "legacy"))
    p.add_argument("--round", required=True, type=int, choices=(1, 2))
    p.add_argument("--out", required=True)
    p.add_argument("--binding", required=True)
    a = p.parse_args()
    print(json.dumps(aggregate(a.root, a.suite, a.round, a.out, load(a.binding))))


if __name__ == "__main__":
    main()
