"""Predeclared paired ablation; refuses dirty source and overwriting evidence."""
import argparse
import datetime as dt
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from study import (ARMS, FROZEN, HERE, WORKLOADS, assert_contract, check, classify_group,
                   demands, digest, make_inventory, materialize, route, seeded_mapping,
                   summarize, validate, validate_mapping)
from oracle import solve
from tiny_cases import cases

ROOT = HERE.parents[2]


def write(path, value):
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


def expected_keys(cfg):
    return {(f"t{t}-s{s}-a{a}", name, seed, arm)
            for t, s, a, name, seed, arm in itertools.product(
                cfg["tracks"], cfg["spans"], cfg["original_access"], cfg["workloads"], cfg["seeds"], cfg["arms"])}


def check_config(cfg):
    expected = {"schema": 1, "input_version": "endpoint-overlay-ablation-v1", "tracks": [1, 2],
                "spans": [1, 2], "original_access": [2, 4], "access_multiplier": 2,
                "wire_capacity": 3, "seeds": [17, 43, 101], "workloads": list(WORKLOADS),
                "arms": list(ARMS), "method": "multi_order", "random_order_trials": 12}
    if any(cfg.get(k) != value for k, value in expected.items()) or set(cfg) != {*expected, "note"}:
        raise ValueError("config differs from predeclared Issue13 contract; use a new version for a new study")


def oracle_records():
    records = []
    for case in cases():
        for arm in ARMS:
            base = materialize(case["master"], case["overlays"][arm])
            exact = solve(base, case["nets"])
            assert (exact is not None) == case["expected_feasible"][arm]
            if exact:
                solution = {"base_sha256": digest(base), "connectors": exact[1]}
                assert validate(base, case["nets"], solution)["valid"]
            records.append({"name": case["name"], "arm": arm, "master": case["master"],
                            "overlay": case["overlays"][arm], "nets": case["nets"],
                            "expected_feasible": case["expected_feasible"][arm],
                            "exact_feasible": exact is not None,
                            "optimum": exact[0] if exact else None,
                            "connectors": exact[1] if exact else None})
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=HERE / "campaign.json")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--allow-dirty", action="store_true", help="development evidence only")
    args = parser.parse_args()
    cfg_bytes = args.config.read_bytes()
    cfg = json.loads(cfg_bytes)
    check_config(cfg)
    if cfg_bytes != (HERE / "campaign.json").read_bytes():
        raise ValueError("use the exact committed campaign bytes")
    if args.out.exists():
        raise SystemExit("Choose a new output directory; old evidence is immutable")
    dirty = git("status", "--porcelain")
    if dirty and not args.allow_dirty:
        raise SystemExit("Commit source/config before a formal run")
    source_commit = git("rev-parse", "HEAD")
    source_paths = sorted([*HERE.glob("*.py"), *FROZEN.glob("*.py"), HERE / "campaign.json"])
    source_hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    args.out = args.out.resolve()
    args.out.mkdir(parents=True)
    (args.out / "inventories").mkdir()
    (args.out / "campaign.json").write_bytes(cfg_bytes)
    write(args.out / "workloads.json", WORKLOADS)
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    start = time.perf_counter()
    all_rows = []
    for tracks, span, access in itertools.product(cfg["tracks"], cfg["spans"], cfg["original_access"]):
        variant = f"t{tracks}-s{span}-a{access}"
        master, overlays = make_inventory(tracks, span, access, cfg["wire_capacity"], cfg["access_multiplier"])
        master_hash = digest(master)
        bases = assert_contract(master, overlays)
        write(args.out / "inventories" / (variant + ".json"), {"master": master, "overlays": overlays})
        rows = []
        for name, seed in itertools.product(cfg["workloads"], cfg["seeds"]):
            workload = WORKLOADS[name]
            mapping = seeded_mapping(workload, seed)
            nets = demands(workload, mapping)
            group = []
            for arm in ARMS:
                base = bases[arm]
                before = digest(base)
                assert validate_mapping(base, workload, mapping)["valid"]
                t0 = time.perf_counter()
                solution = route(base, nets, cfg["method"], seed, cfg["random_order_trials"])
                elapsed = time.perf_counter() - t0
                row = {"variant": variant, "workload": name, "prior_split_label": workload["split"],
                       "seed": seed, "arm": arm, "mapping": mapping, "master_sha256": master_hash,
                       "overlay_sha256": digest(overlays[arm]), "effective_sha256": before,
                       "method": cfg["method"], "route_attempt_budget": 2 + cfg["random_order_trials"],
                       "runtime_seconds": elapsed, "raw_solution": solution}
                if solution is not None:
                    row["validation"] = validate(base, nets, solution, before)
                    assert row["validation"]["valid"]
                    row["numeric"] = check(name, workload, mapping, base, solution, seed)
                group.append(row)
                assert digest(base) == before and digest(master) == master_hash
            rows.extend(classify_group(group, bases))
        (args.out / (variant + "-cases.jsonl")).write_bytes(
            "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in rows).encode("utf-8"))
        all_rows.extend(rows)
        print(variant, {arm: sum(r["knowledge"] == "routed" for r in rows if r["arm"] == arm) for arm in ARMS}, flush=True)
    assert {(r["variant"], r["workload"], r["seed"], r["arm"]) for r in all_rows} == expected_keys(cfg)
    assert len(all_rows) == len(expected_keys(cfg))
    oracle_rows = oracle_records()
    write(args.out / "oracle.json", oracle_rows)
    summary = summarize(all_rows, oracle_rows)
    summary["elapsed_seconds"] = time.perf_counter() - start
    write(args.out / "summary.json", summary)
    assert git("rev-parse", "HEAD") == source_commit and git("status", "--porcelain") == dirty
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in source_hashes.items())
    manifest = {"schema": 1, "started_utc": started, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "source_commit": source_commit, "source_dirty": bool(dirty), "dirty_status": dirty,
                "source_sha256": source_hashes, "config_sha256": hashlib.sha256(cfg_bytes).hexdigest(),
                "input_version": cfg["input_version"], "workloads_sha256": digest(WORKLOADS),
                "command": [sys.executable, *sys.argv], "python": sys.version,
                "numpy": __import__("numpy").__version__, "platform": platform.platform(),
                "task_temporary_directory": os.environ.get("TEMP"),
                "python_cache_prefix": sys.pycache_prefix,
                "logical_cpus": os.cpu_count(), "output_location": str(args.out),
                "files": {f.relative_to(args.out).as_posix(): {"bytes": f.stat().st_size,
                          "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
                          for f in sorted(args.out.rglob("*")) if f.is_file()}}
    write(args.out / "manifest.json", manifest)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
