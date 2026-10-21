"""Read only new parallel reports and scheduler state; invoked through SSH stdin."""
import datetime
import json
from pathlib import Path
import re
import subprocess
import sys

root = Path(sys.argv[1])
assert root.parent == Path("/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7")
assert re.fullmatch(r"parallel-blocks-[a-z0-9-]+", root.name)
submission = json.loads((root / "submission.json").read_text())
job = str(submission["job_id"])


def command(args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return {"exit_code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def small(path, max_size=2 * 1024 * 1024):
    if not path.is_file():
        return None
    if path.stat().st_size > max_size:
        return {"path": str(path), "size": path.stat().st_size, "read": "omitted: exceeds light-report limit"}
    return path.read_text(errors="replace")


def tail(path):
    if not path.is_file():
        return None
    with path.open("rb") as src:
        src.seek(max(0, path.stat().st_size - 5000))
        return "\n".join(src.read().decode(errors="replace").splitlines()[-12:])


record = {"observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "submission": submission,
          "scheduler": command(["sacct", "-n", "-P", "-j", job,
                                "--format=JobIDRaw,JobName%40,State,ExitCode,Elapsed,AllocCPUS,NodeList"]),
          "allocation": command(["scontrol", "-o", "show", "job", job]),
          "steps": command(["scontrol", "-d", "-o", "show", "step", job]),
          "cases": {}}
for case in submission["cases"]:
    base = root / case
    nickname = "parallel_" + case.replace("-", "_")
    logs = base / "flow/logs/nangate45" / nickname / "base"
    results = base / "flow/results/nangate45" / nickname / "base"
    reports = base / "flow/reports/nangate45" / nickname / "base"
    metrics = {}
    for path in sorted(logs.glob("*.json")):
        text = small(path)
        if isinstance(text, str):
            try:
                metrics[path.name] = json.loads(text)
            except json.JSONDecodeError:
                metrics[path.name] = {"parse_error": "incomplete or invalid JSON", "bytes": path.stat().st_size}
    case_record = {
        "path": str(base), "step": small(base / "slurm-step.txt"),
        "started_utc": small(base / "started-utc.txt"), "finished_utc": small(base / "finished-utc.txt"),
        "pipeline_exit_code": small(base / "exit-code.txt"),
        "output_hash_index": {"exists": (base / "output-files.sha256").is_file(),
                              "path": str(base / "output-files.sha256")},
        "step_log_tail": tail(root / (case + ".step.log")), "metrics": metrics,
        "artifacts": [{"name": p.name, "size": p.stat().st_size} for p in sorted(results.glob("*")) if p.is_file()],
        "route_drc_report": {"exists": (reports / "5_route_drc.rpt").is_file(),
                             "bytes": (reports / "5_route_drc.rpt").stat().st_size if (reports / "5_route_drc.rpt").is_file() else None},
        "stages": {
            "synthesis": (results / "1_synth.odb").is_file() and (logs / "1_synth.json").is_file(),
            "placement": (results / "3_place.odb").is_file() and (logs / "3_5_place_dp.json").is_file(),
            "cts": (results / "4_cts.odb").is_file() and (logs / "4_1_cts.json").is_file(),
            "global_route": (results / "5_1_grt.odb").is_file() and (logs / "5_1_grt.json").is_file(),
            "detailed_route": (results / "5_2_route.odb").is_file() and (logs / "5_2_route.json").is_file(),
            "final_report": (results / "6_final.odb").is_file() and (logs / "6_report.json").is_file()},
        "acceptance": "Requires separate per-stage metric, signal/PG, timing, electrical and model review; no signoff inferred"}
    final_metrics = metrics.get("6_report.json", {})
    case_record["quality_summary"] = {
        "route_drc_errors": metrics.get("5_2_route.json", {}).get("detailedroute__route__drc_errors"),
        "setup_ws_ns": final_metrics.get("finish__timing__setup__ws"),
        "setup_tns_ns": final_metrics.get("finish__timing__setup__tns"),
        "hold_ws_ns": final_metrics.get("finish__timing__hold__ws"),
        "hold_tns_ns": final_metrics.get("finish__timing__hold__tns"),
        "max_cap_violations": final_metrics.get("finish__timing__drv__max_cap"),
        "max_slew_violations": final_metrics.get("finish__timing__drv__max_slew"),
        "max_fanout_violations": final_metrics.get("finish__timing__drv__max_fanout"),
        "die_area_um2": final_metrics.get("finish__design__die__area"),
        "nonfiller_instance_area_um2": final_metrics.get("finish__design__instance__area"),
        "stdcell_area_um2": final_metrics.get("finish__design__instance__area__stdcell"),
        "macro_area_um2": final_metrics.get("finish__design__instance__area__macros"),
        "scope": "Tool single-corner budget checks, no complete boundary load/activity or signoff"}
    final_log = small(logs / "6_report.log")
    if isinstance(final_log, str):
        case_record["final_log_markers"] = [line for line in final_log.splitlines()
                                            if "PSM-0040" in line or "[ERROR" in line or "IR drop" in line]
    else:
        case_record["final_log_markers"] = None
    for name in ("experiment.json", "elaboration-summary.json"):
        text = small(base / name)
        if isinstance(text, str):
            case_record[name] = json.loads(text)
    for name in ("image.sha256", "tools.sha256", "config-inputs.sha256"):
        case_record[name] = small((root if name == "image.sha256" else base) / name)
    record["cases"][case] = case_record

elabs = {name: item.get("elaboration-summary.json", {}) for name, item in record["cases"].items()}
if all(elabs[n] for n in ("opentpu-act", "opentpu-mxu", "opentpu-act-mxu")):
    from collections import Counter
    split = Counter(elabs["opentpu-act"]["blackbox_cells"])
    split.update(elabs["opentpu-mxu"]["blackbox_cells"])
    merged = Counter(elabs["opentpu-act-mxu"]["blackbox_cells"])
    record["memory_resource_comparison"] = {
        "split": dict(split), "merged": dict(merged), "identical_instances_by_model": split == merged,
        "scope": "Actual elaborated blackbox type/count, not physical endpoint/clock/PDN cost or functional equivalence"}
print(json.dumps(record, indent=2))
