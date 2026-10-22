"""Independent read-only audit of Issue13; no project module is imported.

Only this directory receives artifacts. Source/run directories are read-only.
Run with existing Python -B; all subprocess TEMP/cache locations stay on D:.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from itertools import combinations, permutations, product
from pathlib import Path
import json
import math
import os
import random
import subprocess
import sys
import time
import traceback

OUT = Path(__file__).resolve().parent
PROJECT = Path("D:/Projects/LLMHardwareDesign-endpoints")
RUN = PROJECT / "project/experiments/endpoint_ablation/local_runs/issue-13-run01"
OLD = Path("D:/Projects/LLMHardwareDesign-dac/project/experiments/frozen_routing/local_runs/issue-11-run01")
EXPECTED_COMMIT = "dc294114a6758b6baa1e4f6085630971a8f11fcc"
ARMS = ("restricted", "access", "capacity", "joint")
os.environ.update(TEMP=str(OUT), TMP=str(OUT), TMPDIR=str(OUT),
                  PYTHONPYCACHEPREFIX=str(OUT / "pycache"),
                  PYTHONDONTWRITEBYTECODE="1", GIT_NO_LAZY_FETCH="1")
import numpy as np


def h(data):
    return sha256(data).hexdigest()


def digest(value):
    return h(json.dumps(value, sort_keys=True, separators=(",", ":"),
                        ensure_ascii=False).encode("utf-8"))


def read(path):
    return json.loads(path.read_bytes())


def git(*args):
    return subprocess.run(["git", *args], cwd=PROJECT, capture_output=True,
                          check=True, env=os.environ).stdout


def effective(master, overlay):
    assert set(overlay) == {"allowed_connectors", "tap_capacities"}
    allowed, caps = overlay["allowed_connectors"], overlay["tap_capacities"]
    assert len(allowed) == len(set(allowed)) and set(allowed) <= set(master["connectors"])
    assert set(caps) == set(master["taps"])
    result = deepcopy(master)
    result["connectors"] = {key: deepcopy(master["connectors"][key]) for key in allowed}
    for key, cap in caps.items():
        assert type(cap) is int and 0 < cap <= master["taps"][key]["capacity"]
        if master["components"][master["taps"][key]["component"]]["kind"] != "wire":
            assert cap == master["taps"][key]["capacity"] == 1
        result["taps"][key]["capacity"] = cap
    return result


def mapped_demands(workload, mapping):
    result = {}
    for source, destination, port in workload["edges"]:
        driver = mapping[source] + ".o"
        result.setdefault(driver, []).append(mapping[destination] + "." + port)
    return [{"driver": driver, "sinks": sinks, "width": 16}
            for driver, sinks in result.items()]


def expected_mapping(workload, seed):
    matrices = [n for n, op in workload["ops"].items() if op == "matmul"]
    vectors = [n for n, op in workload["ops"].items() if op != "matmul"]
    options = [{"x": "S0", "y": "S1", **dict(zip(matrices, cs)), **dict(zip(vectors, vs))}
               for cs in permutations(["C0", "C1", "C2", "C3"], len(matrices))
               for vs in permutations(["V0", "V1"], len(vectors))]
    return options[random.Random(seed).randrange(len(options))]


def validate_mapping(base, workload, mapping):
    assert set(mapping) == {"x", "y", *workload["ops"]}
    assert mapping["x"] == "S0" and mapping["y"] == "S1"
    assert len(set(mapping.values())) == len(mapping)
    for node, operation in workload["ops"].items():
        assert operation in base["blocks"][mapping[node]]["operations"]


def electrical(base, demands, selected):
    """Contract passive components, then independently check all live drivers.

    Return None for an illegal configuration, including tap-capacity/global
    budget violations. This is separate code from the project's verifier.
    """
    if len(selected) != len(set(selected)) or not set(selected) <= set(base["connectors"]):
        return None
    if len(selected) > base["limits"]["custom_connector_budget"]:
        return None
    parent = {name: name for name in base["components"]}

    def find(name):
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    contacts = Counter()
    touched = set()
    for key in selected:
        con = base["connectors"][key]
        if con["a"] not in base["taps"] or con["b"] not in base["taps"]:
            return None
        contacts.update([con["a"], con["b"]])
        a, b = [base["taps"][con[port]]["component"] for port in ("a", "b")]
        touched.update((a, b))
        parent[find(a)] = find(b)
    if any(count > base["taps"][tap]["capacity"] for tap, count in contacts.items()):
        return None
    roots = {name: find(name) for name in parent}
    drivers = defaultdict(set)
    for name, component in base["components"].items():
        if component["driver"]:
            drivers[roots[name]].add(component["driver"])
    if any(len(value) > 1 for value in drivers.values()):
        return None
    sink_owner = {}
    for demand in demands:
        driver = demand["driver"]
        if driver not in roots or base["components"][driver]["driver"] != driver:
            return None
        if type(demand["width"]) is not int or demand["width"] <= 0:
            return None
        for sink in demand["sinks"]:
            if sink not in roots or base["components"][sink]["kind"] != "input":
                return None
            if sink in sink_owner and sink_owner[sink] != driver:
                return None
            sink_owner[sink] = driver
            if roots[sink] != roots[driver] or drivers[roots[sink]] != {driver}:
                return None
        if any(component["width"] < demand["width"] for name, component in base["components"].items()
               if roots[name] == roots[driver]):
            return None
    stats = {"valid": True, "errors": [], "custom_connections": len(selected),
             "custom_cost_units": sum(base["connectors"][k]["cost_units"] for k in selected),
             "occupied_prefab_length_units": sum(base["components"][c]["length_units"] for c in touched)}
    return roots, drivers, stats


def check_solution(base, demands, solution):
    assert set(solution) == {"base_sha256", "connectors"}
    assert solution["base_sha256"] == digest(base)
    value = electrical(base, demands, solution["connectors"])
    assert value is not None, "illegal saved witness"
    return value


def cuts(base, demands):
    result = []
    for demand in demands:
        driver, sinks = demand["driver"], set(demand["sinks"])
        blocked = {name for name, component in base["components"].items()
                   if (component["driver"] is not None and name != driver)
                   or (component["kind"] == "input" and name not in sinks)}
        adjacency = defaultdict(set)
        for con in base["connectors"].values():
            a, b = [base["taps"][con[port]]["component"] for port in ("a", "b")]
            if a not in blocked and b not in blocked:
                adjacency[a].add(b)
                adjacency[b].add(a)
        reached, queue = {driver}, deque([driver])
        while queue:
            name = queue.popleft()
            for neighbor in adjacency[name] - reached:
                reached.add(neighbor)
                queue.append(neighbor)
        missing = sinks - reached
        if missing:
            result.append({"driver": driver, "unreachable_sinks": sorted(missing),
                           "reachable_components": sorted(reached)})
    return result


def normalized_cuts(values):
    return sorted(values, key=lambda value: value["driver"])


def numeric(row, workload, base, solution, record):
    roots, drivers, _ = check_solution(base, mapped_demands(workload, row["mapping"]), solution)
    source = lambda pin: next(iter(drivers[roots[pin]]))
    rng = random.Random(row["seed"])
    inputs = [[rng.uniform(-0.5, 0.5) for _ in range(4)] for _ in range(2)]
    weights = {node: [[rng.uniform(-0.5, 0.5) for _ in range(4)] for _ in range(4)]
               for node, operation in workload["ops"].items() if operation == "matmul"}
    x = np.array(inputs)
    w = {name: np.array(value) for name, value in weights.items()}
    silu = lambda value: value / (1 + np.exp(-value))
    name = row["workload"]
    if name == "ffn":
        reference = silu(x @ w["m0"]) @ w["m1"]
    elif name == "gated_ffn":
        reference = (silu(x @ w["m0"]) * (x @ w["m1"])) @ w["m2"]
    elif name == "residual_ffn":
        reference = silu(x @ w["m0"]) @ w["m1"] + x
    elif name == "fork_add":
        reference = ((x @ w["m0"]) + (x @ w["m1"])) @ w["m2"]
    else:
        raise AssertionError("unknown workload")
    values, pending = {"S0.o": inputs}, dict(workload["ops"])
    while pending:
        initial = len(pending)
        for node, operation in list(pending.items()):
            block = row["mapping"][node]
            sources = [source(block + ".a")]
            if operation in ("mul", "add"):
                sources.append(source(block + ".b"))
            if any(s not in values for s in sources):
                continue
            a = values[sources[0]]
            if operation == "matmul":
                result = [[sum(a[i][k] * weights[node][k][j] for k in range(4))
                           for j in range(4)] for i in range(2)]
            elif operation == "silu":
                result = [[v / (1 + math.exp(-v)) for v in ar] for ar in a]
            else:
                b = values[sources[1]]
                result = [[(u * v if operation == "mul" else u + v) for u, v in zip(ar, br)]
                          for ar, br in zip(a, b)]
            values[block + ".o"] = result
            del pending[node]
        assert len(pending) < initial, "cyclic or unresolved value flow"
    error = float(np.max(np.abs(np.array(values[source("S1.a")]) - reference)))
    assert math.isfinite(error) and error <= 1e-12
    assert error == record["max_abs_error"] and record["passed"] is True
    assert record["seed"] == row["seed"] and record["shape"] == [2, 4]
    assert record["semantics"] == "software_float64_no_quantization"
    return error


def audit():
    started = time.perf_counter()
    manifest, cfg, workloads = [read(RUN / name) for name in ("manifest.json", "campaign.json", "workloads.json")]
    assert manifest["source_commit"] == EXPECTED_COMMIT
    assert manifest["source_dirty"] is False and manifest["dirty_status"] == ""
    assert h((RUN / "campaign.json").read_bytes()) == manifest["config_sha256"]
    assert digest(workloads) == manifest["workloads_sha256"]
    actual_paths = {path.relative_to(RUN).as_posix() for path in RUN.rglob("*") if path.is_file()}
    assert actual_paths == {*manifest["files"], "manifest.json"}
    assert len(manifest["files"]) == 20 and len(actual_paths) == 21
    outputs = {}
    for name, expected in manifest["files"].items():
        path = (RUN / name).resolve()
        assert path.is_relative_to(RUN.resolve())
        data = path.read_bytes()
        assert len(data) == expected["bytes"] and h(data) == expected["sha256"], name
        outputs[name] = {"bytes": len(data), "sha256": h(data)}
    sources = {}
    for name, expected in manifest["source_sha256"].items():
        current = (PROJECT / name).read_bytes()
        frozen = git("show", EXPECTED_COMMIT + ":" + name)
        assert h(current) == expected and h(frozen) == expected, name
        sources[name] = expected
    assert h((PROJECT / "project/experiments/endpoint_ablation/campaign.json").read_bytes()) == manifest["config_sha256"]
    assert tuple(cfg["arms"]) == ARMS and cfg["method"] == "multi_order" and cfg["random_order_trials"] == 12
    variants = [f"t{t}-s{s}-a{a}" for t, s, a in product(cfg["tracks"], cfg["spans"], cfg["original_access"])]
    expected_keys = set(product(variants, cfg["workloads"], cfg["seeds"], ARMS))
    rows, inventories, inventory_checks, masters_before = [], {}, {}, {}
    for variant in variants:
        inv = read(RUN / "inventories" / (variant + ".json"))
        master, overlays = inv["master"], inv["overlays"]
        masters_before[variant] = digest(master)
        assert set(overlays) == set(ARMS)
        bases = {arm: effective(master, overlays[arm]) for arm in ARMS}
        assert bases["joint"] == master
        for arm, base in bases.items():
            for field in ("components", "blocks", "limits", "parameters", "assumptions"):
                assert base[field] == master[field]
            assert set(base["taps"]) == set(master["taps"])
            for key in base["taps"]:
                assert {k: v for k, v in base["taps"][key].items() if k != "capacity"} == {
                    k: v for k, v in master["taps"][key].items() if k != "capacity"}
        for small, large in (("restricted", "access"), ("restricted", "capacity"),
                             ("access", "joint"), ("capacity", "joint")):
            assert set(bases[small]["connectors"]) <= set(bases[large]["connectors"])
            assert all(bases[large]["connectors"][key] == con for key, con in bases[small]["connectors"].items())
            assert all(bases[small]["taps"][key]["capacity"] <= bases[large]["taps"][key]["capacity"] for key in master["taps"])
        assert bases["restricted"]["taps"] == bases["access"]["taps"]
        assert bases["capacity"]["taps"] == bases["joint"]["taps"]
        assert bases["restricted"]["connectors"] == bases["capacity"]["connectors"]
        assert bases["access"]["connectors"] == bases["joint"]["connectors"]
        old_base = read(OLD / "fabrics" / (variant + ".json"))
        for field in ("components", "blocks", "taps", "connectors", "limits"):
            assert bases["restricted"][field] == old_base[field], (variant, field)
        inventory_checks[variant] = {"master_sha256": digest(master), "restricted_inventory_equals_issue11": True,
                                     "all_overlays_preserve_components_blocks_sites_and_costs": True}
        inventories[variant] = (master, overlays, bases)
        rows.extend(json.loads(line) for line in (RUN / (variant + "-cases.jsonl")).read_text().splitlines())
    keys = [(r["variant"], r["workload"], r["seed"], r["arm"]) for r in rows]
    assert len(rows) == len(set(keys)) == 384 and set(keys) == expected_keys
    grouped, numeric_errors = defaultdict(dict), []
    cut_count, raw_count, imported_count = 0, 0, 0
    counters, by_task, by_variant = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    for row in rows:
        variant, name, seed, arm = row["variant"], row["workload"], row["seed"], row["arm"]
        master, overlays, bases = inventories[variant]
        base, workload = bases[arm], workloads[name]
        assert row["master_sha256"] == digest(master)
        assert row["overlay_sha256"] == digest(overlays[arm])
        assert row["effective_sha256"] == digest(base)
        assert row["mapping"] == expected_mapping(workload, seed)
        assert row["prior_split_label"] == workload["split"]
        assert row["method"] == "multi_order" and row["route_attempt_budget"] == 14
        assert row["runtime_seconds"] >= 0
        validate_mapping(base, workload, row["mapping"])
        demands = mapped_demands(workload, row["mapping"])
        computed_cuts = cuts(base, demands)
        assert normalized_cuts(computed_cuts) == normalized_cuts(row["no_path_certificates"])
        cut_count += len(computed_cuts)
        if row["raw_solution"] is not None:
            _, _, stats = check_solution(base, demands, row["raw_solution"])
            assert stats == row["validation"] and row["knowledge"] == "routed"
            assert row["imported_witness"] is None and not computed_cuts
            numeric_errors.append(numeric(row, workload, base, row["raw_solution"], row["numeric"]))
            raw_count += 1
        else:
            assert "validation" not in row and "numeric" not in row
            witness = row["imported_witness"]
            if witness is not None:
                assert row["knowledge"] == "known_feasible_heuristic_miss" and not computed_cuts
                _, _, stats = check_solution(base, demands, witness["solution"])
                assert stats == witness["validation"]
                numeric_errors.append(numeric(row, workload, base, witness["solution"], witness["numeric"]))
                imported_count += 1
            else:
                assert row["knowledge"] == ("proven_no_path_fixed_mapping" if computed_cuts else "unknown")
        grouped[(variant, name, seed)][arm] = row
        counters[arm][row["knowledge"]] += 1
        by_task[(arm, name)][row["knowledge"]] += 1
        by_variant[(variant, arm)][row["knowledge"]] += 1
    assert len(grouped) == 96 and raw_count == 230
    promotions = Counter()
    for key, group in grouped.items():
        assert set(group) == set(ARMS)
        assert all(row["mapping"] == group["restricted"]["mapping"] for row in group.values())
        master, overlays, bases = inventories[key[0]]
        for arm, row in group.items():
            if row["imported_witness"]:
                witness = row["imported_witness"]
                source = group[witness["source_arm"]]
                assert source["raw_solution"] is not None
                assert witness["solution"]["connectors"] == source["raw_solution"]["connectors"]
                assert witness["source_effective_sha256"] == source["effective_sha256"]
            if group["restricted"]["no_path_certificates"] and row["knowledge"] in ("routed", "known_feasible_heuristic_miss"):
                promotions[arm] += 1
        assert digest(master) == masters_before[key[0]]
    exact_rows = read(RUN / "oracle.json")
    assert len(exact_rows) == 24 and len({(r["name"], r["arm"]) for r in exact_rows}) == 24
    assert len({r["name"] for r in exact_rows}) == 6
    exact_summary, enumerated = defaultdict(dict), 0
    exact_masters = {}
    for row in exact_rows:
        name, arm = row["name"], row["arm"]
        assert exact_masters.setdefault(name, digest(row["master"])) == digest(row["master"])
        base = effective(row["master"], row["overlay"])
        connectors, best = sorted(base["connectors"]), None
        assert len(connectors) <= 5
        for mask in range(1 << len(connectors)):
            selected = [key for bit, key in enumerate(connectors) if mask & (1 << bit)]
            value = electrical(base, row["nets"], selected)
            enumerated += 1
            if value is not None:
                cost = value[2]["custom_cost_units"]
                best = cost if best is None else min(best, cost)
        assert (best is not None) == row["exact_feasible"] == row["expected_feasible"]
        assert best == row["optimum"]
        if best is None:
            assert row["connectors"] is None
        else:
            selected = electrical(base, row["nets"], row["connectors"])
            assert selected is not None and selected[2]["custom_cost_units"] == best
        exact_summary[name][arm] = {"feasible": best is not None, "optimum": best}
    old_rows = [json.loads(line) for p in sorted(OLD.glob("*-cases.jsonl"))
                for line in p.read_text().splitlines() if line.strip()]
    legacy = {(r["variant"], r["workload"], r["seed"]): r for r in old_rows if r["method"] == "multi_order"}
    assert len(legacy) == 96 and set(legacy) == set(grouped)
    for key, old in legacy.items():
        current = grouped[key]["restricted"]
        assert current["mapping"] == old["mapping"]
        assert (old["status"] == "routed") == (current["raw_solution"] is not None)
        if old["solution"] is not None:
            assert set(current["raw_solution"]["connectors"]) == set(old["solution"]["connectors"])
            assert current["raw_solution"]["connectors"] == old["solution"]["connectors"]
    summary = read(RUN / "summary.json")
    assert summary["cases"] == 384 and summary["paired_groups"] == 96
    assert summary["by_arm"] == {arm: dict(counters[arm]) for arm in ARMS}
    assert summary["numeric_checks"] == len(numeric_errors) == raw_count + imported_count
    assert summary["oracle_rows"] == len(exact_rows)
    assert summary["no_path_to_legal_witness_fixed_mappings"] == {arm: promotions[arm] for arm in ("access", "joint")}
    # Check that neither this audit nor concurrent work altered inspected inputs.
    assert all(h((RUN / name).read_bytes()) == info["sha256"] for name, info in outputs.items())
    assert all(h((PROJECT / name).read_bytes()) == value for name, value in sources.items())
    same_pairs = {}
    for a, b in (("restricted", "capacity"), ("access", "joint")):
        same_pairs[a + "__" + b] = {
            "same_raw_success_status_count": sum((g[a]["raw_solution"] is not None) == (g[b]["raw_solution"] is not None) for g in grouped.values()),
            "same_connector_set_count": sum((None if g[a]["raw_solution"] is None else set(g[a]["raw_solution"]["connectors"])) ==
                                             (None if g[b]["raw_solution"] is None else set(g[b]["raw_solution"]["connectors"])) for g in grouped.values())}
    return {"status": "PASS", "audited_utc": datetime.now(timezone.utc).isoformat(),
            "auditor_source_sha256": h(Path(__file__).read_bytes()),
            "auditor_imported_project_modules": False, "python": sys.version, "numpy": np.__version__,
            "run": str(RUN), "run_manifest_sha256": h((RUN / "manifest.json").read_bytes()),
            "source_commit": EXPECTED_COMMIT, "source_dirty_at_run": False,
            "observed_current_head": git("rev-parse", "HEAD").decode().strip(),
            "observed_current_status": git("status", "--porcelain").decode(),
            "source_files_matched_current_and_commit": len(sources),
            "indexed_output_files_verified": len(outputs), "actual_files_including_manifest": len(actual_paths),
            "cases": len(rows), "paired_groups": len(grouped), "fixed_mapping_and_attempt_budget_verified": True,
            "inventories": inventory_checks,
            "electrically_valid_raw_solutions": raw_count, "valid_imported_witnesses": imported_count,
            "numeric_checks_recomputed": len(numeric_errors), "numeric_error_max": max(numeric_errors),
            "cut_certificates_recomputed": cut_count, "knowledge_by_arm": {arm: dict(counters[arm]) for arm in ARMS},
            "knowledge_by_task": {"|".join(key): dict(value) for key, value in sorted(by_task.items())},
            "knowledge_by_variant": {"|".join(key): dict(value) for key, value in sorted(by_variant.items())},
            "no_path_to_witness_promotions": dict(promotions), "oracle_rows": len(exact_rows),
            "oracle_candidate_subsets_enumerated": enumerated, "oracle_results": dict(exact_summary),
            "legacy_restricted_comparison": {"old_run": str(OLD), "compared_cases": len(legacy),
                                             "all_success_states_identical": True, "all_mappings_identical": True,
                                             "all_success_connector_sets_and_lists_identical": True,
                                             "note": "Effective base hash differs due to maximum-inventory metadata; electrical restricted inventory matches Issue11."},
            "arm_pair_comparison": same_pairs, "all_original_inputs_unchanged": True,
            "elapsed_seconds": time.perf_counter() - started,
            "scope": "Independent synthetic connectivity/constraint audit. No EDA, calibrated PPA, manufacturing proof or new blind held-out evaluation."}


if __name__ == "__main__":
    try:
        report = audit()
    except Exception as exc:
        report = {"status": "FAIL", "error": str(exc), "traceback": traceback.format_exc(),
                  "auditor_source_sha256": h(Path(__file__).read_bytes())}
    output = OUT / "audit.json"
    output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    (OUT / "SHA256SUMS").write_text(
        h(Path(__file__).read_bytes()) + "  recompute.py\n" + h(output.read_bytes()) + "  audit.json\n",
        encoding="ascii")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)
