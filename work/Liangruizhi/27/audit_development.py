"""Independent development-result audit; does not import project code."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import time
import zipfile


ORDER = ("O", "m", "l")


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def bits(placement):
    return tuple(placement[name] for name in ORDER)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(row):
    return canon(row["config"]), bits(row["placement"]), tuple(row["disabled_links"]), row["workload"]


def independent_reservation(cfg, workload, placement):
    q, k, d = cfg["max_query_tile"], cfg["key_tile"], workload["head_dim"]
    sizes = [("Q", q*d*4), ("K", k*d*4), ("V", k*d*4), ("S", q*k*4),
             ("P", q*k*4), ("T", q*d*4), ("O", q*d*4), ("m", q*4), ("l", q*4), ("a", q*4)]
    homes = {"Q": 0, "K": 0, "V": 0, "S": 1, "P": 1, "T": 1,
             "O": placement["O"], "m": placement["m"], "l": placement["l"], "a": placement["m"]}
    used = [0, 0]
    slots = {}
    for name, size in sizes:
        home = homes[name]
        start = ((used[home] + 63)//64)*64
        slots[name] = {"bank": home, "offset": start, "bytes": size}
        used[home] = start + size
    scratch = {"M": (q*d + k*d + q*k)*4,
               "V": max(2*q*k + 5*q, 3*q*d + q)*4}
    return used, scratch, slots


def independent_feasibility(cfg, workload, placement, disabled):
    used, scratch, _ = independent_reservation(cfg, workload, placement)
    for b in (0, 1):
        if used[b] > cfg["bank_bytes"][b]:
            return False, "capacity B" + str(b)
    for engine in ("M", "V"):
        if scratch[engine] > cfg["scratch_bytes"][engine]:
            return False, "scratch " + engine
    required = {"M0", "M1", "D0", "V1"}
    if any(placement[name] == 0 for name in ORDER):
        required.add("V0")
    if placement["O"] == 1:
        required.add("D1")
    for link in disabled:
        if link in required:
            return False, "missing static link " + link
    return True, None


def audit_witness(witness, errors):
    row, graph, out = (witness[k] for k in ("row", "graph", "schedule"))
    nodes = {task["id"]: task for task in graph["tasks"]}
    cfg, workload = row["config"], row["workload_data"]
    expected_caps = {"compute:M": 1, "compute:V": 1, "external": 1}
    for engine in "MVD":
        expected_caps["endpoint:"+engine] = 1
        for bank in (0, 1):
            expected_caps[f"link:{engine}{bank}"] = 1
    for bank in (0, 1):
        if cfg["bank_ports"] == "1R1W":
            expected_caps[f"bank:{bank}:R"] = expected_caps[f"bank:{bank}:W"] = 1
        else:
            expected_caps[f"bank:{bank}:RW"] = 2 if cfg["bank_ports"] == "2RW" else 1
    for name in graph["slots"]:
        expected_caps["address:"+name] = 1
    if graph["capacities"] != expected_caps:
        errors.append("witness resource inventory differs from declared contract")
    if "endpoint_staging_bytes" in cfg and graph.get("endpoint_staging_bytes") != {e: cfg["endpoint_staging_bytes"] for e in "MVD"}:
        errors.append("witness endpoint staging inventory mismatch")
    events = out["events"]
    if len(nodes) != len(graph["tasks"]) or len(events) != len(nodes):
        errors.append("witness event/task cardinality")
    spans = {event["id"]: (event["start"], event["end"]) for event in events}
    if len(spans) != len(events) or set(spans) != set(nodes):
        errors.append("witness missing/duplicate/unknown ids")
        return
    intervals = defaultdict(list)
    for name, (start, end) in spans.items():
        task = nodes[name]
        if type(start) is not int or type(end) is not int or start < 0 or end-start != task["duration"]:
            errors.append("witness invalid task interval")
        for dep in task["deps"]:
            if spans[dep][1] > start:
                errors.append("witness dependency violated")
        for resource, amount in task["resources"].items():
            intervals[resource].append((start, end, amount))
        if task["kind"] == "transfer":
            engine, obj = task["engine"], task["object"]
            home = graph["slots"][obj]["bank"]
            port = task["direction"] if cfg["bank_ports"] == "1R1W" else "RW"
            expected_resources = {f"endpoint:{engine}": 1, f"link:{engine}{home}": 1,
                f"bank:{home}:{port}": 1, f"address:{obj}": 1}
            rate = min(cfg["bank_port_bytes_per_cycle"], cfg["link_bytes_per_cycle"])
            if engine == "D":
                expected_resources["external"] = 1
                rate = min(rate, cfg["external_bytes_per_cycle"])
            duration = cfg["burst_setup_cycles"]+(task["bytes"]+rate-1)//rate
            if task["resources"] != expected_resources or task["duration"] != duration:
                errors.append("witness transfer duration/reservation differs from contract")
        elif task["resources"] != {"compute:"+task["engine"]: 1}:
            errors.append("witness compute inventory mismatch")
    # Independent direct interval summation at every start, not the project
    # scheduler's availability counters or its end/start boundary sweep.
    for resource, uses in intervals.items():
        peak = max(sum(amount for start, end, amount in uses if start <= t < end)
                   for t in {start for start, _, _ in uses})
        if peak > graph["capacities"][resource]:
            errors.append("witness resource oversubscribed " + resource)
    if max(end for _, end in spans.values()) != out["makespan"] or out["makespan"] != row["makespan"]:
        errors.append("witness makespan mismatch")
    expected_sha = hashlib.sha256((canon(events)+"\n").encode()).hexdigest()
    if expected_sha != row["best_events_sha256"]:
        errors.append("witness event digest mismatch")
    used, scratch, slots = independent_reservation(row["config"], row["workload_data"], row["placement"])
    if slots != graph["slots"] or used != graph["bank_reserved_bytes"] or scratch != graph["scratch_reserved_bytes"]:
        errors.append("witness static slot/reservation mismatch")
    # Version audit follows emitted object accesses, independently from deps.
    writes, readers = {}, defaultdict(list)
    for access in graph["accesses"]:
        obj, name = access["object"], access["id"]
        start, end = spans[name]
        slot = graph["slots"][obj]
        if (access["bank"], access["offset"]) != (slot["bank"], slot["offset"]) or not 0 < access["bytes"] <= slot["bytes"]:
            errors.append("witness access outside static slot")
        if access["direction"] == "R":
            if obj not in writes or spans[writes[obj][0]][1] > start or access["bytes"] > writes[obj][1]:
                errors.append("witness wrong/uninitialized read version")
            readers[obj].append(name)
        else:
            if obj in writes and spans[writes[obj][0]][1] > start:
                errors.append("witness WAW")
            if any(spans[prior][1] > start for prior in readers[obj]):
                errors.append("witness WAR")
            readers[obj] = []
            writes[obj] = name, access["bytes"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected-source", default=None)
    args = parser.parse_args()
    start = time.time()
    source = args.project/"project/experiments/state_ports"
    cases = json.loads((args.run/"cases.json").read_text())
    static = json.loads((args.run/"static-choices.json").read_text())
    summary = json.loads((args.run/"summary.json").read_text())
    manifest = json.loads((args.run/"manifest.json").read_text())
    source_names = ("run.py", "graph.py", "scheduler.py", "experiment.json")
    if manifest["development_run"]:
        source_bytes = {name: (source/name).read_bytes() for name in source_names}
    else:
        source_bytes = {name: subprocess.check_output(["git", "show", manifest["source_commit"] +
            ":project/experiments/state_ports/" + name], cwd=args.project) for name in source_names}
    spec = json.loads(source_bytes["experiment.json"])
    witnesses = json.loads(gzip.decompress((args.run/"witnesses.json.gz").read_bytes()))
    workloads = {w["id"]: w for w in spec["workloads"]}
    errors, notes = [], []
    trace_file = args.project/"project/experiments/qwen3_trace/results/issue-23-run01/evidence.zip"
    trace_binding = json.loads((args.run/"trace-binding.json").read_text())
    trace_checks = {"archive_sha256": digest(trace_file) == spec["trace_archive_sha256"],
                    "binding_archive_sha256": trace_binding["archive_sha256"] == spec["trace_archive_sha256"]}
    with zipfile.ZipFile(trace_file) as archive:
        trace_events = [json.loads(line) for line in gzip.decompress(archive.read("primary-events.jsonl.gz")).splitlines()]
    selected = []
    for call, q, length in ((0, 32, 32), (16, 1, 48)):
        for stage, shape in (("attention.query_post_rope", [1, 16, q, 128]),
                             ("attention.key_cached_post_rope", [1, 8, length, 128])):
            matches = [e for e in trace_events if e.get("schedule") == "single_prefill"
                and e.get("layer") == 0 and e.get("call") == call and e.get("stage") == stage]
            key = str(call) + ":" + stage
            trace_checks[key] = len(matches) == 1 and matches[0]["shape"] == shape and matches[0]["dtype"] == "torch.float32"
            if len(matches) == 1:
                selected.append(matches[0])
    trace_checks["exact_observation_records"] = selected == trace_binding["observations"]
    if not all(trace_checks.values()):
        errors.append("independent trace-binding check failed")
    manifest_checks = {name: {"bytes": (args.run/name).stat().st_size == info["bytes"],
                              "sha256": digest(args.run/name) == info["sha256"]}
                       for name, info in manifest["files"].items()}
    if any(not all(check.values()) for check in manifest_checks.values()):
        errors.append("run manifest byte/hash mismatch")
    if hashlib.sha256(source_bytes["experiment.json"]).hexdigest() != manifest["config_sha256"]:
        errors.append("audit input config differs from run config")
    if args.expected_source and manifest["source_commit"] != args.expected_source:
        errors.append("source commit differs from expected frozen commit")
    if not manifest["development_run"] and manifest["dirty_at_start"] is not False:
        errors.append("formal run did not record a clean source start")
    expected = set()
    sweep = spec["sweep"]
    for tile, ports, bank, bandwidth, placement, disabled, workload in itertools.product(
            sweep["key_tiles"], sweep["port_types"], sweep["bank_profiles"],
            sweep["bandwidth_profiles"], itertools.product((0, 1), repeat=3),
            sweep["disabled_links"], spec["workloads"]):
        cfg = {**spec["base"], **bandwidth, "key_tile": tile, "bank_ports": ports, "bank_bytes": bank}
        expected.add((canon(cfg), placement, tuple(disabled), workload["id"]))
    keys = Counter(identity(row) for row in cases)
    if set(keys) != expected or any(count != 1 for count in keys.values()):
        errors.append("Cartesian missing/duplicate/unexpected case")
    by_key = {identity(row): row for row in cases}
    statuses, causes = Counter(), Counter()
    for row in cases:
        workload, cfg = workloads[row["workload"]], row["config"]
        feasible, cause = independent_feasibility(cfg, workload, row["placement"], row["disabled_links"])
        statuses[row["status"]] += 1
        if feasible != (row["status"] == "feasible"):
            errors.append("analytic feasibility mismatch " + repr(identity(row)))
        if not feasible:
            causes[cause] += 1
            if not row.get("reason", "").startswith(cause):
                errors.append("first blocker attribution mismatch")
            continue
        values = row["policy_cycles"]
        chosen = min(sweep["policies"], key=lambda p: values[p])
        if set(values) != set(sweep["policies"]) or chosen != row["chosen_policy"] or values[chosen] != row["makespan"]:
            errors.append("best policy mismatch")
        q, n, d, k = workload["queries"], workload["keys"], workload["head_dim"], cfg["key_tile"]
        tiles = (n+k-1)//k
        expected_traffic = {"D": 8*d*(q+n), "M": 8*d*(tiles*q+n)+8*q*n,
                            "V": 12*q*d+12*q+8*q*n+tiles*(24*q+12*q*d)}
        if row["traffic"] != expected_traffic or row["matrix_macs"] != 2*q*n*d or row["task_count"] != 10+23*tiles:
            errors.append("analytic work/traffic/task count mismatch")
        used, scratch, _ = independent_reservation(cfg, workload, row["placement"])
        if used != row["bank_reserved_bytes"] or scratch != row["scratch_reserved_bytes"]:
            errors.append("reservation mismatch")
        if row["makespan"] < max(row["lower_bounds"]["dependency"], row["lower_bounds"]["resource"]):
            errors.append("reported makespan below lower bound")
    static_groups = defaultdict(lambda: defaultdict(list))
    for row in cases:
        if row["workload"].startswith("observed"):
            static_groups[(canon(row["config"]), tuple(row["disabled_links"]))][bits(row["placement"])].append(row)
    expected_static = {}
    for group, placements in static_groups.items():
        options = []
        for assignment, pair in placements.items():
            if len(pair) != 2 or {r["workload"] for r in pair} != {"observed-prefill32", "observed-decode48"}:
                errors.append("static group missing or duplicate observed phase")
            if all(r["status"] == "feasible" for r in pair):
                options.append({"placement": dict(zip(ORDER, assignment)),
                    "sum_query_tile_cycles": sum(r["makespan"] for r in pair),
                    "phases": {r["workload"]: r["makespan"] for r in pair}})
        options.sort(key=lambda x: (x["sum_query_tile_cycles"], bits(x["placement"])))
        envelope = sum(min(x["phases"][phase] for x in options)
                       for phase in ("observed-prefill32", "observed-decode48")) if options else None
        expected_static[group] = {"config": json.loads(group[0]), "disabled_links": list(group[1]),
            "options": options, "best": options[0] if options else None,
            "phasewise_mapping_lower_envelope": envelope}
    actual_static = {(canon(row["config"]), tuple(row["disabled_links"])): row for row in static}
    if len(actual_static) != len(static) or set(actual_static) != set(expected_static):
        errors.append("static group missing/duplicate")
    for key, wanted in expected_static.items():
        if wanted != actual_static.get(key):
            errors.append("independently rebuilt static choice differs")
    mask_pairs = Counter()
    comparison_fields = ("policy_cycles", "makespan", "best_events_sha256", "task_count", "traffic",
                         "matrix_macs", "bank_reserved_bytes", "scratch_reserved_bytes", "lower_bounds")
    for key, row in by_key.items():
        if not key[2]:
            continue
        full = by_key[key[0], key[1], (), key[3]]
        if row["status"] == "feasible":
            mask_pairs["retained_feasible"] += 1
            if full["status"] != "feasible" or any(row[k] != full[k] for k in comparison_fields):
                errors.append("disabled retained-placement invariance violated")
        elif full["status"] == "feasible":
            mask_pairs["lost_feasible"] += 1
        else:
            mask_pairs["already_infeasible"] += 1
    static_masks = Counter()
    for key, row in actual_static.items():
        if not key[1]:
            continue
        full = actual_static[key[0], ()]
        original = {bits(x["placement"]): x for x in full["options"]}
        if any(original.get(bits(x["placement"])) != x for x in row["options"]):
            errors.append("disabled static option not identical full subset")
        if not row["best"]:
            static_masks["no_common_feasible_placement"] += 1
        elif not full["best"] or row["best"]["sum_query_tile_cycles"] < full["best"]["sum_query_tile_cycles"]:
            errors.append("disabled mask improved static minimum")
        elif row["best"]["sum_query_tile_cycles"] == full["best"]["sum_query_tile_cycles"]:
            static_masks["same_best"] += 1
        else:
            static_masks["worse_best"] += 1
    for witness in witnesses:
        witness["row"]["workload_data"] = workloads[witness["row"]["workload"]]
        audit_witness(witness, errors)
    pair_groups = defaultdict(list)
    for witness in witnesses:
        row = witness["row"]
        pair_groups[(canon(row["config"]), row["workload"])].append(witness)
    for pair in pair_groups.values():
        if len(pair) != 2 or {bits(w["row"]["placement"]) for w in pair} != {(0, 0, 0), (1, 1, 1)}:
            errors.append("witness pair missing")
            continue
        a, b = (x["graph"] for x in pair)
        for field in ("capacities", "traffic", "matrix_macs", "scratch_reserved_bytes", "bank_capacity_bytes"):
            if a[field] != b[field]:
                errors.append("witness same-resource pair changed " + field)
        strip = lambda graph: [{k: v for k, v in task.items() if k != "resources"} for task in graph["tasks"]]
        if strip(a) != strip(b):
            errors.append("placement changed duration/deps/compute work")
        if a.get("endpoint_staging_bytes") != b.get("endpoint_staging_bytes"):
            errors.append("placement changed endpoint staging inventory")
        if sum(a["bank_reserved_bytes"]) != sum(b["bank_reserved_bytes"]):
            errors.append("placement changed total static buffer payload/reservation")
        for name in ("Q", "K", "V", "S", "P", "T"):
            if a["slots"][name] != b["slots"][name]:
                errors.append("placement changed nonstate slot")
    if summary["counts"] != {"feasible": statuses["feasible"], "infeasible": statuses["infeasible"],
            "validated_schedules": statuses["feasible"]*4, "zero_effect_pairs": statuses["feasible"]}:
        errors.append("summary count mismatch")
    if summary["static_groups"] != len(static) or summary["witness_count"] != len(witnesses):
        errors.append("summary group/witness count mismatch")
    representative = []
    for port in sweep["port_types"]:
        target = next(row for row in actual_static.values() if row["config"]["key_tile"] == 16
            and row["config"]["bank_ports"] == port and row["config"]["bank_bytes"] == [65536, 65536]
            and row["config"]["bank_port_bytes_per_cycle"] == 64 and not row["disabled_links"])
        representative.append({"ports": port, "all_full_options": target["options"], "best": target["best"]})
    notes.extend([
        "JSON serialization sorts placement keys as O,l,m; audited with explicit O,m,l extraction. run.py groups before serialization, so its present insertion order is correct but fragile if read-back is added.",
        "The mask model rejects required direct edges; there is no alternate routing. Retained same-placement graphs have identical service cost; disabled static options must be a subset.",
        "Failure reason is the first capacity/scratch/link blocker, not a proof of a unique failure cause.",
        "All durations, rates, capacities, scratch and FP32 operand bytes are model assumptions. No real port/RTL/cycle/PPA calibration or INT8 result.",
        "Changing placement also moves a together with m; the actual compared state placement is O,m,l with a tied to m.",
        "The objective is an equal-count sum of one observed prefill query-head tile and one observed decode query-head tile, not prompt/model end-to-end latency.",
        "Each phase may choose its best policy from the same four-policy budget; the placement is shared. Optimality of those large-graph schedules is not established.",
        "Only 24 schedules are archived as witnesses; the other feasible rows archive cycles and event SHA, not full events. This audit validates all case metadata and all archived witnesses, not all 4896 original full schedules.",
    ])
    report = {"status": "PASS" if not errors else "FAIL", "errors": errors, "notes": notes,
        "run_directory": str(args.run), "development_run": manifest["development_run"],
        "source_commit": manifest["source_commit"],
        "source_is_not_frozen_for_formal_claims": manifest["development_run"],
        "source_read_mode": "current worktree (development only)" if manifest["development_run"] else "frozen local Git objects at manifest source_commit",
        "source_snapshot_sha256": {name: hashlib.sha256(raw).hexdigest() for name, raw in source_bytes.items()},
        "audit_script_sha256": digest(Path(__file__)), "manifest_checks": manifest_checks,
        "independent_trace_binding_checks": trace_checks,
        "expected_cartesian_cases": len(expected), "actual_cases": len(cases), "statuses": dict(statuses),
        "first_blocker_counts": dict(causes), "static_groups_rebuilt": len(expected_static),
        "mask_case_pairs": dict(mask_pairs), "static_mask_groups": dict(static_masks),
        "witnesses_independently_validated": len(witnesses), "same_inventory_witness_pairs": len(pair_groups),
        "representative_placements_explicit_order_O_m_l": representative,
        "elapsed_seconds": time.time()-start}
    args.out.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("representative_placements_explicit_order_O_m_l", "notes")}, indent=2))


if __name__ == "__main__":
    main()
