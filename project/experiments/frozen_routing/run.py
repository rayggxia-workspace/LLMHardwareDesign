"""Reproducible single-machine campaign; output is evidence, never a PPA claim."""
from __future__ import annotations
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

from fixtures import tiny
from model import WORKLOADS, demands, digest, make_fabric, mappings, seeded_mapping
from numeric import check
from oracle import solve
from router import route
from validate import validate, validate_mapping

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")


def command(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True, encoding="utf-8").strip()


def fixed_coverage(base, connectors, workloads):
    solution = {"base_sha256": digest(base), "connectors": connectors}
    found = {}
    if not validate(base, [], solution)["valid"]:
        return found
    for name, workload in workloads.items():
        for mapping in mappings(workload):
            if validate(base, demands(workload, mapping), solution)["valid"]:
                found[name] = mapping
                break
    return found


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=HERE/"campaign.json")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--allow-dirty", action="store_true", help="development only; recorded in manifest")
    args = p.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    if set(cfg["design_workloads"]) != {n for n, w in WORKLOADS.items() if w["split"] == "design"} or set(
            cfg["held_out_workloads"]) != {n for n, w in WORKLOADS.items() if w["split"] == "held_out"}:
        raise ValueError("design/held-out split differs from frozen input version")
    args.out = args.out.resolve()
    if args.out.exists():
        raise SystemExit("Output directory already exists; choose a new attempt")
    dirty = command("git", "status", "--porcelain")
    if dirty and not args.allow_dirty:
        raise SystemExit("Commit source/config before a recorded run (or explicitly --allow-dirty for development)")
    args.out.mkdir(parents=True)
    (args.out/"fabrics").mkdir()
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    start = time.perf_counter()
    write(args.out/"campaign.json", cfg)
    write(args.out/"workloads.json", WORKLOADS)
    source_hashes = {str(f.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(f.read_bytes()).hexdigest()
                     for f in sorted(HERE.glob("*.py"))}
    rows, baseline_rows = [], []
    variants = list(itertools.product(cfg["tracks"], cfg["segment_spans"], cfg["pin_access"]))
    for tracks, span, access in variants:
        variant = f"t{tracks}-s{span}-a{access}"
        base = make_fabric(tracks, span, access, cfg["endpoint_capacity"])
        frozen_hash = digest(base)
        write(args.out/"fabrics"/(variant+".json"), base)
        per_variant, candidates = [], {(): []}
        for name, workload in WORKLOADS.items():
            for seed in cfg["seeds"]:
                mapping = seeded_mapping(workload, seed)
                nets = demands(workload, mapping)
                for method in cfg["methods"]:
                    t0 = time.perf_counter()
                    result = route(base, nets, method, seed, cfg["multi_order_trials"])
                    elapsed = time.perf_counter()-t0
                    row = {"variant": variant, "workload": name, "split": workload["split"],
                           "seed": seed, "method": method, "mapping": mapping,
                           "route_attempt_budget": 1 if method == "sequential" else 2+cfg["multi_order_trials"],
                           "base_sha256": frozen_hash, "runtime_seconds": elapsed,
                           "status": "routed" if result else "heuristic_no_solution",
                           "solution": result}
                    row["mapping_validation"] = validate_mapping(base, workload, mapping)
                    if not row["mapping_validation"]["valid"]:
                        raise AssertionError(row)
                    if result:
                        row["validation"] = validate(base, nets, result, frozen_hash)
                        if not row["validation"]["valid"]:
                            raise AssertionError(row)
                        row["numeric"] = check(name, workload, mapping, base, result, seed)
                        if name in cfg["design_workloads"]:
                            candidates[tuple(result["connectors"])] = result["connectors"]
                    per_variant.append(row)
                    if digest(base) != frozen_hash:
                        raise AssertionError("fabric mutated during routing")
        # Candidate family is declared: every successful design-set route plus
        # physically legal pairwise unions. Held-out results cannot select it.
        singles = list(candidates.values())
        for a, b in itertools.combinations(singles, 2):
            joined = sorted(set(a) | set(b))
            if validate(base, [], {"base_sha256": frozen_hash, "connectors": joined})["valid"]:
                candidates[tuple(joined)] = joined
        design = {n: WORKLOADS[n] for n in cfg["design_workloads"]}
        scored = []
        for candidate in candidates.values():
            covered = fixed_coverage(base, candidate, design)
            cost = validate(base, [], {"base_sha256": frozen_hash, "connectors": candidate})["custom_cost_units"]
            scored.append(((-len(covered), cost, tuple(candidate)), candidate, covered))
        _, fixed, covered = min(scored, key=lambda x: x[0])
        all_covered = fixed_coverage(base, fixed, WORKLOADS)
        fixed_solution = {"base_sha256": frozen_hash, "connectors": fixed}
        for name, workload in WORKLOADS.items():
            record = {"variant": variant, "workload": name, "split": workload["split"],
                      "method": "design_selected_fixed", "base_sha256": frozen_hash,
                      "candidate_count": len(candidates), "design_coverage": sorted(covered),
                      "status": "supported" if name in all_covered else "no_mapping_for_selected_fixed",
                      "solution": fixed_solution, "mapping": all_covered.get(name)}
            if name in all_covered:
                m = all_covered[name]
                record["validation"] = validate(base, demands(workload, m), fixed_solution, frozen_hash)
                record["numeric"] = check(name, workload, m, base, fixed_solution, cfg["seeds"][0])
            baseline_rows.append(record)
        (args.out/(variant+"-cases.jsonl")).write_text(
            "".join(json.dumps(r, sort_keys=True, separators=(",", ":"))+"\n" for r in per_variant), encoding="utf-8")
        rows.extend(per_variant)
        print(variant, sum(r["status"] == "routed" for r in per_variant), "/", len(per_variant),
              "fixed:", sorted(all_covered), flush=True)
    oracle_rows = []
    for seed in range(cfg["oracle_seeds"]):
        base, nets = tiny(seed)
        exact = solve(base, nets)
        for method in cfg["methods"]:
            result = route(base, nets, method, seed, cfg["multi_order_trials"])
            val = validate(base, nets, result) if result else None
            if result and (exact is None or not val["valid"] or val["custom_cost_units"] < exact[0]):
                raise AssertionError("router/oracle disagreement")
            oracle_rows.append({"seed": seed, "base": base, "nets": nets, "method": method,
                                "exact_feasible": exact is not None, "exact_optimum": exact[0] if exact else None,
                                "heuristic_found": result is not None, "solution": result,
                                "cost": val["custom_cost_units"] if val else None})
    write(args.out/"fixed-baseline.json", baseline_rows)
    write(args.out/"oracle.json", oracle_rows)
    summary = {"cases": len(rows), "variants": len(variants),
               "by_method": {m: {"routed": sum(r["status"] == "routed" for r in rows if r["method"] == m),
                                  "total": sum(r["method"] == m for r in rows)} for m in cfg["methods"]},
               "fixed_supported": sum(r["status"] == "supported" for r in baseline_rows),
               "fixed_total": len(baseline_rows),
               "numeric_checks": sum("numeric" in r for r in rows+baseline_rows),
               "max_numeric_error": max((r["numeric"]["max_abs_error"] for r in rows+baseline_rows if "numeric" in r), default=None),
               "oracle_instances": cfg["oracle_seeds"],
               "oracle_feasible": sum(r["exact_feasible"] for r in oracle_rows[::len(cfg["methods"])]),
               "oracle_by_method": {m: {"found": sum(r["heuristic_found"] for r in oracle_rows if r["method"] == m),
                                          "missed_feasible": sum(r["exact_feasible"] and not r["heuristic_found"] for r in oracle_rows if r["method"] == m)} for m in cfg["methods"]},
               "elapsed_seconds": time.perf_counter()-start,
               "scope": "abstract electrical connectivity; no calibrated PPA or physical H2"}
    write(args.out/"summary.json", summary)
    manifest = {"schema": 1, "started_utc": started, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "source_commit": command("git", "rev-parse", "HEAD"), "source_dirty": bool(dirty),
                "dirty_status": dirty, "source_sha256": source_hashes,
                "config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
                "input_version": cfg["input_version"], "workloads_sha256": digest(WORKLOADS),
                "command": [sys.executable, *sys.argv], "python": sys.version,
                "platform": platform.platform(), "cpu": platform.processor(),
                "logical_cpus": os.cpu_count(), "numpy": __import__("numpy").__version__,
                "venv_system_site_packages": (Path(sys.prefix)/"pyvenv.cfg").exists() and
                    "include-system-site-packages = true" in (Path(sys.prefix)/"pyvenv.cfg").read_text(),
                "output_location": str(args.out),
                "files": {str(f.relative_to(args.out)).replace("\\", "/"): {"bytes": f.stat().st_size,
                          "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
                          for f in sorted(args.out.rglob("*")) if f.is_file()}}
    write(args.out/"manifest.json", manifest)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
