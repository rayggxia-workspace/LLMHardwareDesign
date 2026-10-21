"""One-shot dependent compute audit. Collect negative results without hiding them."""
import datetime
import json
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
observer = Path(__file__).resolve().parent
destination = root / "completion.json"
assert not destination.exists(), "No overwriting a prior completion audit"
result = subprocess.run([sys.executable, str(observer / "remote_status.py"), str(root)],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
if result.returncode:
    raise RuntimeError(result.stderr)
record = json.loads(result.stdout)
record["audit_observed_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
record["audit_scope"] = "One-shot new-artifact checksum verification and existing report review; no new STA/PI/LEC"
failures = 0
for name, case in record["cases"].items():
    case_dir = root / name
    log_path = root / (name + "-checksum-audit.log")
    manifest = case_dir / "output-files.sha256"
    if manifest.is_file():
        with log_path.open("w") as log:
            checked = subprocess.run(["sha256sum", "-c", "output-files.sha256"], cwd=str(case_dir),
                                     stdout=log, stderr=subprocess.STDOUT)
        case["checksum_audit"] = {"status": "pass" if checked.returncode == 0 else "fail",
                                  "exit_code": checked.returncode, "log": str(log_path),
                                  "entries": len(manifest.read_text().splitlines())}
        failures += int(checked.returncode != 0)
    else:
        case["checksum_audit"] = {"status": "missing", "log": None}
        failures += 1
    q = case["quality_summary"]
    markers = case.get("final_log_markers") or []
    gate = {
        "pipeline_exit_zero": (case.get("pipeline_exit_code") or "").strip() == "0",
        "final_report_present": case["stages"]["final_report"],
        "detailed_route_present": case["stages"]["detailed_route"],
        "router_drc_zero": q["route_drc_errors"] == 0,
        "setup_nonnegative": isinstance(q["setup_ws_ns"], (int, float)) and q["setup_ws_ns"] >= 0,
        "hold_nonnegative": isinstance(q["hold_ws_ns"], (int, float)) and q["hold_ws_ns"] >= 0,
        "max_cap_zero": q["max_cap_violations"] == 0,
        "max_slew_zero": q["max_slew_violations"] == 0,
        "max_fanout_zero": q["max_fanout_violations"] == 0,
        "vdd_shapes_connected_reported": any("All shapes on net VDD are connected" in x for x in markers),
        "vss_shapes_connected_reported": any("All shapes on net VSS are connected" in x for x in markers),
        "no_final_report_error_markers": bool(markers) and not any("[ERROR" in x for x in markers)}
    case["observed_tool_budget_gates"] = gate
    case["observed_tool_budget_gates_all_pass"] = all(gate.values())
    case["manufacturing_or_system_signoff"] = False
record["audit_status"] = "complete" if failures == 0 else "artifact_audit_incomplete_or_failed"
record["failed_or_missing_checksum_audits"] = failures
destination.write_text(json.dumps(record, indent=2) + "\n")
print("Audit status: " + record["audit_status"])
for name, case in record["cases"].items():
    print(name + ": checksum=" + case["checksum_audit"]["status"] +
          "; tool budget gates=" + str(case["observed_tool_budget_gates_all_pass"]))
raise SystemExit(bool(failures))
