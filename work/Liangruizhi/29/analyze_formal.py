"""Independent stdlib audit of Issue29 frozen programs and result summaries.

Does not import project generator, scheduler, verifier or RTL internals. Optional
recorded traces establish per-transfer ACK intervals; untraced cases have only
the explicitly reported summary-level checks, never a claimed full replay.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import re

POLICIES = ("critical", "fifo", "shortest", "longest")
PHASES = ("prefill32", "decode48")
MODES = (0, 1, 2)
DEPTHS = (1, 2, 4)
MASKS = (63, 59, 31)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def placement(row):
    # Intentionally explicit: JSON dictionary order is O,l,m in the index.
    return "".join(str(row["placement"][key]) for key in ("O", "m", "l"))


def key(row, mask=None):
    return (row["mode"], row["depth"], row["phase"], placement(row),
            row["policy"], row["stalls"], row["mask"] if mask is None else mask)


def case_name(parts):
    m, d, phase, p, policy, s, mask = parts
    return f"m{m}-d{d}-{phase}-p{p}-{policy}-s{s}-l{mask}"


def parse_program(path, meta):
    lines = path.read_text(encoding="utf-8").splitlines()
    head = list(map(int, lines[0].split()))
    n, stalls, mode, depth, mask = head
    if head != [len(meta["task_ids"]), meta["stalls"], meta["mode"], meta["depth"], meta["mask"]]:
        raise ValueError("header/index mismatch")
    priority = list(map(int, lines[1].split()))
    if len(priority) != n or len(lines) != n + 2:
        raise ValueError("program row/priority count mismatch")
    tasks = []
    for i, line in enumerate(lines[2:]):
        row = list(map(int, line.split()))
        if len(row) < 10:
            raise ValueError("short task row")
        ident, kind, ep, bank, write, offset, size, latency, version, nd = row[:10]
        deps = row[10:]
        if ident != i or len(deps) != nd or len(set(deps)) != nd or any(d < 0 or d >= i for d in deps):
            raise ValueError("task id/dependency mismatch")
        if kind not in (0, 1) or ep not in range(3) or bank not in (0, 1) or write not in (0, 1) or latency <= 0:
            raise ValueError("invalid task domain")
        if kind and (offset < 0 or offset % 64 or size <= 0 or offset + size > 65536 or not (mask & (1 << (2 * ep + bank)))):
            raise ValueError("transfer extent/disabled link")
        if kind and not write and not (0 <= version < i and tasks[version]["kind"] == 1 and tasks[version]["write"] == 1):
            raise ValueError("invalid read generation")
        tasks.append(dict(id=i, kind=kind, ep=ep, bank=bank, write=write,
                          offset=offset, size=size, latency=latency, version=version,
                          deps=deps, priority=priority[i], name=meta["task_ids"][i]))
    return tasks


class Audit:
    def __init__(self):
        self.errors = []
        self.counts = Counter()

    def check(self, condition, context, message):
        self.counts["checks"] += 1
        if not condition:
            self.errors.append({"context": context, "message": message})
        return bool(condition)


def audit_summary(audit, meta, tasks, result):
    ctx = meta["name"]
    intervals = result["tasks"]
    audit.check(len(intervals) == len(tasks) and {r[0] for r in intervals} == set(range(len(tasks))), ctx, "task result identities/count")
    by_id = {r[0]: r[1:] for r in intervals}
    if len(by_id) != len(tasks):
        return
    intervals_ep = defaultdict(list)
    compute_ep = defaultdict(list)
    expected_reads = expected_writes = 0
    traffic = Counter()
    for t in tasks:
        start, end = by_id[t["id"]]
        audit.check(isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= result["cycles"], ctx, f"invalid interval {t['name']}")
        for dep in t["deps"]:
            audit.check(by_id[dep][1] <= start, ctx, f"dependency completion after start {dep}->{t['id']}")
            audit.counts["dependency_edges"] += 1
        if t["kind"] == 0:
            audit.check(end - start == t["latency"], ctx, f"compute duration {t['name']}")
            compute_ep[t["ep"]].append((start, end, t["id"]))
            audit.counts["compute_tasks"] += 1
        else:
            beats = (t["size"] + 63) // 64
            expected_writes += beats if t["write"] else 0
            expected_reads += beats if not t["write"] else 0
            traffic["MVD"[t["ep"]]] += t["size"]
            intervals_ep[t["ep"]].append((start, end, t["id"]))
            audit.check(end - start >= t["latency"] + beats + 1, ctx, f"transfer shorter than setup+beats+response {t['name']}")
            audit.counts["transfer_tasks"] += 1
    for label, per_ep in (("compute", compute_ep), ("transfer", intervals_ep)):
        for ep, rows in per_ep.items():
            ordered = sorted(rows)
            for before, after in zip(ordered, ordered[1:]):
                audit.check(before[1] <= after[0], ctx, f"overlapping {label} ep={ep}: {before[2]}/{after[2]}")
    audit.check(max(e for _, e in by_id.values()) == result["cycles"], ctx, "cycles != maximum task completion")
    audit.check(result["requests"] == result["responses"] == expected_reads + expected_writes, ctx, "request/response beat count")
    audit.check(result["read_beats"] == expected_reads and result["write_beats"] == expected_writes, ctx, "read/write beat count")
    audit.check(dict(traffic) == meta["traffic"], ctx, "endpoint byte traffic/index mismatch")
    audit.check(len(result["max_pending"]) == 3 and all(0 <= p <= meta["depth"] for p in result["max_pending"]), ctx, "reported max pending exceeds depth")
    audit.counts["summary_case_checks"] += 1


def audit_trace(audit, path, meta, tasks, result, row):
    ctx = meta["name"]
    audit.check(sha(path) == row["trace_gz_sha256"], ctx, "compressed trace SHA")
    intervals = {ident: (start, end) for ident, start, end in result["tasks"]}
    transfers = defaultdict(list)
    for t in tasks:
        if t["kind"]:
            transfers[t["ep"]].append((intervals[t["id"]][0], intervals[t["id"]][1], t))
    for rows in transfers.values():
        rows.sort(key=lambda r: r[0])
    cursor = [0, 0, 0]
    accepted = Counter()
    received = Counter()
    first_grant = {}
    last_ack = {}
    outstanding = {}
    trace_digest = hashlib.sha256()
    observed_reads = observed_writes = 0
    cycles = 0
    with gzip.open(path, "rb") as src:
        for raw in src:
            trace_digest.update(raw)
            record = json.loads(raw)
            if record.get("type") == "config":
                audit.check([record["mode"], record["depth"], record["mask"]] == [meta["mode"], meta["depth"], meta["mask"]], ctx, "trace hardware config")
                continue
            cycle = record["cycle"]
            audit.check(cycle == cycles, ctx, "trace cycle sequence")
            cycles += 1
            # Consume old responses before adding newly accepted requests. This
            # independently rules out same-edge zero-cycle responses.
            for ep, rsp in enumerate(record["rsp"]):
                if rsp["valid"] and rsp["ready"]:
                    tag = rsp["tag"]
                    known = audit.check(tag in outstanding, ctx, f"unknown ACK tag {tag}")
                    if known:
                        task, grant_cycle = outstanding.pop(tag)
                        audit.check(task["ep"] == ep and bool(task["write"]) == bool(rsp["write"]) and cycle > grant_cycle, ctx, f"ACK endpoint/direction/latency tag {tag}")
                        start, end = intervals[task["id"]]
                        audit.check(start <= cycle < end, ctx, f"ACK outside task interval {task['name']}")
                        received[task["id"]] += 1
                        last_ack[task["id"]] = cycle
            for ep, req in enumerate(record["req"]):
                if not (req["valid"] and req["ready"]):
                    continue
                rows = transfers[ep]
                while cursor[ep] < len(rows) and rows[cursor[ep]][1] <= cycle:
                    cursor[ep] += 1
                valid = cursor[ep] < len(rows) and rows[cursor[ep]][0] <= cycle < rows[cursor[ep]][1]
                if not audit.check(valid, ctx, f"grant outside transfer interval ep={ep} cycle={cycle}"):
                    continue
                start, end, task = rows[cursor[ep]]
                ident = task["id"]
                beat = accepted[ident]
                count = min(64, task["size"] - 64 * beat)
                audit.check(count > 0, ctx, f"excess beat {task['name']}")
                audit.check(cycle >= start + task["latency"], ctx, f"request before task setup {task['name']}")
                audit.check(req["bank"] == task["bank"] and bool(req["write"]) == bool(task["write"]) and req["addr"] == task["offset"] // 64 + beat, ctx, f"grant transfer/address mismatch {task['name']}")
                audit.check(int(req["wstrb_hex"], 16) == (1 << max(0, count)) - 1, ctx, f"byte mask mismatch {task['name']}")
                audit.check(req["generation"] == (ident if task["write"] else task["version"]) and req["generation_offset"] == beat * 64, ctx, f"generation metadata mismatch {task['name']}")
                tag = req["tag"]
                audit.check(tag not in outstanding, ctx, f"duplicate outstanding tag {tag}")
                outstanding[tag] = (task, cycle)
                first_grant.setdefault(ident, cycle)
                accepted[ident] += 1
                observed_reads += not task["write"]
                observed_writes += bool(task["write"])
    audit.check(trace_digest.hexdigest() == row["trace_sha256"], ctx, "uncompressed trace SHA")
    audit.check(not outstanding, ctx, "undrained trace ACKs")
    for t in tasks:
        if not t["kind"]:
            continue
        ident = t["id"]
        beats = (t["size"] + 63) // 64
        audit.check(accepted[ident] == received[ident] == beats, ctx, f"transfer beat/ACK count {t['name']}")
        audit.check(last_ack.get(ident, -2) + 1 == intervals[ident][1], ctx, f"task end is not final ACK+1 {t['name']}")
    audit.check(observed_reads == result["read_beats"] and observed_writes == result["write_beats"] and cycles == result["cycles"] + 1, ctx, "trace aggregate/cycle count")
    audit.counts["traced_cases"] += 1
    audit.counts["trace_cycles"] += cycles
    audit.counts["traced_transfer_tasks"] += sum(t["kind"] for t in tasks)
    return {"name": ctx, "cycles": cycles, "granted_beats": observed_reads + observed_writes,
            "transfers": sum(t["kind"] for t in tasks), "trace_gz_sha256": sha(path)}


def summarize(meta_by_name, results):
    grouped = defaultdict(list)
    for name, row in results.items():
        m = meta_by_name[name]
        grouped[(m["mode"], m["depth"], m["stalls"], m["mask"], m["phase"], placement(m))].append((row["result"]["cycles"], m["policy"], name))
    best = {}
    for k, rows in grouped.items():
        value = min(r[0] for r in rows)
        best[k] = {"cycles": value, "policies": sorted(r[1] for r in rows if r[0] == value),
                   "cases": sorted(r[2] for r in rows if r[0] == value)}
    phase_groups = defaultdict(dict)
    for (*hardware_phase, p), value in best.items():
        phase_groups[tuple(hardware_phase)][p] = value
    phase_report = []
    for (m, d, s, mask, phase), placements in sorted(phase_groups.items()):
        minimum = min(v["cycles"] for v in placements.values())
        p000, p111 = placements.get("000"), placements.get("111")
        phase_report.append({"mode": m, "depth": d, "stalls": s, "mask": mask, "phase": phase,
                             "available_placements": len(placements), "best_of_four_by_placement": placements,
                             "best_cycles": minimum, "best_placements": sorted(p for p, v in placements.items() if v["cycles"] == minimum),
                             "p000_vs_p111": None if p000 is None or p111 is None else
                             {"p000": p000["cycles"], "p111": p111["cycles"],
                              "saved_cycles": p000["cycles"] - p111["cycles"],
                              "fraction_saved": (p000["cycles"] - p111["cycles"]) / p000["cycles"]}})
    static_report = []
    for m, d, s, mask in itertools.product(MODES, DEPTHS, (0, 1), sorted(MASKS)):
        phase_places = [phase_groups[(m, d, s, mask, phase)] for phase in PHASES]
        common = set(phase_places[0]) & set(phase_places[1])
        sums = {p: sum(rows[p]["cycles"] for rows in phase_places) for p in sorted(common)}
        minimum = min(sums.values()) if sums else None
        separate = sum(min(v["cycles"] for v in rows.values()) for rows in phase_places)
        static_report.append({"mode": m, "depth": d, "stalls": s, "mask": mask,
                              "objective": "one prefill32 plus one decode48, unweighted cycle sum; each phase independently selects best of four policies",
                              "available_common_placements": len(common), "cycles_by_placement": sums,
                              "best_sum_cycles": minimum, "best_placements": [p for p, v in sums.items() if v == minimum],
                              "independent_phase_minimum_sum": separate,
                              "shared_placement_regret_cycles": None if minimum is None else minimum - separate})
    return phase_report, static_report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--skip-traces", action="store_true")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    audit = Audit()
    index_path = args.bundle / "programs/index.json"
    index = load(index_path)
    bundle = load(args.bundle / "bundle.json")
    manifest = load(args.run / "manifest.json")
    audit.check(bundle == manifest["source_bundle"], "manifest", "source bundle differs")
    audit.check(bundle["clean_source"] is True and not manifest["development"], "manifest", "not clean formal run")
    audit.check(manifest["failures"] == 0 and all(g["failures"] == 0 for g in manifest["groups"]), "manifest", "reported formal failure")
    audit.check(bundle["source_commit"] == "916dcf9e74ecd6a2164bdbb79991b0f3f7ed1b1e", "manifest", "unexpected formal source commit")
    audit.check(sha(index_path) == manifest["index_sha256"], "manifest", "index SHA")
    for name, expected in bundle["files"].items():
        audit.check(sha(args.bundle / name) == expected, name, "frozen bundle file SHA")
    metas = {c["name"]: c for c in index["cases"]}
    rejected = {c["name"]: c for c in index["rejected"]}
    audit.check(len(metas) == len(index["cases"]) == 1872, "index", "accepted names/count not 1872 unique")
    audit.check(len(rejected) == len(index["rejected"]) == 1584, "index", "rejected names/count not 1584 unique")
    expected_keys = set(itertools.product(MODES, DEPTHS, PHASES, ("".join(map(str, x)) for x in itertools.product((0, 1), repeat=3)), POLICIES, (0, 1), MASKS))
    all_meta = list(metas.values()) + list(rejected.values())
    audit.check({key(m) for m in all_meta} == expected_keys and len(all_meta) == len(expected_keys), "index", "complete 3456-point design domain missing or duplicated")
    programs = {}
    traffic_by_phase = defaultdict(set)
    for name, meta in metas.items():
        audit.check(name == case_name(key(meta)), name, "metadata/name or O,m,l order mismatch")
        path = args.bundle / "programs" / (name + ".case")
        audit.check(sha(path) == meta["sha256"], name, "program SHA")
        try:
            programs[name] = parse_program(path, meta)
        except (ValueError, IndexError) as exc:
            audit.errors.append({"context": name, "message": str(exc)})
            continue
        audit.check(len(set(meta["task_ids"])) == len(meta["task_ids"]), name, "duplicate logical task id")
        audit.check(sum(meta["bank_reserved_bytes"]) <= 131072 and all(v <= 65536 for v in meta["bank_reserved_bytes"]), name, "bank reserved capacity")
        audit.check(all(v <= 65536 for v in meta["scratch_reserved_bytes"].values()), name, "scratch reserved capacity")
        traffic_by_phase[meta["phase"]].add(tuple(sorted(meta["traffic"].items())))
    # Every excluded combination must really request at least one disabled link
    # in its otherwise-identical full-link program; no project graph is invoked.
    excluded_by_mask = Counter()
    for name, meta in rejected.items():
        audit.check(name == case_name(key(meta)), name, "rejected metadata/name mismatch")
        full = programs.get(case_name(key(meta, 63)))
        missing = {"MVD"[t["ep"]] + str(t["bank"]) for t in full if t["kind"] and not (meta["mask"] & (1 << (2 * t["ep"] + t["bank"])))} if full else set()
        audit.check(bool(missing), name, "rejected case has no independently observed missing link")
        excluded_by_mask[meta["mask"]] += 1
    for phase, values in traffic_by_phase.items():
        audit.check(len(values) == 1, phase, "byte traffic varies by fixed-shape hardware/placement/policy")
    results = {}
    stress_records = []
    files = []
    trace_reports = []
    configs = set()
    for folder in sorted(args.run.glob("m*-d*-l*")):
        if not folder.is_dir():
            continue
        result_path = folder / "results.json"
        output = load(result_path)
        config = tuple(output["config"])
        configs.add(config)
        audit.check(folder.name == "m%d-d%d-l%d" % config, folder.name, "folder/config mismatch")
        manifest_group = next((g for g in manifest["groups"] if tuple(g["config"]) == config), None)
        audit.check(manifest_group is not None and sha(result_path) == manifest_group["results_sha256"], folder.name, "result SHA/manifest group")
        if manifest_group:
            audit.check(len(output["cases"]) == manifest_group["cases"] and len(output["stress"]) == manifest_group["stress"], folder.name, "manifest group sample counts")
        command_path = folder / "command.json"
        command = load(command_path)
        audit.check(all(arg in command for arg in ("--assert", "-Wall", "-GPORT_MODE=" + str(config[0]),
                                                  "-GRESP_DEPTH=" + str(config[1]), "-GLINK_MASK=6'd" + str(config[2]))),
                    folder.name, "compile flags/hardware parameters")
        audit.check("%Warning" not in (folder / "build.log").read_text(encoding="utf-8"), folder.name, "Verilator warning in build log")
        files.append({"name": folder.name + "/results.json", "sha256": sha(result_path)})
        files.append({"name": folder.name + "/command.json", "sha256": sha(command_path)})
        files.append({"name": folder.name + "/build.log", "sha256": sha(folder / "build.log")})
        for row in output["cases"]:
            name = row["name"]
            audit.check(name not in results and name in metas, name, "unknown/duplicate result")
            results[name] = row
            if name not in programs:
                continue
            meta = metas[name]
            audit.check((meta["mode"], meta["depth"], meta["mask"]) == config, name, "case/hardware group mismatch")
            if not audit.check(row["exit_code"] == 0 and not row["stderr"], name, "case failed or stderr nonempty"):
                continue
            audit.check(json.loads(row["stdout"]) == row["result"], name, "stdout/result mismatch")
            audit_summary(audit, meta, programs[name], row["result"])
            if "trace_gz_sha256" in row and not args.skip_traces:
                trace_reports.append(audit_trace(audit, folder / (name + ".jsonl.gz"), meta, programs[name], row["result"], row))
        audit.check(len(output["stress"]) == 2 and {r["seed"] for r in output["stress"]} == {2901, 2902}, folder.name, "stress identities")
        for row in output["stress"]:
            audit.check(row["exit_code"] == 0 and not row["stderr"], folder.name, "stress failed or stderr nonempty")
            if "result" in row:
                r = row["result"]
                audit.check(r["requests"] == r["responses"] == r["stress_requests"] + 2048 and r["seed"] == row["seed"], folder.name, "stress initialization/drain count")
                audit.check(all(v <= config[1] for v in r["max_pending"]), folder.name, "stress max credit")
                stress_records.append({"config": config, "seed": row["seed"], **r})
    audit.check(configs == set(itertools.product(MODES, DEPTHS, MASKS)), "results", "27 hardware groups incomplete")
    audit.check(set(results) == set(metas) and len(results) == 1872, "results", "1872 complete unique results")
    audit.check(len(stress_records) == 54, "results", "54 complete stress summaries")
    unused_pairs = []
    for name, meta in metas.items():
        if meta["mask"] == 63 or name not in results:
            continue
        full_name = case_name(key(meta, 63))
        audit.check(programs[name] == programs[full_name], name, "retained-link program changed tasks/priority")
        same = results[name]["result"] == results[full_name]["result"]
        audit.check(same, name, "unused-link removal changes full task times/result summary")
        unused_pairs.append({"restricted": name, "full": full_name, "identical_result": same})
    audit.check(len(unused_pairs) == 720, "results", "retained unused-link pairs count")
    phases, static = summarize(metas, results)
    audit.check(all(r["available_placements"] == 8 for r in phases if r["mask"] == 63), "statistics", "full-link missing one of eight placements")
    audit.check(all(len(v["policies"]) > 0 for r in phases for v in r["best_of_four_by_placement"].values()), "statistics", "empty best4")
    report = {"schema": "issue29-independent-result-audit-v1", "observed_utc": datetime.now(timezone.utc).isoformat(),
              "script_sha256": sha(Path(__file__)), "source_commit": bundle["source_commit"], "source_tree": bundle["source_tree"],
              "index_sha256": sha(index_path), "manifest_sha256": sha(args.run / "manifest.json"),
              "passed": not audit.errors, "counts": dict(audit.counts), "errors": audit.errors,
              "accepted_cases": len(metas), "rejected_cases": len(rejected), "excluded_by_mask": dict(excluded_by_mask),
              "byte_traffic_by_phase": {phase: dict(next(iter(values))) for phase, values in traffic_by_phase.items()},
              "result_files": files, "stress_summaries": stress_records, "traced_case_audits": trace_reports,
              "unused_link_pairs": unused_pairs, "phase_comparisons": phases, "static_joint_placement": static,
              "limits": ["No numerical matrix/vector/softmax computation is implemented in this RTL experiment; arithmetic service times and generation payloads are synthetic.",
                         "All1872 summaries independently check task dependencies, durations, per-engine compute nonoverlap, per-endpoint transfer nonoverlap and byte/beat counts; only recorded traces independently establish detailed ACK-to-task intervals.",
                         "This script does not replace the separate full electrical/data scoreboard trace checker; stress summaries are checked here without replaying payloads.",
                         "Best4 and best placement are finite heuristic selections, not a global scheduling/placement optimum proof.",
                         "Joint placement uses one unweighted prefill32 plus one decode48 occurrence; it is not throughput for any deployment workload mix.",
                         "Every comparison row fixes mode, response depth, response-stall profile and link mask. Different queue depths or port modes consume different hardware resources.",
                         "Behavioral bank RTL, synthetic compute service and cycle counts establish no clock frequency, technology SRAM mapping, area, energy or PPA benefit."]}
    target = args.out / "formal-analysis.json"
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "errors": len(audit.errors), "counts": dict(audit.counts), "report": str(target), "report_sha256": sha(target)}, indent=2), flush=True)
    if audit.errors:
        print(json.dumps(audit.errors[:20], indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
