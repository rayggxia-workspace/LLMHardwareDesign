#!/usr/bin/env python3
"""Resume routing a completed CTS checkpoint in a new job directory."""
import argparse
import json
from pathlib import Path
import shutil

from physical import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("candidate", type=Path)
parser.add_argument("out", type=Path)
parser.add_argument("cpus", type=int, choices=(10, 12))
parser.add_argument("mode", choices=("fast", "cugr"))
parser.add_argument("--hold-target", type=float, default=0.005)
parser.add_argument("--post-hold-repair", action="store_true")
args = parser.parse_args()
src = args.candidate.resolve()
out = args.out.resolve()
out.mkdir()
inputs = json.loads((src / "inputs.json").read_text())
(out / "inputs.json").write_text(json.dumps(inputs | {"cts_checkpoint": str(src), "route_mode": args.mode}))
for lib in src.glob("*.lib"):
    shutil.copyfile(lib, out / lib.name)
config = src / "config.mk"
cts = next((src / "flow/results/nangate45").glob("*/base/4_cts.odb"))
target = out / cts.parent.relative_to(src)
target.mkdir(parents=True)
for name in ("4_cts.odb", "4_cts.sdc", "1_synth_lec.v"):
    shutil.copyfile(cts.with_name(name), target / name)
pre = out / "pre-global-route.tcl"
pre.write_text("""rename pin_access pu_pin_access
proc pin_access {args} {
    pu_pin_access {*}$args -min_access_points 1
}
rename repair_timing_helper pu_grt_repair
proc repair_timing_helper {args} {
    pu_grt_repair {*}$args -max_buffer_percent 60
""" + ("    repair_design -cap_margin 35 -slew_margin 20\n" if args.post_hold_repair else "") + "}\n")
(out / "config.mk").write_text(config.read_text() + f"""
export PRE_GLOBAL_ROUTE_TCL = {pre}
export HOLD_SLACK_MARGIN = {args.hold_target}
export GLOBAL_ROUTE_ARGS = -allow_congestion -congestion_iterations 24
export GLOBAL_ROUTE_USE_CUGR = {int(args.mode == 'cugr')}
""")
command = ["make", "-C", "/OpenROAD-flow-scripts/flow", f"DESIGN_CONFIG={out/'config.mk'}",
           f"WORK_HOME={out/'flow'}", f"NUM_CORES={args.cpus}"]
for stage in ("do-route", "do-finish", "do-gds"):
    run(command + [stage], out / (stage + ".log"))
