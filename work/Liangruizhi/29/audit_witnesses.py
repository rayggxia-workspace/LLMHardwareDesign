"""Independent Issue29 formal-witness binding, replay and real-trace mutations.

All extraction/new files live under the newly created --output directory. The
formal result and project directories are read-only inputs. No simulator runs.
"""
import argparse
import copy
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import subprocess

from trace_checker import audit_trace


SOURCE = "916dcf9e74ecd6a2164bdbb79991b0f3f7ed1b1e"
CHECKER_SHA = "70054bafbf0cb91efb687c1080ce6ca9037fc3f9c79eebcebe4de2a0e907e67b"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=Path, default=Path("D:/Projects/Codex/port-rtl-study-20261022/formal-results01"))
    p.add_argument("--bundle", type=Path, default=Path("D:/Projects/Codex/port-rtl-study-20261022/formal-bundle01"))
    p.add_argument("--repository", type=Path, default=Path("D:/Projects/LLMHardwareDesign-portrtl"))
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    raw_dir, audit_dir, mutation_dir = [args.output / name for name in ("raw", "traces", "mutations")]
    for directory in (raw_dir, audit_dir, mutation_dir):
        directory.mkdir()
    report = {"audit": "Issue29-independent-selected-witness-audit-v1", "source_commit": SOURCE,
              "development": False, "status": "FAIL", "checks": [], "witnesses": [], "mutations": [],
              "scope": "33 selected full-cycle witnesses only (24 programs at depth2/full links/critical/000-or-111 and9 stress at seed2901). 1872 program and54 stress records are hash/count/status-bound, NOT all independently cycle-replayed. No new RTL/model simulation or PPA claim.",
              "audit_script_sha256": sha(__file__), "checker_sha256": sha(Path(__file__).with_name("trace_checker.py"))}

    def check(name, passed, **details):
        report["checks"].append({"name": name, "pass": bool(passed), **details})

    root = args.results / "run-01"
    manifest, start, bundle = read(root / "manifest.json"), read(root / "manifest-start.json"), read(args.results / "bundle.json")
    check("checker.frozen_source", report["checker_sha256"] == CHECKER_SHA)
    check("formal.source", manifest["development"] is False and bundle["clean_source"] is True
          and bundle["source_commit"] == SOURCE and manifest["source_bundle"] == bundle
          and read(args.bundle / "bundle.json") == bundle and manifest["failures"] == 0)
    check("formal.start_end_binding", all(start[key] == manifest[key] for key in start))
    tree = subprocess.check_output(["git", "-C", str(args.repository), "rev-parse", f"{SOURCE}^{{tree}}"], text=True).strip()
    check("formal.source_tree", tree == bundle["source_tree"])
    for relative, expected in bundle["source_files"].items():
        content = subprocess.check_output(["git", "-C", str(args.repository), "show", f"{SOURCE}:{relative}"])
        check("formal.git_blob." + relative, hashlib.sha256(content).hexdigest() == expected, sha256=expected)
    for relative, expected in bundle["files"].items():
        check("formal.bundle_file." + relative, sha(args.bundle / relative) == expected)
    index = read(args.bundle / "programs/index.json")
    check("formal.program_index", sha(args.bundle / "programs/index.json") == manifest["index_sha256"]
          and len(index["cases"]) == 1872 and len(index["rejected"]) == 1584)
    index_by_name = {case["name"]: case for case in index["cases"]}
    check("formal.program_names_unique", len(index_by_name) == len(index["cases"]))
    metadata_files = [root / "manifest.json", root / "manifest-start.json", args.results / "bundle.json", args.bundle / "programs/index.json"]
    expected_groups = set(itertools.product(range(3), (1, 2, 4), (31, 59, 63)))
    check("formal.exact_group_inventory", {tuple(group["config"]) for group in manifest["groups"]} == expected_groups
          and len(manifest["groups"]) == 27)
    record_map = {}
    program_records, stress_records, all_names = 0, 0, set()
    for group in manifest["groups"]:
        mode, depth, mask = group["config"]
        directory = root / f"m{mode}-d{depth}-l{mask}"
        path = directory / "results.json"
        results = read(path)
        metadata_files.extend((path, directory / "command.json", directory / "build.log"))
        check(f"group.{directory.name}.results_binding", sha(path) == group["results_sha256"]
              and results["config"] == group["config"] and group["failures"] == 0
              and len(results["cases"]) == group["cases"] and len(results["stress"]) == group["stress"])
        command = read(directory / "command.json")
        check(f"group.{directory.name}.build_parameters", "--assert" in command
              and f"-GPORT_MODE={mode}" in command and f"-GRESP_DEPTH={depth}" in command
              and f"-GLINK_MASK=6'd{mask}" in command)
        for case in results["cases"]:
            name = case["name"]
            check(f"case.{name}.record", case["exit_code"] == 0 and case["stderr"] == ""
                  and json.loads(case["stdout"]) == case["result"] and name in index_by_name
                  and (index_by_name[name]["mode"], index_by_name[name]["depth"], index_by_name[name]["mask"]) == (mode, depth, mask)
                  and case["result"]["requests"] == case["result"]["responses"])
            program_records += 1
            all_names.add(name)
            record_map[(directory.name, name + ".jsonl.gz")] = ("program", case, results)
        for case in results["stress"]:
            check(f"stress.{directory.name}.{case['seed']}.record", case["exit_code"] == 0
                  and case["stderr"] == "" and json.loads(case["stdout"]) == case["result"]
                  and case["result"]["requests"] == case["result"]["responses"] and case["seed"] in (2901, 2902))
            stress_records += 1
            record_map[(directory.name, f"stress-{case['seed']}.jsonl.gz")] = ("stress", case, results)
    check("formal.all_record_counts", program_records == 1872 and stress_records == 54 and all_names == set(index_by_name))
    traces = sorted(root.glob("m*-d*-l*/*.jsonl.gz"))
    expected_programs = {(f"m{mode}-d2-l63", f"m{mode}-d2-{phase}-p{place}-critical-s{stall}-l63.jsonl.gz")
        for mode, phase, place, stall in itertools.product(range(3), ("prefill32", "decode48"), ("000", "111"), (0, 1))}
    expected_stress = {(f"m{mode}-d{depth}-l63", "stress-2901.jsonl.gz") for mode, depth in itertools.product(range(3), (1, 2, 4))}
    check("witness.exact_selected_inventory", len(traces) == 33
          and {(trace.parent.name, trace.name) for trace in traces} == expected_programs | expected_stress)
    counters = {}
    for trace in traces:
        key = (trace.parent.name, trace.name)
        kind, record, group = record_map[key]
        compressed_hash = sha(trace)
        check("witness.compressed_sha." + "/".join(key), compressed_hash == record["trace_gz_sha256"])
        raw_path = raw_dir / (trace.parent.name + "__" + trace.name[:-3])
        with gzip.open(trace, "rb") as source, raw_path.open("xb") as destination:
            shutil.copyfileobj(source, destination)
        raw_hash = sha(raw_path)
        check("witness.raw_sha." + "/".join(key), raw_hash == record["trace_sha256"])
        if kind == "program":
            case_info = index_by_name[record["name"]]
            program_path = args.bundle / "programs" / (record["name"] + ".case")
            check("witness.program_sha." + record["name"], sha(program_path) == case_info["sha256"])
            # Read the frozen text program directly, without importing its graph
            # builder or C++ source. Full beat transport includes unrequested
            # tail bytes; initialization is mandatory for semantic bytes only.
            program_lines = program_path.read_text(encoding="utf-8").splitlines()
            program_rows = [list(map(int, line.split())) for line in program_lines[2:]]
            semantic_read_bytes = sum(row[6] for row in program_rows if row[1] == 1 and row[4] == 0)
            physical_read_bytes = sum(((row[6] + 63) // 64) * 64 for row in program_rows if row[1] == 1 and row[4] == 0)
            possible_padding_bytes = physical_read_bytes - semantic_read_bytes
        audit = audit_trace(raw_path, require_known_reads=(kind == "stress"), external_min_gap=2 if kind == "program" else 0)
        audit_path = audit_dir / (trace.parent.name + "__" + trace.name[:-3] + ".audit.json")
        save(audit_path, audit)
        data = record["result"]
        config = audit["config"]
        check("witness.config." + "/".join(key), [config["mode"], config["depth"], config["mask"]] == group["config"])
        # Program summary excludes its final evidence-only empty cycle; stress
        # summary includes it. This matches frozen sim.cpp, not inferred latency.
        expected_cycles = data["cycles"] + (1 if kind == "program" else 0)
        check("witness.summary." + "/".join(key), audit["status"] == "PASS"
              and audit["counts"]["cycles"] == expected_cycles
              and audit["counts"]["requests_accepted"] == data["requests"]
              and audit["counts"]["responses_consumed"] == data["responses"]
              and audit["response_queue_peak"] == data["max_pending"])
        if kind == "program":
            check("witness.program_beats." + "/".join(key), audit["counts"]["reads_accepted"] == data["read_beats"]
                  and audit["counts"]["writes_accepted"] == data["write_beats"]
                  and audit["counts"].get("versioned_read_bytes", 0) == semantic_read_bytes
                  and audit["counts"]["read_bytes_known"] + audit["counts"]["read_bytes_unknown"] == physical_read_bytes
                  and audit["counts"]["read_bytes_unknown"] <= possible_padding_bytes,
                  requested_read_bytes=semantic_read_bytes, full_beat_read_bytes=physical_read_bytes,
                  possible_unrequested_padding_bytes=possible_padding_bytes,
                  unverified_padding_bytes=audit["counts"]["read_bytes_unknown"])
        for name, count in audit["counts"].items():
            counters[name] = counters.get(name, 0) + count
        report["witnesses"].append({"kind": kind, "group": trace.parent.name, "name": trace.name,
            "compressed": {"path": str(trace), "bytes": trace.stat().st_size, "sha256": compressed_hash},
            "raw": {"path": str(raw_path), "bytes": raw_path.stat().st_size, "sha256": raw_hash},
            "group_results_sha256": sha(trace.parent / "results.json"),
            "group_binary_sha256_declared": group["binary_sha256"],
            "audit": {"path": str(audit_path), "sha256": sha(audit_path), "status": audit["status"],
                      "counts": audit["counts"], "queue_peak": audit["response_queue_peak"]}})
        print(json.dumps({"witness": "/".join(key), "status": audit["status"]}), flush=True)
    # Mutate ONE recorded field/record in a real formal witness, never regenerate
    # traffic from the RTL or duplicate its arbitration algorithm.
    base = raw_dir / "m0-d2-l63__m0-d2-prefill32-p000-critical-s1-l63.jsonl"
    lines = base.read_text(encoding="utf-8").splitlines(keepends=True)
    rows = [json.loads(line) for line in lines]
    candidates = {}
    occupancy = [0, 0, 0]
    previous_req_stall, previous_rsp_stall = [False] * 3, [False] * 3
    for line_index, row in enumerate(rows[1:], 1):
        for ep, (req, rsp) in enumerate(zip(row["req"], row["rsp"])):
            valid_rsp, rsp_pop = bool(rsp["valid"]), bool(rsp["valid"] and rsp["ready"])
            accepted = req["valid"] and req["ready"]
            if valid_rsp and "tag" not in candidates:
                candidates["tag"] = (line_index, ep)
            if rsp_pop and not rsp["write"] and "data" not in candidates:
                candidates["data"] = (line_index, ep)
            if accepted and not req["write"] and req.get("generation", -1) >= 0 and "version" not in candidates:
                candidates["version"] = (line_index, ep)
            if req["valid"] and not req["ready"] and not req["write"] and occupancy[ep] - rsp_pop >= 2 and "credit" not in candidates:
                candidates["credit"] = (line_index, ep)
            if accepted and "disabledlink" not in candidates:
                candidates["disabledlink"] = (line_index, ep)
            if previous_req_stall[ep] and req["valid"] and "request_stable" not in candidates:
                candidates["request_stable"] = (line_index, ep)
            if previous_rsp_stall[ep] and rsp["valid"] and "response_stable" not in candidates:
                candidates["response_stable"] = (line_index, ep)
            if valid_rsp and "missingresponse" not in candidates:
                candidates["missingresponse"] = (line_index, ep)
            occupancy[ep] += bool(accepted) - rsp_pop
            previous_req_stall[ep] = bool(req["valid"] and not req["ready"])
            previous_rsp_stall[ep] = bool(rsp["valid"] and not rsp["ready"])
    targets = {"tag": "response_type_tag_order", "data": "read_data",
        "version": "graph_read_generation_or_offset", "credit": "response_credit_overflow",
        "disabledlink": "disabled_link_accepted", "request_stable": "request_changed_while_stalled",
        "response_stable": "response_changed_while_stalled", "missingresponse": "response_valid_or_latency"}
    for mutation, target in targets.items():
        line_index, ep = candidates[mutation]
        record_index = 0 if mutation == "disabledlink" else line_index
        changed = copy.deepcopy(rows[record_index])
        if mutation == "tag": changed["rsp"][ep]["tag"] ^= 1
        elif mutation == "data": changed["rsp"][ep]["data_hex"] = f"{int(changed['rsp'][ep]['data_hex'], 16) ^ 1:0128x}"
        elif mutation == "version": changed["req"][ep]["generation"] += 256
        elif mutation == "credit": changed["req"][ep]["ready"] = 1
        elif mutation == "disabledlink": changed["mask"] &= ~(1 << (ep * 2 + rows[line_index]["req"][ep]["bank"]))
        elif mutation == "request_stable": changed["req"][ep]["addr"] ^= 1
        elif mutation == "response_stable": changed["rsp"][ep]["tag"] ^= 1
        elif mutation == "missingresponse": changed["rsp"][ep]["valid"] = 0
        mutant = mutation_dir / (mutation + ".jsonl")
        with mutant.open("x", encoding="utf-8", newline="\n") as stream:
            for index, original in enumerate(lines):
                stream.write(json.dumps(changed, separators=(",", ":")) + "\n" if index == record_index else original)
        outcome = audit_trace(mutant, external_min_gap=2)
        outcome_path = mutation_dir / (mutation + ".audit.json")
        save(outcome_path, outcome)
        detected = outcome["status"] == "FAIL" and any(error["code"] == target for error in outcome["errors"])
        check("mutation.detected." + mutation, detected, targeted_error=target)
        report["mutations"].append({"name": mutation, "base_sha256": sha(base), "changed_line": record_index + 1,
            "cycle": rows[line_index]["cycle"], "endpoint": ep, "targeted_error": target,
            "detected": detected, "mutant_sha256": sha(mutant), "audit_sha256": sha(outcome_path),
            "mutant_path": str(mutant), "audit_path": str(outcome_path)})
    report["metadata_files"] = {str(path): {"bytes": path.stat().st_size, "sha256": sha(path)} for path in metadata_files}
    report["totals"] = {"binding_checks": len(report["checks"]), "binding_failed": sum(not c["pass"] for c in report["checks"]),
        "witnesses": len(report["witnesses"]), "program_witnesses": 24, "stress_witnesses": 9,
        "internally_recorded_programs": program_records, "internally_recorded_stress": stress_records,
        "external_cycle_checks": counters.get("checks", 0), "trace_counts": counters,
        "mutation_controls": len(report["mutations"]), "mutations_detected": sum(m["detected"] for m in report["mutations"])}
    report["status"] = "PASS" if all(c["pass"] for c in report["checks"]) else "FAIL"
    save(args.output / "audit.json", report)
    print(json.dumps({"status": report["status"], "totals": report["totals"]}), flush=True)
    return report["status"] == "PASS"


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
