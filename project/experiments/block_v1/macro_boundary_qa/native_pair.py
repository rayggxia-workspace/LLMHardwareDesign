"""Run/receive two fresh native STA processes with the same sealed SDC.

Aggregate boundary observations and complete native endpoint inventories are
kept separately: macro collapse changes endpoint identities. This diagnostic
does not claim all arcs, exceptions, corners or electrical limits equivalent.
"""
import argparse
import concurrent.futures
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from audit import Invalid, file_sha, load_json, number, require
from spef_inventory import inventory


def rows(path):
    return [line.split("\t") for line in Path(path).read_text(encoding="utf-8").splitlines()]


def scalar(value, finite=True):
    number_value = float(value)
    require(not math.isnan(number_value), "native NaN")
    if finite:
        require(math.isfinite(number_value) and abs(number_value) < 1e30, "native nonfinite/sentinel")
    return number_value


def receive(folder, expected_ports):
    folder = Path(folder)
    ports = {}
    for row in rows(folder / "ports.tsv"):
        require(len(row) == 6 and row[0] not in ports, "duplicate/malformed native port")
        name, direction, *slew = row
        require(expected_ports.get(name) == direction, "native port identity/direction")
        ports[name] = {"direction": direction, "slew_ns": [scalar(x) for x in slew]}
    require(set(ports) == set(expected_ports), "missing/extra native ports")
    endpoints = {}
    for row in rows(folder / "endpoints.tsv"):
        require(len(row) == 7 and row[0] not in endpoints, "duplicate/malformed native endpoint")
        name, is_port, direction, *slacks = row
        require(is_port in ("0", "1") and direction in ("input", "output"), "native endpoint kind")
        values = [scalar(x, finite=False) for x in slacks]
        # Keep nonfinite endpoints visible, never silently count them as passing.
        endpoints[name] = {"is_port": is_port == "1", "direction": direction,
                           "slacks_ns": [x if math.isfinite(x) and abs(x) < 1e30 else None for x in values]}
    summary, electrical, clocks = {}, {}, {}
    for row in rows(folder / "summary.tsv"):
        key, *values = row
        if key in ("capacitance", "slew", "fanout"):
            require(len(values) == 3 and key not in electrical, "electrical summary")
            count, slack, limit = values
            require(count.isdigit(), "electrical count")
            parsed_slack, parsed_limit = scalar(slack, False), scalar(limit, False)
            electrical[key] = {"violations": int(count),
                               "slack_native": parsed_slack if math.isfinite(parsed_slack) else None,
                               "limit_native": parsed_limit if math.isfinite(parsed_limit) else None,
                               "has_limit": math.isfinite(parsed_limit) and 0 < parsed_limit < 1e30}
        elif key == "clock":
            require(len(values) == 3 and values[0] not in clocks, "clock summary")
            clocks[values[0]] = {"propagated": values[1] == "1", "period_ns": scalar(values[2])}
        else:
            require(len(values) == 1 and key not in summary, "duplicate/malformed native summary")
            summary[key] = scalar(values[0])
    require(set(summary) == {"time_unit_seconds", "capacitance_unit_farads", "check_setup",
                            "setup_violations", "hold_violations", "endpoint_count", "observation_count"}, "native summary coverage")
    # The native unit API returns a single-precision seconds scale (e.g.
    # 9.999999717e-10 for ns). This tolerance identifies units only; timing
    # observations/tolerances below remain unrounded native values.
    require(abs(summary["time_unit_seconds"]/1e-9 - 1) < 1e-6, "native time units must be ns")
    require(summary["capacitance_unit_farads"] > 0, "native capacitance units")
    require(summary["endpoint_count"] == len(endpoints) and endpoints, "native endpoint count/coverage")
    require(set(electrical) == {"capacitance", "slew", "fanout"} and clocks, "native electrical/clock coverage")
    expected_observations = {(direction, name, edge, analysis)
                             for name, direction in expected_ports.items() if name != "clk"
                             for edge in ("rise", "fall") for analysis in ("max", "min")}
    observations = {}
    for row in rows(folder / "observations.tsv"):
        require(len(row) == 9, "native observation arity")
        direction, name, edge, analysis, start, end, slack, arrival, required = row
        key = (direction, name, edge, analysis)
        require(key in expected_observations and key not in observations, "native observation identity")
        require(start != "NO_PATH", f"native boundary path missing: {key}")
        require(end in endpoints, "observation endpoint not in native inventory")
        observations[key] = {"startpoint": start, "endpoint": end, "slack_ns": scalar(slack),
                             "arrival_ns": scalar(arrival), "required_ns": scalar(required)}
    require(set(observations) == expected_observations
            and summary["observation_count"] == len(observations), "native boundary coverage/count")
    return {"schema": "block-v1-native-boundary-observations/1", "ports": ports,
            "endpoints": endpoints, "summary": summary, "electrical": electrical, "clocks": clocks,
            "observations": [{"key": list(key), **value} for key, value in sorted(observations.items())],
            "all_native_endpoint_slacks_finite": all(x is not None for v in endpoints.values() for x in v["slacks_ns"]),
            "scope": "Complete endpoint inventory and worst-per-input/output-edge diagnostic; no full arc equivalence"}


def compare_native(flat, abstract, time_tolerance_ns, slew_tolerance_ns):
    require(number(time_tolerance_ns) >= 0 and number(slew_tolerance_ns) >= 0, "native comparison tolerances")
    require(flat["clocks"] == abstract["clocks"], "different native clocks")
    require(flat["ports"].keys() == abstract["ports"].keys(), "different native ports")
    require(flat["summary"]["time_unit_seconds"] == abstract["summary"]["time_unit_seconds"]
            and flat["summary"]["capacitance_unit_farads"] == abstract["summary"]["capacitance_unit_farads"], "different native units")
    by_key = [{tuple(row["key"]): row for row in report["observations"]} for report in (flat, abstract)]
    require(by_key[0].keys() == by_key[1].keys(), "different native observation coverage")
    mismatches, differences = [], []
    for key, a in by_key[0].items():
        b = by_key[1][key]
        # Arrival/required absolute origins legitimately change with macro
        # collapse; preserve them as evidence but compare boundary slack.
        delta = abs(a["slack_ns"] - b["slack_ns"])
        differences.append({"key": list(key), "slack_absolute_difference_ns": delta})
        if delta > time_tolerance_ns:
            mismatches.append({"key": list(key), "metric": "slack_ns", "difference": delta, "limit": time_tolerance_ns})
    for name, a in flat["ports"].items():
        b = abstract["ports"][name]
        require(a["direction"] == b["direction"], "native port direction difference")
        for index, (x, y) in enumerate(zip(a["slew_ns"], b["slew_ns"])):
            delta = abs(x-y)
            if delta > slew_tolerance_ns:
                mismatches.append({"port": name, "metric": f"slew_{index}", "difference": delta, "limit": slew_tolerance_ns})
    return {"passed": not mismatches, "mismatches": mismatches, "differences": differences,
            "flat_abstract_boundary_qualified": False,
            "scope": "Native aggregate slack/port-slew comparison only; endpoint sets retained separately, full arc/electrical/RC equivalence still required"}


def signed_slack_diagnostic(flat, abstract, threshold_ns):
    """Report optimism separately from pessimism; no new acceptance policy."""
    require(number(threshold_ns) >= 0, "signed diagnostic threshold")
    by_key = [{tuple(row["key"]): row for row in v["observations"]} for v in (flat, abstract)]
    require(by_key[0].keys() == by_key[1].keys() and by_key[0], "signed diagnostic observation coverage")
    require(all(len(mapping) == len(v["observations"]) for mapping, v in zip(by_key, (flat, abstract))), "signed diagnostic duplicate observation")
    differences = [{"key": list(k), "abstract_minus_flat_slack_ns": scalar(by_key[1][k]["slack_ns"])-scalar(row["slack_ns"])}
                   for k, row in by_key[0].items()]
    return {"threshold_ns": threshold_ns,
            "optimistic_count": sum(d["abstract_minus_flat_slack_ns"] > threshold_ns for d in differences),
            "pessimistic_count": sum(d["abstract_minus_flat_slack_ns"] < -threshold_ns for d in differences),
            "worst_optimistic": max(differences, key=lambda d: d["abstract_minus_flat_slack_ns"]),
            "worst_pessimistic": min(differences, key=lambda d: d["abstract_minus_flat_slack_ns"]),
            "qualified_hard_macro": False, "scope": "Diagnostic direction only; source/context and acceptance policy must be reviewed separately"}


def tcl_list(paths):
    values = []
    for path in paths:
        text = str(path)
        require(not any(c in text for c in "{}\\\n\r"), "unsupported Tcl path characters")
        values.append("{" + text + "}")
    return " ".join(values)


def native_log_diagnostics(path):
    counts, examples = {}, []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        match = re.match(r"(Error|Warning)\s+(\d+):", line)
        if match:
            key = f"{match[1]} {match[2]}"
            counts[key] = counts.get(key, 0)+1
            if len(examples) < 10:
                examples.append(line)
    # OpenSTA can print read errors without a nonzero process status.
    missing_parasitic_bindings = sum(counts.get(f"Warning {code}", 0) for code in (1648, 1650))
    return {"message_counts": counts, "examples": examples,
            "native_error_count": sum(n for key, n in counts.items() if key.startswith("Error ")),
            "missing_spef_instance_or_net_messages": missing_parasitic_bindings,
            "exact_source_annotation_binding_accepted": missing_parasitic_bindings == 0,
            "scope": "Native log diagnostics; zero missing-name messages does not prove full active-net annotation"}


def run(request_path, output, executable, parallel=1):
    request_path, output = Path(request_path).resolve(), Path(output).resolve()
    request_bytes = request_path.read_bytes()
    request = load_json(request_bytes)
    require(request["schema"] == "block-v1-native-boundary-request/1", "native request schema")
    require(parallel in (1, 2), "native process parallelism")
    require(request["abstract_parent_interconnect"] in ("ideal", "explicit-spef"), "parent interconnect declaration")
    require(request["evidence_kind"] in ("native-control", "native-candidate-diagnostic"), "native evidence kind")
    for tolerance in ("time_tolerance_ns", "slew_tolerance_ns"):
        require(number(request[tolerance]) >= 0, "native tolerance")
    expected_ports = request["expected_ports"]
    require(expected_ports.get("clk") == "input" and len(expected_ports) > 1
            and all(d in ("input", "output") for d in expected_ports.values()), "native expected ports")
    roles = request["files"]
    require({"flat_verilog", "flat_spef", "sdc", "abstract_verilog", "macro_lib"} <= roles.keys(), "native required files")
    require(any(role.startswith("base_lib_") for role in roles), "native base Liberty required")
    require(("abstract_spef" in roles) == (request["abstract_parent_interconnect"] == "explicit-spef"),
            "abstract parent SPEF/declaration mismatch")
    paths = {}
    for role, entry in roles.items():
        path = (request_path.parent / entry["path"]).resolve()
        require(file_sha(path) == entry["sha256"], f"native input hash: {role}")
        require(not output.is_relative_to(path.parent), "output inside input directory")
        paths[role] = path
    executable = Path(executable).resolve()
    require(executable.is_file(), "native executable missing")
    script = Path(__file__).with_name("measure_native.tcl").resolve()
    sealed = {"request": file_sha(request_path), "executable": file_sha(executable),
              "collector": file_sha(script), "runner": file_sha(Path(__file__)),
              "spef_inventory": file_sha(Path(__file__).with_name("spef_inventory.py")),
              **{role: file_sha(path) for role, path in paths.items()}}
    source_rc = inventory(paths["flat_spef"], retain_all=False)
    require(source_rc["ports"] == {n: "I" if d == "input" else "O" for n, d in expected_ports.items()}, "SPEF/native expected port identity")
    candidate_binding = None
    if request["evidence_kind"] == "native-candidate-diagnostic":
        from candidate_request import validate_binding
        candidate_binding = validate_binding(request, paths)
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"schema": "block-v1-native-boundary-receipt/1", "passed": False,
               "started": time.time(), "request_path": str(request_path), "inputs": sealed,
               "input_paths": {role: str(path) for role, path in paths.items()},
               "executable": str(executable), "process_parallelism": parallel,
               "threads_per_process": 1, "commands": [], "outputs": {}}
    try:
        provenance = output / "provenance"
        provenance.mkdir()
        for name in ("native_pair.py", "measure_native.tcl", "spef_inventory.py", "audit.py", "candidate_request.py"):
            source = Path(__file__).with_name(name)
            (provenance / name).write_bytes(source.read_bytes())
        (output / "source-rc-inventory.json").write_text(json.dumps(source_rc, indent=2, allow_nan=False)+"\n", encoding="utf-8")

        def one(view):
            folder = output / view
            folder.mkdir()
            libraries = [paths[r] for r in sorted(paths) if r.startswith("base_lib_")]
            if view == "abstract":
                libraries.append(paths["macro_lib"])
            env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       BV1QA_LIBS=tcl_list(libraries), BV1QA_VERILOG=str(paths[view+"_verilog"]),
                       BV1QA_TOP=request[view+"_top"], BV1QA_SDC=str(paths["sdc"]),
                       BV1QA_SPEF=str(paths["flat_spef"]) if view == "flat" else str(paths.get("abstract_spef", "")))
            argv = [str(executable), "-no_init", "-exit", str(script)]
            record = {"view": view, "argv": argv, "cwd": str(folder),
                      "environment": {k: env[k] for k in ("OMP_NUM_THREADS", "BV1QA_LIBS", "BV1QA_VERILOG", "BV1QA_TOP", "BV1QA_SDC", "BV1QA_SPEF")}}
            with (folder / "native.log").open("w", encoding="utf-8") as log:
                record["returncode"] = subprocess.run(argv, cwd=folder, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
            receipt["commands"].append(record)
            require(record["returncode"] == 0, f"native {view} process failed; inspect preserved native.log")
            observed = receive(folder, expected_ports)
            (folder / "observed.json").write_text(json.dumps(observed, indent=2, allow_nan=False)+"\n", encoding="utf-8")
            return observed

        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as pool:
            futures = [pool.submit(one, view) for view in ("flat", "abstract")]
            reports = [future.result() for future in futures]
        require(all(file_sha(path) == sealed[role] for role, path in paths.items())
                and file_sha(request_path) == sealed["request"] and file_sha(executable) == sealed["executable"]
                and file_sha(script) == sealed["collector"], "native input/tool changed during run")
        require(all(p.read_bytes() == Path(__file__).with_name(p.name).read_bytes() for p in provenance.iterdir()),
                "native code changed during run")
        result = compare_native(*reports, request["time_tolerance_ns"], request["slew_tolerance_ns"])
        result.update(schema="block-v1-native-boundary-pair/1", evidence_kind=request["evidence_kind"],
                      native_measurement_completed=True, source_spef_sha256=sealed["flat_spef"],
                      request_sha256=sealed["request"], source_input_inventory_sha256=file_sha(output / "source-rc-inventory.json"),
                      qualified_hard_macro=False)
        result["native_log_diagnostics"] = {view: native_log_diagnostics(output / view / "native.log") for view in ("flat", "abstract")}
        result["measurement_context_accepted"] = all(d["native_error_count"] == 0 and d["exact_source_annotation_binding_accepted"]
                                                      for d in result["native_log_diagnostics"].values())
        result["candidate_source_binding"] = candidate_binding
        result["passed"] = result["passed"] and result["measurement_context_accepted"]
        (output / "native-pair-report.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
        # Receipt means the diagnostic actually ran, not that both models matched.
        receipt["passed"] = True
        return result
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        receipt["finished"] = time.time()
        receipt["outputs"] = {p.relative_to(output).as_posix(): file_sha(p)
                              for p in output.rglob("*") if p.is_file() and p != output / "receipt.json"}
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def verify(folder, request_path):
    """Recompute from bound native TSV and actual source SPEF, not result claims."""
    folder, request_path = Path(folder), Path(request_path).resolve()
    receipt = load_json((folder / "receipt.json").read_bytes())
    require(receipt["schema"] == "block-v1-native-boundary-receipt/1"
            and receipt["passed"] is True, "native receipt failed")
    request = load_json(request_path.read_bytes())
    require(file_sha(request_path) == receipt["inputs"]["request"], "native request receipt binding")
    for role, entry in request["files"].items():
        path = (request_path.parent / entry["path"]).resolve()
        require(str(path) == receipt["input_paths"][role]
                and file_sha(path) == entry["sha256"] == receipt["inputs"][role], "native input receipt binding")
    require({record["view"] for record in receipt["commands"]} == {"flat", "abstract"}
            and len(receipt["commands"]) == 2
            and all(record["returncode"] == 0 for record in receipt["commands"]), "native command coverage")
    outputs = receipt["outputs"]
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*")
              if p.is_file() and p != folder / "receipt.json"}
    require(actual == outputs.keys(), "native output inventory changed")
    for name, digest in outputs.items():
        path = (folder / name).resolve()
        require(path.is_relative_to(folder.resolve()) and file_sha(path) == digest, "native output receipt binding")
    for filename, key in (("native_pair.py", "runner"), ("measure_native.tcl", "collector"), ("spef_inventory.py", "spef_inventory")):
        require(file_sha(folder / "provenance" / filename) == receipt["inputs"][key], "native executed code binding")
    require(file_sha(Path(receipt["executable"])) == receipt["inputs"]["executable"], "native executable binding")
    computed_rc = inventory(Path(receipt["input_paths"]["flat_spef"]), retain_all=False)
    require(computed_rc == load_json((folder / "source-rc-inventory.json").read_bytes()), "native source RC derivation mismatch")
    observed = [receive(folder / view, request["expected_ports"]) for view in ("flat", "abstract")]
    for view, result in zip(("flat", "abstract"), observed):
        require(result == load_json((folder / view / "observed.json").read_bytes()), "native observed JSON disagrees with TSV")
    computed = compare_native(*observed, request["time_tolerance_ns"], request["slew_tolerance_ns"])
    saved = load_json((folder / "native-pair-report.json").read_bytes())
    diagnostics = {view: native_log_diagnostics(folder / view / "native.log") for view in ("flat", "abstract")}
    accepted = all(d["native_error_count"] == 0 and d["exact_source_annotation_binding_accepted"] for d in diagnostics.values())
    computed["passed"] = computed["passed"] and accepted
    require(saved["native_log_diagnostics"] == diagnostics and saved["measurement_context_accepted"] == accepted, "native log diagnostics derivation")
    if request["evidence_kind"] == "native-candidate-diagnostic":
        from candidate_request import validate_binding
        paths = {role: Path(receipt["input_paths"][role]) for role in request["files"]}
        require(validate_binding(request, paths) == saved["candidate_source_binding"], "native candidate source derivation")
    require(all(saved[key] == value for key, value in computed.items()), "native saved comparison disagrees with measurements")
    return {"passed": True, "native_measurement_binding_passed": True,
            "models_match_within_declared_diagnostic_tolerances": computed["passed"],
            "receipt_sha256": file_sha(folder / "receipt.json"), "source_rc_derived_from_spef": True,
            "flat_abstract_boundary_qualified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--parallel", type=int, default=1)
    args = parser.parse_args()
    try:
        result = run(args.request, args.output, args.executable, args.parallel)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result["passed"] else 2
    except (Invalid, ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps({"passed": False, "qualified_hard_macro": False, "error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
