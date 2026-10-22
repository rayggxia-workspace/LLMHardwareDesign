"""Reproducible service-cost sweep; all cycles are uncalibrated model outputs."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
import json
import platform
import subprocess
import time
import zipfile
from collections import Counter
from pathlib import Path

from graph import Infeasible, make_graph, verify_access_order
from scheduler import schedule, validate_schedule

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def encoded(x):
    return (json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))+"\n").encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def trace_binding(spec):
    archive = ROOT/"project/experiments/qwen3_trace/results/issue-23-run01/evidence.zip"
    if sha(archive.read_bytes()) != spec["trace_archive_sha256"]:
        raise ValueError("trace archive SHA mismatch")
    with zipfile.ZipFile(archive) as z:
        events = [json.loads(x) for x in gzip.decompress(z.read("primary-events.jsonl.gz")).splitlines()]
    selected = []
    for call, q, n in ((0, 32, 32), (16, 1, 48)):
        items = {e["stage"]: e for e in events if e["schedule"] == "single_prefill" and e["layer"] == 0 and e["call"] == call}
        for stage, shape in (("attention.query_post_rope", [1, 16, q, 128]),
                             ("attention.key_cached_post_rope", [1, 8, n, 128])):
            if items[stage]["shape"] != shape or items[stage]["dtype"] != "torch.float32":
                raise ValueError("actual trace dimensions/precision changed")
            selected.append(items[stage])
    return dict(archive_sha256=spec["trace_archive_sha256"], observations=selected,
                limitation="metadata binding only; online tiled execution is a new model, not observed eager schedule")


def lower_bounds(tasks, capacities):
    by_id = {t["id"]: t for t in tasks}
    memo = {}
    def path(name):
        if name not in memo:
            t = by_id[name]
            memo[name] = t["duration"] + max((path(d) for d in t["deps"]), default=0)
        return memo[name]
    busy = Counter()
    for t in tasks:
        for resource, amount in t["resources"].items():
            busy[resource] += amount*t["duration"]
    bounds = {r: (value+capacities[r]-1)//capacities[r] for r, value in busy.items()}
    return dict(dependency=max(map(path, by_id)), resource=max(bounds.values()),
                resource_bounds=bounds, occupied_resource_cycles=dict(busy))


def run(output, dev=False):
    if output.exists():
        raise ValueError("refuse to replace existing output")
    dirty = git("status", "--porcelain")
    if dirty and not dev:
        raise ValueError("formal run requires a clean source tree")
    source = git("rev-parse", "HEAD")
    spec = json.loads((HERE/"experiment.json").read_text(encoding="utf-8"))
    binding = trace_binding(spec)
    output.mkdir(parents=True)
    start = time.time()
    rows, witnesses, counts = [], [], Counter()
    sweep = spec["sweep"]
    for tile, ports, banks, bw, bits, disabled in itertools.product(
            sweep["key_tiles"], sweep["port_types"], sweep["bank_profiles"],
            sweep["bandwidth_profiles"], itertools.product((0, 1), repeat=3), sweep["disabled_links"]):
        cfg = dict(spec["base"], **bw, key_tile=tile, bank_ports=ports, bank_bytes=banks)
        placement = dict(zip(("O", "m", "l"), bits))
        common = dict(config=cfg, placement=placement, disabled_links=disabled)
        for workload in spec["workloads"]:
            row = dict(common, workload=workload["id"])
            try:
                graph = make_graph(cfg, workload, placement, disabled)
            except Infeasible as exc:
                rows.append(dict(row, status="infeasible", reason=str(exc)))
                counts["infeasible"] += 1
                continue
            results = {}
            for policy in sweep["policies"]:
                result = schedule(graph["tasks"], graph["capacities"], policy)
                checked = validate_schedule(graph["tasks"], graph["capacities"], result)
                if not checked["valid"] or verify_access_order(graph, result):
                    raise AssertionError((row, policy, checked, verify_access_order(graph, result)))
                results[policy] = result
                counts["validated_schedules"] += 1
            best_policy = min(sweep["policies"], key=lambda p: results[p]["makespan"])
            best = results[best_policy]
            # Metadata-only partition labels cannot affect any hardware task.
            joined = make_graph(cfg, workload, placement, disabled, boundary="joined")
            if any(joined[k] != graph[k] for k in ("tasks", "capacities", "slots", "scratch_reserved_bytes")):
                raise AssertionError("boundary rename changed hardware")
            if schedule(joined["tasks"], joined["capacities"], best_policy) != best:
                raise AssertionError("boundary rename changed schedule")
            counts["zero_effect_pairs"] += 1
            bounds = lower_bounds(graph["tasks"], graph["capacities"])
            assert best["makespan"] >= max(bounds["dependency"], bounds["resource"])
            row.update(status="feasible", policy_cycles={p: r["makespan"] for p, r in results.items()},
                       chosen_policy=best_policy, makespan=best["makespan"],
                       best_events_sha256=sha(encoded(best["events"])), task_count=len(graph["tasks"]),
                       bank_reserved_bytes=graph["bank_reserved_bytes"], scratch_reserved_bytes=graph["scratch_reserved_bytes"],
                       traffic=graph["traffic"], matrix_macs=graph["matrix_macs"], lower_bounds=bounds)
            rows.append(row)
            counts["feasible"] += 1
            if tile == 16 and banks == [65536, 65536] and bw["bank_port_bytes_per_cycle"] == 64 and not disabled and bits in ((0, 0, 0), (1, 1, 1)):
                witnesses.append(dict(row=row, graph=graph, schedule=best))
    # One static mapping serves both phases. Summation is a declared equal-count
    # query-tile objective, NOT the latency of a prompt or a full model.
    static = []
    groups = {}
    for row in rows:
        if row["workload"].startswith("observed"):
            key = encoded(dict(config=row["config"], disabled_links=row["disabled_links"])).decode()
            groups.setdefault(key, {}).setdefault(tuple(row["placement"].values()), []).append(row)
    for key, placements in groups.items():
        options = []
        for bits, pair in placements.items():
            if len(pair) == 2 and all(x["status"] == "feasible" for x in pair):
                options.append(dict(placement=dict(zip(("O", "m", "l"), bits)),
                                    sum_query_tile_cycles=sum(x["makespan"] for x in pair),
                                    phases={x["workload"]: x["makespan"] for x in pair}))
        options.sort(key=lambda x: (x["sum_query_tile_cycles"], tuple(x["placement"].values())))
        static.append(dict(**json.loads(key), options=options, best=options[0] if options else None,
                           phasewise_mapping_lower_envelope=sum(min(x["phases"][p] for x in options)
                           for p in ("observed-prefill32", "observed-decode48")) if options else None))
    payloads = {"cases.json": rows, "static-choices.json": static, "trace-binding.json": binding}
    for name, data in payloads.items():
        (output/name).write_bytes(encoded(data))
    (output/"witnesses.json.gz").write_bytes(gzip.compress(encoded(witnesses), mtime=0))
    summary = dict(status="PASS", counts=dict(counts), static_groups=len(static),
                   witness_count=len(witnesses), scope=spec["selection"], calibration=spec["calibration"])
    (output/"summary.json").write_bytes(encoded(summary))
    if git("rev-parse", "HEAD") != source or (not dev and git("status", "--porcelain")):
        raise ValueError("source changed during formal run")
    manifest = dict(source_commit=source, development_run=dev, dirty_at_start=dirty if dev else False,
                    python=platform.python_version(), started_unix=start, elapsed_seconds=time.time()-start,
                    config_sha256=sha((HERE/"experiment.json").read_bytes()),
                    files={p.name: dict(bytes=p.stat().st_size, sha256=sha(p.read_bytes())) for p in sorted(output.iterdir())})
    (output/"manifest.json").write_bytes(encoded(manifest))
    print(json.dumps(summary))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    run(args.output, args.development)
