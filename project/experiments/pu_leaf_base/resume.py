#!/usr/bin/env python3
"""Resume from an immutable CTS or global-routing checkpoint."""
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
parser.add_argument("--m10-guard", type=float, choices=(0.0, 0.2))
parser.add_argument("--from-global-route", action="store_true")
parser.add_argument("--repair-extracted", type=Path)
parser.add_argument("--setup-target", type=float, default=0.025)
parser.add_argument("--resize-report", type=Path)
parser.add_argument("--route-keepout", type=Path)
parser.add_argument("--isolate-rows", type=Path)
args = parser.parse_args()
if not 0 <= args.setup_target <= 1:
    parser.error("setup optimization target must be between 0 and 1 ns")
if (args.repair_extracted or args.resize_report or args.isolate_rows) and not args.from_global_route:
    parser.error("extracted repair, driver sizing and row isolation require a saved global route")
src = args.candidate.resolve()
out = args.out.resolve()
out.mkdir()
inputs = json.loads((src / "inputs.json").read_text())
(out / "inputs.json").write_text(json.dumps(inputs | {"route_checkpoint": str(src), "from_global_route": args.from_global_route,
    "route_mode": args.mode, "via_access_layer": args.via_access_layer,
    "m10_guard_um": args.m10_guard, "hold_endpoints": str(args.hold_endpoints or ""),
    "repair_extracted": str(args.repair_extracted or ""), "setup_target_ns": args.setup_target,
    "resize_report": str(args.resize_report or ""),
    "route_keepout": str(args.route_keepout or ""), "isolate_rows": str(args.isolate_rows or "")}))
for lib in src.glob("*.lib"):
    shutil.copyfile(lib, out / lib.name)
config = src / "config.mk"
checkpoint = "5_1_grt.odb" if args.from_global_route else "4_cts.odb"
cts = next((src / "flow/results/nangate45").glob("*/base/" + checkpoint))
target = out / cts.parent.relative_to(src)
target.mkdir(parents=True)
names = ("5_1_grt.sdc", "1_synth_lec.v") if args.from_global_route else (
    "4_cts.odb", "4_cts.sdc", "1_synth_lec.v")
for name in names:
    shutil.copyfile(cts.with_name(name), target / name)
pre = out / "pre-global-route.tcl"
via_access = f" -via_access_layer {args.via_access_layer}" if args.via_access_layer else ""
old_hook = src / "pre-global-route.tcl"
prelude = "" if args.from_global_route else "".join(
    line for line in old_hook.read_text().splitlines(keepends=True) if line.startswith("source "))
hold_setup = ""
if args.hold_endpoints:
    with args.hold_endpoints.open(newline="") as stream:
        endpoints = list(csv.DictReader(stream, delimiter="\t"))
    pads = []
    for row in endpoints:
        pin, slack = row["capture_pin"], float(row["slack_ns"])
        threshold = .010 if args.from_global_route else .030
        if not re.fullmatch(r"[a-zA-Z0-9_.]+/[a-zA-Z0-9_]+(?:\[\d+\])?", pin) or slack >= threshold:
            continue
        stages = 4 if slack < -.015 else 3 if slack < .0 else 2
        if args.from_global_route:
            stages += 1
        pads.append(f"{{{pin}}} {stages}")
    if not pads:
        raise ValueError("the extracted timing report has no actionable hold endpoints")
    hold_setup += f"set pu_hold_endpoints {{{' '.join(pads)}}}\n"
    hold_setup += f"source {{{Path(__file__).with_name('hold_endpoints.tcl').resolve()}}}\n"
route_guard = ""
if args.m10_guard is not None:
    route_guard += f"set pu_m10_guard_um {args.m10_guard}\n"
    route_guard += f"source {{{Path(__file__).with_name('guard_m10.tcl').resolve()}}}\n"
if args.route_keepout:
    for line in args.route_keepout.read_text().splitlines():
        if not re.fullmatch(r"(?:via[79]|metal9|metal10)(?:[ \t]+[0-9]+){4}", line):
            raise ValueError(f"invalid observed routing keepout: {line}")
        layer, x0, y0, x1, y1 = line.split()
        if not (int(x0) < int(x1) and int(y0) < int(y1)):
            raise ValueError(f"empty observed routing keepout: {line}")
        route_guard += (
            f"set pu_keepout_layer [[ord::get_db_tech] findLayer {layer}]\n"
            f"set pu_keepout_shadow [odb::dbObstruction_create [ord::get_db_block] $pu_keepout_layer {x0} {y0} {x1} {y1}]\n"
            "odb::dbBoolProperty_create $pu_keepout_shadow pu_m10_route_shadow 1\n"
        )
pre.write_text(prelude + hold_setup + route_guard + """rename pin_access pu_pin_access
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
if args.from_global_route:
    platform = Path("/OpenROAD-flow-scripts/flow/platforms/nangate45")
    script = out / "eco-from-global-route.tcl"
    extracted = ""
    repair = ""
    if args.repair_extracted:
        extracted = (
            f"source {{{platform/'setRC.tcl'}}}\n"
            f"read_spef {{{args.repair_extracted.resolve()}}}\n"
            "set_propagated_clock [all_clocks]\n"
        )
        repair = (
            "repair_design -cap_margin 5 -slew_margin 10\n"
            f"repair_timing -setup -setup_margin {args.setup_target} -max_buffer_percent 10\n"
            "detailed_placement\ncheck_placement -verbose\n"
        )
    if args.resize_report:
        report = args.resize_report.read_text().split("=== ELECTRICAL VIOLATIONS ===")[1].split(
            "=== CONSTRAINT AUDIT ===")[0]
        pins = re.findall(
            r"(?m)^([a-zA-Z0-9_.]+/[a-zA-Z0-9_]+(?:\[\d+\])?)\s+[-.\d]+\s+"
            r"[-.\d]+\s+[-.\d]+\s+\(VIOLATED\)", report
        )
        if not pins:
            raise ValueError("no actionable electrical pins")
        pin_list = " ".join(f"{{{pin}}}" for pin in dict.fromkeys(pins))
        repair += (
            f"set pu_resize_pins {{{pin_list}}}\n"
            f"source {{{Path(__file__).with_name('resize_drivers.tcl').resolve()}}}\n"
        )
    if args.isolate_rows:
        rows = args.isolate_rows.read_text().splitlines()
        if not rows or not all(re.fullmatch(r"ROW_[0-9_]+(?: [0-9]+ [0-9]+)*", row) for row in rows):
            raise ValueError("invalid placed rows for well isolation")
        repair += (
            f"set pu_placed_rows {{{' '.join('{' + row + '}' for row in rows)}}}\n"
            f"source {{{Path(__file__).with_name('isolate_placed_rows.tcl').resolve()}}}\n"
        )
    script.write_text(
        f"read_liberty {{{platform/'lib/NangateOpenCellLibrary_typical.lib'}}}\n"
        + "".join(f"read_liberty {{{p}}}\n" for p in sorted(out.glob("*.lib")))
        + f"read_db {{{cts.with_name('5_1_grt.odb')}}}\n"
        + f"read_sdc {{{target/'5_1_grt.sdc'}}}\n"
        + f"set ::env(RESULTS_DIR) {{{target}}}\n"
        + "set_routing_layers -signal metal2-metal10 -clock metal4-metal10\n"
        + route_guard
        + extracted
        + "global_route -start_incremental\n"
        + repair
        + "proc detailed_placement_helper {} { detailed_placement }\n"
        + hold_setup
        + "global_route -end_incremental -allow_congestion\n"
        + f"write_db {{{target/'5_1_grt.odb'}}}\n"
    )
    run(["openroad", "-no_init", "-threads", str(args.cpus), "-exit", str(script)],
        out / "eco-from-global-route.log")
    run(command + ["do-5_2_route", "do-5_3_fillcell", "do-5_route", "do-5_route.sdc"],
        out / "do-route.log")
else:
    run(command + ["do-route"], out / "do-route.log")
# The PG shadows constrain only routing. PSM and GDS audit use the actual
# routed signals, actual PG conductors, and original permanent obstructions.
if args.m10_guard or args.route_keepout or args.from_global_route:
    final_route = target / "5_route.odb"
    cleanup = out / "clear-m10-route-shadows.tcl"
    cleanup.write_text(
        f"read_db {{{final_route}}}\n"
        "set count 0\n"
        "foreach shadow [[ord::get_db_block] getObstructions] {\n"
        "    if {[odb::dbBoolProperty_find $shadow pu_m10_route_shadow] eq \"NULL\"} {continue}\n"
        "    odb::dbObstruction_destroy $shadow\n"
        "    incr count\n"
        "}\n"
        + ('if {$count == 0} {error "temporary M10 route shadows were lost"}\n' if args.m10_guard or args.route_keepout else "")
        + 'puts "Removed $count temporary route shadows, without modifying conductors"\n'
        f"write_db {{{final_route}}}\n"
    )
    run(["openroad", "-no_init", "-exit", str(cleanup)], out / "clear-m10-route-shadows.log")
for stage in ("do-finish", "do-gds"):
    run(command + [stage], out / (stage + ".log"))
