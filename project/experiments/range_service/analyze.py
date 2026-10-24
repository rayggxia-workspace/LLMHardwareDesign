"""Analyze immutable Issue68 conditional schedules, never execute a model.

All scientific artifact bytes are rehashed in both rounds. Arithmetic/resource
decomposition uses a predeclared subset of actual gzip witnesses. Independent
full schedule legality acceptance is a separate receiver responsibility.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import platform
import sys


ORGS = ("shared8", "shared2_6", "shared4_4", "shared6_2", "split2_6", "split4_4", "split6_2")
TILES, ROUTES, EXTS = (16, 32), ("reread", "spill"), (1, 16)


def canonical(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def desc(p):
    p = Path(p)
    return {"bytes": p.stat().st_size, "sha256": sha(p)}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def union_length(intervals):
    """Half-open time union, not the sum of overlapping operation durations."""
    total, lo, hi = 0, None, None
    for a, b in sorted(intervals):
        require(0 <= a <= b, "invalid interval")
        if lo is None:
            lo, hi = a, b
        elif a > hi:
            total += hi - lo
            lo, hi = a, b
        else:
            hi = max(hi, b)
    return total + (hi - lo if lo is not None else 0)


def key(row):
    return (row["organization"], row["tile"], row["norm_route"], row["ext_ii"])


def percent(new, old):
    return 100 * (new - old) / old if old else None


def paired(rows):
    expected = set(itertools.product(ORGS, TILES, ROUTES, EXTS))
    by = {key(r): r for r in rows}
    require(len(rows) == len(by) == 56 and set(by) == expected, "incomplete56 configuration grid")
    for field in ("task", "task_fingerprint", "state_bits", "commit_contract"):
        require(len({r[field] for r in rows}) == 1, "incomparable task/precision/contract")
    labels, tiles, routes, exts = [], [], [], []
    for suffix, tile, route, ext in itertools.product(("2_6", "4_4", "6_2"), TILES, ROUTES, EXTS):
        a, b = by[("shared" + suffix, tile, route, ext)], by[("split" + suffix, tile, route, ext)]
        require(a["best"]["cycles"] == b["best"]["cycles"] and
                all(a["best"][f] == b["best"][f] for f in ("memory", "payload_bytes", "wire_bytes")),
                "label-only control differs")
        labels.append({"partition": suffix, "tile": tile, "norm_route": route, "ext_ii": ext,
                       "delta_cycles": b["best"]["cycles"] - a["best"]["cycles"]})
    for org, route, ext in itertools.product(ORGS, ROUTES, EXTS):
        a, b = by[(org, 16, route, ext)], by[(org, 32, route, ext)]
        tiles.append({"organization": org, "norm_route": route, "ext_ii": ext,
                      "tile16_cycles": a["best"]["cycles"], "tile32_cycles": b["best"]["cycles"],
                      "tile32_vs16_percent": percent(b["best"]["cycles"], a["best"]["cycles"]),
                      "extra_payload_bytes": b["best"]["payload_bytes"] - a["best"]["payload_bytes"],
                      "tile16_R_bytes": a["best"]["memory"]["R"], "tile32_R_bytes": b["best"]["memory"]["R"],
                      "tile32_S4_shadow_bytes": b["best"]["memory"].get("S4", 0)})
    for org, tile, ext in itertools.product(ORGS, TILES, EXTS):
        a, b = by[(org, tile, "reread", ext)], by[(org, tile, "spill", ext)]
        routes.append({"organization": org, "tile": tile, "ext_ii": ext,
                       "reread_cycles": a["best"]["cycles"], "spill_cycles": b["best"]["cycles"],
                       "spill_vs_reread_percent": percent(b["best"]["cycles"], a["best"]["cycles"]),
                       "extra_payload_bytes": b["best"]["payload_bytes"] - a["best"]["payload_bytes"]})
    for org, tile, route in itertools.product(ORGS, TILES, ROUTES):
        a, b = by[(org, tile, route, 1)], by[(org, tile, route, 16)]
        exts.append({"organization": org, "tile": tile, "norm_route": route,
                     "ext1_cycles": a["best"]["cycles"], "ext16_cycles": b["best"]["cycles"],
                     "ext16_vs1_percent": percent(b["best"]["cycles"], a["best"]["cycles"])})
    fronts = []
    for ext, issue in itertools.product(EXTS, ("coarse8", "partitioned")):
        candidates = [r for r in rows if r["ext_ii"] == ext and
                      (r["organization"] == "shared8") == (issue == "coarse8")]
        winner = min(candidates, key=lambda r: (r["best"]["cycles"], key(r)))
        fronts.append({"ext_ii": ext, "issue_profile": issue, "winner": key(winner),
                       "cycles": winner["best"]["cycles"], "witness": winner["best"]["witness"]})
    ranked = []
    for ext, issue in itertools.product(EXTS, ("coarse8", "partitioned")):
        candidates = [r for r in rows if r["ext_ii"] == ext and
                      (r["organization"] == "shared8") == (issue == "coarse8")]
        for rank, r in enumerate(sorted(candidates, key=lambda x: (x["best"]["cycles"], key(x))), 1):
            ranked.append({"rank_within_same_ext_and_issue_profile": rank, "issue_profile": issue,
                           "organization": r["organization"], "tile": r["tile"], "norm_route": r["norm_route"],
                           "ext_ii": ext, **r["best"]})
    return {"frontiers": fronts, "ranking56": ranked, "label_controls24": labels,
            "tile_pairs28": tiles, "norm_pairs28": routes, "external_pairs28": exts,
            "ranking_scope": "two declared scheduling orders per candidate; shared8 coarse issue granularity is separate from same-context static partitions; no global optimum or physical boundary speedup claim"}


def category(n, task):
    m, kind = n["meta"], n["kind"]
    op = m.get("operation", kind)
    if op == "clone_full_committed_trial":
        return "R_full_trial_clone"
    if op in ("full_head_trial_RNE_shift1", "rescale_RNE_shift1") or kind == "trial_scale_epoch_update":
        return "R_rescale"
    if m.get("stream") == "R":
        if "token" in m and "attempt" in m:
            a = task["tokens"][m["token"]]["attempts"][m["attempt"]]
            if not a["accepted"]:
                return "R_failed_attempt"
            if m["attempt"] > 0:
                return "R_accepted_retry"
        return "R_regular_and_initial"
    if op in ("unit_prepass", "unit_min_scan") or kind == "full_hidden_finest_unit":
        return "V_unit_prepass"
    if op in ("load_mixed_code_plane", "load_mixed_unit_plane") or kind == "norm_source_layout_address":
        return "V_source_pack"
    if m.get("stream") == "norm":
        return "V_norm_and_bounded_proxies"
    return "control"


def decompose(w):
    nodes, task, caps = w["nodes"], w["task"], w["inventory"]["capacities"]
    makespan = w["makespan"]
    require(w["inventory"]["total_S8_lanes"] == 8 and w["inventory"]["active_contexts"] == 2,
            "changed arithmetic/context inventory")
    require(caps.get("SFU") == 1 and caps.get("BUS") == 1, "changed shared service inventory")
    require(w["inventory"]["bank_sizes"]["V"] == 16384 and w["inventory"]["bank_sizes"]["R"] == 32768,
            "changed private bank capacity")
    banks = w["inventory"]["bank_sizes"]
    require(all(banks.get("S" + str(i)) == 32768 for i in range(8)) and
            all(caps.get("PORT:" + b) == 1 for b in banks), "changed SRAM/1RW inventory")
    resident, extents = Counter(), defaultdict(list)
    for allocation in w["allocations"]:
        bank, offset, size = allocation["bank"], allocation["offset"], allocation["bytes"]
        require(size > 0 and 0 <= offset < offset + size <= banks[bank], "buffer capacity")
        resident[bank] += size
        extents[bank].append((offset, offset + size))
    for spans in extents.values():
        spans.sort()
        require(all(a[1] <= b[0] for a, b in zip(spans, spans[1:])), "buffer alias")
    require(dict(resident) == w["producer_audit"]["resident_bytes"], "resident byte account mismatch")
    intervals, events, area = defaultdict(list), defaultdict(list), Counter()
    categories, operations, product_counts = defaultdict(Counter), defaultdict(Counter), Counter()
    routes = defaultdict(Counter)
    cp = []
    rescale_read = rescale_write = rescale_elements = clone_read = clone_write = 0
    commits = aborts = 0
    for n in nodes:
        require(n["id"] == len(cp), "node order")
        require(n["end"] == n["start"] + n["duration"] and n["end"] <= makespan, "node bounds")
        cp.append(n["duration"] + max((cp[d] for d in n["deps"]), default=0))
        m, k = n["meta"], category(n, task)
        op = m.get("operation", n["kind"])
        a = categories[k]
        b = operations[op]
        for counter in (a, b):
            counter["nodes"] += 1
            counter["node_duration_sum_not_elapsed"] += n["duration"]
            counter["lane_work"] += m.get("lane_work", 0)
        if n["kind"] == "packet":
            payload, wire = m["payload_bytes"], m["wire_bytes"]
            for counter in (a, b):
                counter["payload_bytes"] += payload
                counter["wire_bytes"] += wire
                counter["physical_memory_read_bytes"] += ((payload + 15) // 16) * 16
                counter["physical_memory_write_bytes"] += ((payload + 15) // 16) * 16
            routes[k][m["src"] + "->" + m["dst"]] += payload
            if k == "R_full_trial_clone":
                clone_read += payload if m["src"] == "EXT" else 0
                clone_write += payload if m["dst"] == "EXT" else 0
            if k == "R_rescale":
                rescale_read += payload if m["src"] == "EXT" else 0
                rescale_write += payload if m["dst"] == "EXT" else 0
        elif n["kind"] == "math":
            for counter in (a, b):
                counter["physical_memory_read_bytes"] += ((m["read_bytes"] + 15) // 16) * 16
                counter["physical_memory_write_bytes"] += ((m["write_bytes"] + 15) // 16) * 16
            cells = m.get("K", 0) * m.get("Vtile", 0)
            if op == "decay_RNE_completeK_pred":
                product_counts["decay"] += cells
                product_counts["prediction"] += cells
            elif op == "delta_beta_RNE":
                product_counts["beta"] += m["Vtile"]
            elif op == "outer_RNE_guard":
                product_counts["outer"] += cells
            elif op == "outer_RNE_guard_fragment":
                product_counts["outer"] += m["write_bytes"] // (m["state_bits"] // 8)
            elif op == "new_state_completeK_output":
                product_counts["output"] += cells
            elif op == "rescale_RNE_shift1":
                rescale_elements += m["read_bytes"] // (m["state_bits"] // 8)
        if n["kind"] == "atomic_group_commit":
            commits += 1
        if n["kind"] == "abort_unpublished_generation":
            aborts += 1
        for r in n["reservations"]:
            resource = r["resource"]
            lo, hi, amount = n["start"] + r["offset"], n["start"] + r["offset"] + r["duration"], r["amount"]
            intervals[resource].append((lo, hi))
            events[resource].extend(((lo, amount), (hi, -amount)))
            area[resource] += (hi - lo) * amount
    utilization = []
    for resource in intervals:
        use = peak = 0
        for _, delta in sorted(events[resource]):
            use += delta
            peak = max(peak, use)
            require(0 <= use <= caps[resource], "resource overcommit")
        require(use == 0, "unreleased resource")
        busy = union_length(intervals[resource])
        utilization.append({"resource": resource, "capacity": caps[resource], "busy_union_cycles": busy,
                            "capacity_time": area[resource], "high_water": peak,
                            "utilization_percent": 100 * area[resource] / (caps[resource] * makespan),
                            "resource_lower_bound_cycles": (area[resource] + caps[resource] - 1) // caps[resource]})
    utilization.sort(key=lambda x: (-x["resource_lower_bound_cycles"], x["resource"]))
    cost = task.get("source_range_cost")
    if cost:
        require(dict(product_counts) == cost["integer_products_executed"], "actual DAG products differ from source range")
        require(rescale_read == cost["rescale_state_read_bytes"] and rescale_write == cost["rescale_state_write_bytes"] and
                rescale_elements == cost["rescale_RNE_elements"], "rescale costs differ from actual events")
    expected_commits = sum(any(a["accepted"] for a in t["attempts"]) for t in task["tokens"])
    expected_aborts = sum(not a["accepted"] for t in task["tokens"] for a in t["attempts"])
    require(commits == expected_commits and aborts == expected_aborts, "commit/abort event mismatch")
    require(sum(c["nodes"] for c in categories.values()) == len(nodes), "double-counted node categories")
    if "operation_counters" in w:
        require(sum(c["payload_bytes"] for c in categories.values()) == w["operation_counters"]["payload_bytes"] and
                sum(c["wire_bytes"] for c in categories.values()) == w["operation_counters"]["wire_bytes"],
                "packet byte account mismatch")
    if "norm_rows" in task:
        nr = task["norm_rows"]
        require(operations["unit_prepass"]["payload_bytes"] == nr * 5120 and
                operations["load_mixed_code_plane"]["payload_bytes"] + operations["load_mixed_unit_plane"]["payload_bytes"] == nr * 25600 and
                operations["gamma_stream"]["payload_bytes"] == nr * 10240 and
                operations["publish_fresh_A8"]["payload_bytes"] == nr * 2612,
                "norm metadata/packing/physical-payload account mismatch")
    resource_bound = max((x["resource_lower_bound_cycles"] for x in utilization), default=0)
    require(max(cp, default=0) <= makespan and resource_bound <= makespan, "invalid lower bound")
    return {"config": w["config"], "task_fingerprint": w["task_fingerprint"], "makespan": makespan,
            "resource_occupancy": utilization, "precedence_lower_bound": max(cp, default=0),
            "resource_lower_bound": resource_bound,
            "total_lane_capacity_time": sum(v for k, v in area.items() if k.startswith("LANE:")),
            "eight_lane_utilization_percent": 100 * sum(v for k, v in area.items() if k.startswith("LANE:")) / (8 * makespan),
            "sum_node_duration_is_not_elapsed": sum(n["duration"] for n in nodes),
            "categories_disjoint": dict(categories), "packet_routes_by_category": dict(routes), "operations": dict(operations),
            "source_event_cost_crosscheck": {"integer_products": dict(product_counts), "rescale_external_read_bytes": rescale_read,
                                             "rescale_external_write_bytes": rescale_write, "rescale_RNE_elements": rescale_elements,
                                             "full_trial_clone_external_read_bytes": clone_read, "full_trial_clone_external_write_bytes": clone_write,
                                             "commits": commits, "aborts": aborts},
            "buffer_resident_bytes": dict(resident),
            "resource_interpretation": "conditional service demand/occupancy, not hardware measurements; maxima and interval unions are not additive elapsed time"}


def verify_run(folder):
    folder = Path(folder)
    m = load(folder / "manifest.json")
    require(m.get("schema") == "issue68-service/1", "source schema")
    for name, d in m["artifacts"].items():
        require(Path(name).name == name and "\\" not in name, "unsafe artifact path")
        p = folder / name
        require(p.is_file() and desc(p) == {k: d[k] for k in ("bytes", "sha256")}, "source artifact mismatch")
    x = load(folder / "metrics.json")
    require(x.get("status") == "PASS_CONDITIONAL_SCHEDULE" and x["source"] == m["source"], "unaccepted source execution")
    return m, x


def analyze(root, out, binding):
    require(binding.get("analyze_sha256") == sha(__file__) and binding.get("commit"), "analysis source binding")
    root, out = Path(root).resolve(), Path(out).resolve()
    require(out.parent == root and not out.exists(), "new output must stay in task root")
    summary = {"schema": "issue68-analysis/1", "source": binding, "suites": {},
               "status": "PASS_CONDITIONAL_ANALYSIS", "physical_boundary_frozen": False,
               "qualification": "same saved S32D31 math+contracts; ext1/16 and S8 digit/merge service assumptions uncalibrated; norm32 is independent from R32/256, not a complete model; full schedule acceptance belongs to receive_service"}
    sources = {}
    for suite in ("native", "legacy"):
        paths = [root / f"service-{suite}{r:02d}" for r in (1, 2)]
        m1, x1 = verify_run(paths[0])
        m2, x2 = verify_run(paths[1])
        require(m1["source"] == m2["source"] and m1["config"] == m2["config"] and
                m1["artifacts"] == m2["artifacts"], "two-round scientific SHA mismatch")
        require(canonical(x1) == canonical(x2), "two-round metrics mismatch")
        rows = x1["results"]
        report = paired(rows)
        by = {key(r): r for r in rows}
        selected = set(itertools.product(("shared4_4",), TILES, ROUTES, EXTS))
        selected.update((o, 16, "reread", 1) for o in ("shared8", "shared2_6", "shared6_2"))
        selected.update(tuple(f["winner"]) for f in report["frontiers"])
        breakdowns = []
        for k in sorted(selected):
            name = by[k]["best"]["witness"]
            witness = json.loads(gzip.decompress((paths[0] / name).read_bytes()))
            breakdown = decompose(witness)
            breakdown["witness"] = name
            breakdown["artifact"] = m1["artifacts"][name]
            breakdowns.append(breakdown)
        report.update(two_round={"status": "PASS_BYTE_IDENTICAL_SCIENCE", "files_each": len(m1["artifacts"]),
                                 "metrics": m1["artifacts"]["metrics.json"], "manifests": [desc(p / "manifest.json") for p in paths],
                                 "note": "manifest aggregation paths/job/environment provenance may differ; all scientific artifacts actually rehashed"},
                      decomposition=breakdowns,
                      decomposition_scope="predeclared shared4_4 all8, shared8/shared2_6/shared6_2 baseline ext1/tile16/reread, plus each issue/ext frontier winner; all other cases ranking/pairs only",
                      norm_rows=32, R_tokens=len(witness["task"]["tokens"]),
                      contract=rows[0]["commit_contract"], task_fingerprint=rows[0]["task_fingerprint"])
        summary["suites"][suite] = report
        sources[suite] = [{"directory": p.name, "manifest": desc(p / "manifest.json")} for p in paths]
    out.mkdir()
    (out / "analysis.json").write_bytes(canonical(summary))
    manifest = {"schema": "issue68-analysis/1", "source": binding, "inputs": sources,
                "environment": {"python": sys.version, "platform": platform.platform()},
                "artifacts": {"analysis.json": desc(out / "analysis.json")}}
    (out / "manifest.json").write_bytes(canonical(manifest))
    return {"status": summary["status"], "artifact": manifest["artifacts"]["analysis.json"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--binding", required=True)
    a = p.parse_args()
    print(json.dumps(analyze(a.root, a.out, load(a.binding))))


if __name__ == "__main__":
    main()
