"""Re-run the frozen A2 RTL bench with accepted START and runtime PM probes."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys


EXTRA_EVENTS = {"START", "MCPM", "LCPM"}
BOUNDARY_CASE = "boundary_reuse_stall"


def replace_once(text, anchor, replacement):
    if text.count(anchor) != 1:
        raise ValueError("frozen A2 bench has an unexpected anchor: " + anchor.strip())
    return text.replace(anchor, replacement, 1)


def instrument(text):
    mc_anchor = "    if(rst_ni) begin\n      if(lc_event && !event_gate)"
    text = replace_once(text, mc_anchor, """    if(rst_ni) begin
      if(start_valid_i && start_ready_o)
        $display("A2 %0d START %0d %0d %0d",cycle,start_job_i,start_epoch_i,start_sequence_i);
      if(pm_req_valid_o && pm_req_ready_i && !pm_req_write_o && trace_pm_owner_o!=0)
        $display("A2 %0d MCPM %0d",cycle,pm_req_address_o);
      if(lc_event && !event_gate)""")
    lc_anchor = "  always @(posedge clk_i) if(rst_ni) begin\n"
    return replace_once(text, lc_anchor, lc_anchor + """    if(pm_req_valid_o && pm_req_ready_i && !pm_req_write_o && trace_pm_owner_o!=0)
      $display("A2 %0d LCPM %0d",cycle_i,pm_req_address_o);
""")


def stock_trace(log):
    # The source runner's numeric and status checks expect only its original events.
    kept = []
    for line in log.splitlines():
        if line.startswith("A2 ") and line.split()[2] in EXTRA_EVENTS:
            continue
        kept.append(line)
    return "\n".join(kept)


def check_probes(log, jobs):
    windows, events = 0, None
    for line in log.splitlines():
        if not line.startswith("A2 "):
            continue
        _, _, kind, *fields = line.split()
        if kind == "START":
            if events is not None or list(map(int, fields)) != [7 + windows, 1, windows + 1]:
                raise ValueError("invalid START identity or overlapping runtime windows")
            events = set()
        elif kind == "RESULT":
            if events != {"MCPM", "LCPM"}:
                raise ValueError("runtime window missing START or accepted PM reads")
            windows += 1
            events = None
        elif events is not None and kind in ("MCPM", "LCPM"):
            address, = map(int, fields)
            if not 0 <= address < 2**14 or address % 16:
                raise ValueError("invalid accepted PM byte address")
            events.add(kind)
    if events is not None or windows != jobs:
        raise ValueError("wrong number of complete START-to-RESULT probe windows")


def load_runner(path):
    spec = importlib.util.spec_from_file_location("issue265_frozen_run_a2", path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    return runner


def run(source, out, verilator):
    source = source.resolve()
    out = out.resolve()
    bench_dir = source / "project" / "control_p_compute_v0_1"
    bench = bench_dir / "tb_p_compute.sv"
    probe = bench_dir / "tb_p_compute_issue265_probe.sv"
    instrumented = instrument(bench.read_text(encoding="utf-8"))
    if out == source or source in out.parents or out in source.parents:
        raise ValueError("source and results must be separate directories")
    out.mkdir(parents=True, exist_ok=False)
    with probe.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(instrumented)
    runner = load_runner(bench_dir / "run_a2.py")
    if runner.SOURCES.count(bench) != 1:
        raise ValueError("frozen A2 runner does not compile exactly one expected bench")
    runner.SOURCES = [probe if path == bench else path for path in runner.SOURCES]
    audit = runner.audit
    runner.audit = lambda log, *args: audit(stock_trace(log), *args)
    previous_argv = sys.argv
    a2_out = out / "a2"
    try:
        sys.argv = [str(runner.__file__), "--out", str(a2_out), "--verilator", verilator]
        runner.main()
    finally:
        sys.argv = previous_argv

    report = json.loads((a2_out / "report.json").read_text(encoding="utf-8"))
    cases = {case["name"]: case for case in report["cases"]}
    for name, jobs in (("single_signed", 1), (BOUNDARY_CASE, 2)):
        check_probes((a2_out / name / "run.log").read_text(encoding="utf-8"), jobs)

    boundary = cases[BOUNDARY_CASE]
    launch = boundary["command"]
    if launch.count("+STALL=2") != 1 or "+RUNS=2" not in launch or boundary["expected_status"] != 0:
        raise ValueError("unexpected archived A2 boundary-case command")
    heldout = ["+STALL=1" if arg == "+STALL=2" else arg for arg in launch]
    heldout_path = out / "heldout.log"
    log = runner.common.run(heldout, a2_out, dict(os.environ), heldout_path)
    if "PASS A2 jobs=2 status=0" not in log:
        raise ValueError("held-out boundary case did not report two successful jobs")
    check_probes(log, 2)
    boundary_dir = a2_out / BOUNDARY_CASE
    seed = (boundary_dir / "seed.bin").read_bytes()
    if len(seed) != 2 * 144:
        raise ValueError("expected two complete frozen A2 S seeds")
    checks = audit(stock_trace(log), [seed[:144], seed[144:]], (1012, 1016, 1023), 1, 0)
    evidence = {
        "stock_bench_sha256": runner.common.sha(bench.read_bytes()),
        "instrumented_bench_sha256": runner.common.sha(probe.read_bytes()),
        "stock_runner_sha256": runner.common.sha(Path(runner.__file__).read_bytes()),
        "heldout_log_sha256": runner.common.sha(heldout_path.read_bytes()),
        "heldout_command": heldout,
        "heldout_checks": checks,
    }
    (out / "probe-report.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print("PASS A2 held-out boundary case", checks, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--verilator", default="verilator")
    args = parser.parse_args()
    try:
        run(args.source, args.out, args.verilator)
    except (AssertionError, OSError, RuntimeError, ValueError) as exc:
        parser.exit(1, "A2 RTL probe failed: {}\n".format(exc))


if __name__ == "__main__":
    main()
