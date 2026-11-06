#!/usr/bin/env python3
"""Resume routing a completed CTS checkpoint in a new job directory."""
import argparse
import csv
import json
import re
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
parser.add_argument("--via-access-layer", choices=("metal8", "metal9", "metal10"))
parser.add_argument("--hold-endpoints", type=Path)
args = parser.parse_args()
src = args.candidate.resolve()
out = args.out.resolve()
out.mkdir()
inputs = json.loads((src / "inputs.json").read_text())
(out / "inputs.json").write_text(json.dumps(inputs | {"cts_checkpoint": str(src), "route_mode": args.mode, "via_access_layer": args.via_access_layer}))
for lib in src.glob("*.lib"):
    shutil.copyfile(lib, out / lib.name)
config = src / "config.mk"
cts = next((src / "flow/results/nangate45").glob("*/base/4_cts.odb"))
target = out / cts.parent.relative_to(src)
target.mkdir(parents=True)
for name in ("4_cts.odb", "4_cts.sdc", "1_synth_lec.v"):
    shutil.copyfile(cts.with_name(name), target / name)
pre = out / "pre-global-route.tcl"
via_access = f" -via_access_layer {args.via_access_layer}" if args.via_access_layer else ""
old_hook = src / "pre-global-route.tcl"
prelude = "".join(line for line in old_hook.read_text().splitlines(keepends=True) if line.startswith("source "))
if args.hold_endpoints:
    with args.hold_endpoints.open(newline="") as stream:
        endpoints = list(csv.DictReader(stream, delimiter="\t"))
    pads = []
    for row in endpoints:
        pin, slack = row["capture_pin"], float(row["slack_ns"])
        if not re.fullmatch(r"[a-zA-Z0-9_.]+/[a-zA-Z0-9_]+(?:\[\d+\])?", pin) or slack >= .030:
            continue
        stages = 4 if slack < -.015 else 3 if slack < .0 else 2
        pads.append(f"{{{pin}}} {stages}")
    if not pads:
        raise ValueError("the extracted timing report has no actionable hold endpoints")
    prelude += f"set pu_hold_endpoints {{{' '.join(pads)}}}\n"
    prelude += f"source {{{Path(__file__).with_name('hold_endpoints.tcl').resolve()}}}\n"
pre.write_text(prelude + """rename pin_access pu_pin_access
proc pin_access {args} {
    pu_pin_access {*}$args -min_access_points 1""" + via_access + """
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
