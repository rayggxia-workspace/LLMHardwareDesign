#!/usr/bin/env python3
"""Independent-leaf P/U placement coupons on the original native metal stack."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess

from controlled import stage as stage_controller


def run(command, log):
    with log.open("w") as output:
        subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, check=True)


def digest(file):
    result = hashlib.sha256()
    with file.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            result.update(block)
    return result.hexdigest()


def prepare_leaves(base, out, group):
    pu = base / "issue-187-p16-j16/005-leaf-views"
    ge = base / "issue-201-compact-ge/2ba89c0bd/release"
    s = base / "issue-200-compact-local-s"
    n_source = (
        base.parent / "llm_routing_analysis/worktrees"
        / "issue143-seven-block-v2-20261030/outputs/029/bundle-n/block-v2-n-native.tar.gz"
    )
    s_p = s / "run10-delay1/results/4/flow/results/nangate45/local_s_p/base"
    s_base = s / "run08-base0/results/0/flow/results/nangate45/local_s_base/base"
    if group == "P":
        return {
            "store": (s / "final-gates/p-audit/local_s_p.lef", s / "final-gates/p-audit/local_s_p.lib", s_p / "6_final.gds"),
            "multiply": (pu / "views/M/leaf.lef", pu / "views/M/leaf.lib", pu / "inputs/M/6_final.gds"),
            "gate": (ge / "g/block_v2_g.lef", ge / "g/block_v2_g.lib", ge / "g/6_final.gds"),
        }
    expected = "81077733877a58d0fa80ebc40951fc229b70e94666d04c50a5387a2ae8e7457c"
    if digest(n_source) != expected:
        raise ValueError("qualified N source digest mismatch")
    n = out / "n"
    n.mkdir()
    run(["tar", "-xzf", str(n_source), "-C", str(n), "native", "geometry/candidate.lef"], out / "n-unpack.log")
    std = "/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib"
    native = n / "native"
    tcl = n / "model.tcl"
    tcl.write_text(
        f"read_liberty {{{std}}}\nread_db {{{native / '6_final.odb'}}}\n"
        f"read_sdc {{{native / '6_final.sdc'}}}\nread_spef {{{native / '6_final.spef'}}}\n"
        f"set_propagated_clock [all_clocks]\nset_clock_latency -source 0 [all_clocks]\n"
        f"write_timing_model {{{n / 'n.lib'}}}\n"
        f"write_abstract_lef -bloat_factor 0 {{{n / 'n.lef'}}}\n"
    )
    run(["openroad", "-no_init", "-exit", str(tcl)], out / "n-model.log")
    return {
        "store": (s / "audit08/base0/local_s_base.lef", s / "audit08/base0/local_s_base.lib", s_base / "6_final.gds"),
        "normalize": (n / "n.lef", n / "n.lib", native / "6_final.gds"),
        "elementwise": (ge / "e_compact/block_v2_e_compact.lef", ge / "e_compact/block_v2_e_compact.lib", ge / "e_compact/6_final.gds"),
    }


def route_abstract(source_lef, odb, out, name, same_net, access_layers=None, compact_obs=False, guard_cuts=False):
    """Retain actual upper obstructions for legal parent PG and signal entry."""
    exact = out / f"{name}-exact.lef"
    if name == "multiply" or name == "normalize":
        exact = source_lef
    else:
        tcl = out / f"{name}-geometry.tcl"
        tcl.write_text(f"read_db {{{odb}}}\nwrite_abstract_lef -bloat_factor 0 {{{exact}}}\n")
        run(["openroad", "-no_init", "-exit", str(tcl)], out / f"{name}-geometry.log")

    before, obs, _ = source_lef.read_text().partition("\n  OBS\n")
    head, marker, body = exact.read_text().partition("\n  OBS\n")
    if not obs or not marker or before != head:
        raise ValueError(f"{name}: exact view changes leaf pins or outline")
    target = out / f"{name}.lef"
    if name in {"multiply", "normalize"} and not compact_obs:
        shutil.copyfile(exact, target)
        return target

    experiment = Path(__file__).parent
    cuts = out / f"{name}-cuts.tsv"
    if same_net or guard_cuts:
        run(["klayout", "-b", "-rd", f"in_gds={odb.with_suffix('.gds')}",
             "-rd", f"cut_rectangles={cuts}", "-r", str(experiment / "leaf_cuts.rb")],
            out / f"{name}-cuts.log")
    if not same_net:
        sections = re.split(r"(?m)^    LAYER (\w+) ;\n", body)
        for index, layer in enumerate(sections[1::2]):
            if layer not in {f"metal{number}" for number in range(1, 7)}:
                continue
            geometry = sections[2*index+2]
            boxes = [tuple(map(float, box)) for box in
                     re.findall(r"RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)", geometry)]
            if boxes:
                x0, y0, x1, y1 = zip(*boxes)
                extent = (min(x0), min(y0), max(x1), max(y1))
                sections[2*index+2] = "      RECT " + " ".join(f"{value:g}" for value in extent) + " ;\n"
        cut_layers = ""
        if guard_cuts:
            by_layer = {"via7": [], "via9": []}
            for row in cuts.read_text().splitlines():
                layer, *coords = row.split()
                x0, y0, x1, y1 = map(int, coords)
                guard = {"via7": 80, "via9": 160}[layer]
                box = ((x0-guard)/2000, (y0-guard)/2000, (x1+guard)/2000, (y1+guard)/2000)
                by_layer[layer].append("      RECT " + " ".join(map(str, box)) + " ;\n")
            cut_layers = "".join(f"    LAYER {layer} ;\n" + "".join(rects)
                                 for layer, rects in by_layer.items())
        target.write_text(head + marker + cut_layers + sections[0] + "".join(
            f"    LAYER {layer} ;\n{geometry}"
            for layer, geometry in zip(sections[1::2], sections[2::2])
        ))
        return target

    routes = out / f"{name}-access.tsv"
    env = dict(os.environ, PJ_LEAF_ODB=str(odb), PJ_LEAF_ROUTES=str(routes))
    with (out / f"{name}-access.log").open("w") as log:
        subprocess.run(["openroad", "-no_init", "-threads", "1", "-exit", str(experiment / "leaf_access.tcl")],
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    if access_layers:
        # The old SRAM pads have alternating M9 track phases. Where the
        # original M10 landing is half a track off, expose real same-net
        # approach metal. Never enlarge the copper or relabel another net.
        off_track = set()
        for pin, body in re.findall(r"(?ms)^  PIN (\S+)\n(.*?)^  END \1\n", head):
            if "USE SIGNAL" not in body or "LAYER metal10" not in body:
                continue
            box = re.search(r"RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)", body)
            if not box:
                continue
            _, y0, _, y1 = map(float, box.groups())
            if (round((y0 + y1) * 1000) - 140) % 3200:
                off_track.add(pin)
        kept = [line for line in routes.read_text().splitlines()
                if line.split("\t")[0] in off_track and line.split("\t")[1] in access_layers]
        if not kept:
            raise ValueError("no off-track SRAM approach geometry")
        routes.write_text("\n".join(kept) + "\n")
    run(["python3", "-B", str(experiment / "conservative_lef.py"), str(exact), str(routes), str(target), str(cuts)],
        out / f"{name}-abstract.log")
    return target


def conservative_tech_lef(out):
    """Guard parent routing against native whole-GDS spacing mismatches."""
    source = Path("/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef")
    text = source.read_text()
    guards = {
        "via7": ("SPACING 0.44 ;", "SPACING 0.50 ;"),
        "via9": ("SPACING 0.88 ;", "SPACING 0.96 ;"),
        "metal10": (
            "WIDTH 0.0000       0.8000     0.8000     0.8000",
            "WIDTH 0.0000       0.8500     0.8500     0.8500",
        ),
    }
    for layer, (old, new) in guards.items():
        pattern = rf"(?ms)^LAYER {layer}\n.*?^END {layer}$"
        match = re.search(pattern, text)
        if not match or match.group().count(old) != 1:
            raise ValueError(f"unexpected Nangate45 routing rules for {layer}")
        text = text[:match.start()] + match.group().replace(old, new) + text[match.end():]
    target = out / "parent-route.tech.lef"
    target.write_text(text)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("slot", type=int, choices=range(44))
    parser.add_argument("cpus", type=int)
    args = parser.parse_args()
    if args.cpus not in (10, 12) or len(os.sched_getaffinity(0)) < args.cpus:
        raise ValueError("expected 10 or 12 assigned cores")

    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    compact_u_probe = 24 <= args.slot < 28 or 32 <= args.slot < 36 or args.slot >= 40
    guard_native = args.slot >= 36
    compact_obs = args.slot >= 28
    group = "P" if not compact_u_probe and (args.slot >= 16 or args.slot % 8 < 4) else "U"
    with_controller = args.slot >= 8
    exact_p_probe = 16 <= args.slot < 24 or 28 <= args.slot < 32 or 36 <= args.slot < 40
    m9_probe = 20 <= args.slot < 24 or 28 <= args.slot < 32 or 36 <= args.slot < 40
    pg_offset = (5, 12, 17, 23)[args.slot % 4] if exact_p_probe else 5
    if m9_probe and args.slot in {20, 28, 36}:
        pg_offset = 12
    rtl = Path("project/rtl/pu_leaf_base").resolve()
    top = f"pu_{group.lower()}_group"
    controller = None
    if with_controller:
        controller, top = stage_controller(out, group)
    prefix = "datapath." if with_controller else ""
    base = Path("/public/home/yuzelu/project-circuit/LLMHardwareDesign")
    leaves = prepare_leaves(base, out, group)
    files = {}
    dimensions = {}
    for instance, (lef, liberty, gds) in leaves.items():
        instance_files = []
        files[instance + ".odb"] = {"source": str(gds.with_suffix(".odb")), "sha256": digest(gds.with_suffix(".odb"))}
        for suffix, path in [("lef", lef), ("lib", liberty), ("gds", gds)]:
            staged = out / f"{instance}.{suffix}"
            if suffix == "lef":
                use_same_net = group == "P" and (not exact_p_probe or (m9_probe and instance == "store"))
                staged = route_abstract(path, gds.with_suffix(".odb"), out, instance, use_same_net,
                                        ({"metal8", "metal9", "metal10"} if args.slot % 4 == 2
                                         else {"metal8", "metal9"})
                                        if m9_probe and instance == "store" else None,
                                        compact_obs=compact_obs, guard_cuts=guard_native)
            else:
                shutil.copyfile(path, staged)
            files[str(staged)] = {"source": str(path), "sha256": digest(staged)}
            instance_files.append(staged)
        size = re.search(r"\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)", instance_files[0].read_text())
        dimensions[instance] = tuple(float(value) for value in size.groups())
    gap = 88 if m9_probe and args.slot in {20, 28, 36} else (48, 88, 136, 200)[args.slot % 4]
    margin = 48
    store, main_macro, small_macro = leaves
    sw, sh = dimensions[store]
    mw, mh = dimensions[main_macro]
    gw, gh = dimensions[small_macro]
    locations = {
        store: (margin, margin),
        main_macro: (margin + sw + gap, margin),
        small_macro: (margin + sw - gw, margin + sh + gap),
    }
    width = round(sw + mw + gap + 2 * margin)
    height = round(max(mh, sh + gap + gh) + 2 * margin)
    if compact_u_probe:
        locations = {
            store: (margin, margin),
            small_macro: (margin, margin + sh + gap),
            main_macro: (margin + gw + gap, margin + sh + gap),
        }
        width = round(max(sw, gw + gap + mw) + 2 * margin)
        height = round(sh + gap + max(gh, mh) + 2 * margin)
    placement = out / "place.tcl"
    placement.write_text("".join(
        f"place_macro -macro_name {prefix}{name} -location {{{x} {y}}} -orientation R0 -exact\n"
        f"[[ord::get_db_block] findInst {prefix}{name}] setPlacementStatus FIRM\n"
        for name, (x, y) in locations.items()
    ))
    sdc = out / "top.sdc"
    sdc.write_text(
        "create_clock -name clk -period 3.333333333333 [get_ports clk]\n"
        "set_clock_uncertainty 0.1 [get_clocks clk]\n"
        "set data_in [lsearch -all -inline -not -exact [all_inputs] [get_ports clk]]\n"
        "set_input_delay -clock clk -max 0.8 $data_in\nset_input_delay -clock clk -min 0.2 $data_in\n"
        "set_output_delay -clock clk -max 0.8 [all_outputs]\nset_output_delay -clock clk -min 0.2 [all_outputs]\n"
        "set_load 50 [all_outputs]\n"
    )
    if with_controller:
        with sdc.open("a") as constraints:
            constraints.write(
                "set raw_reset [get_ports rst_ni]\n"
                "set reset_sinks [get_fanout -flat -endpoints_only -from $raw_reset]\n"
                "if {[llength $reset_sinks] != 2} {error \"raw reset must reach exactly two synchronizer pins\"}\n"
                "foreach sink $reset_sinks {\n"
                "    if {![string match */RN [get_full_name $sink]]} {error \"unexpected raw reset endpoint\"}\n"
                "}\n"
                "set_false_path -from $raw_reset -to $reset_sinks\n"
            )
    pdn = out / "pdn.tcl"
    pdn.write_text(
        "add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power\n"
        "add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground\n"
        "global_connect\nset_voltage_domain -name CORE -power VDD -ground VSS\n"
        "define_pdn_grid -name parent -voltage_domains CORE -pins metal10\n"
        "add_pdn_stripe -grid parent -layer metal1 -width 0.17 -pitch 2.4 -offset 0 -followpins\n"
        "add_pdn_stripe -grid parent -layer metal4 -width 0.48 -pitch 56 -offset 2\n"
        "add_pdn_stripe -grid parent -layer metal7 -width 1.40 -pitch 30 -offset 2\n"
        f"add_pdn_stripe -grid parent -layer metal10 -width 1.40 -pitch 60 -offset {pg_offset}\n"
        + "".join(f"add_pdn_connect -grid parent -layers {{{a} {b}}}\n"
                  for a, b in (("metal1", "metal4"), ("metal4", "metal7"), ("metal7", "metal10")))
        + "".join(f"define_pdn_grid -name g_{name} -voltage_domains CORE -macro -instances {{^{re.escape(prefix + name)}$}} "
                  "-grid_over_pg_pins -halo {2 2 2 2}\n"
                  f"add_pdn_connect -grid g_{name} -layers {{metal7 metal10}}\n" for name in leaves)
    )
    post_pdn = out / "post-pdn.tcl"
    filter_pg = Path(__file__).with_name("filter_pg_landings.tcl")
    post_pdn.write_text(
        f"source {{{filter_pg}}}\npj_filter_pg {{{' '.join(prefix + name for name in leaves)}}} {{{out / 'pg-removed.tsv'}}}\n"
    )
    footprint = out / "late-pins.tcl"
    contract = Path(__file__).with_name("contract.json")
    endpoint = json.loads(contract.read_text())["groups"][group]["direct"]
    families = (endpoint["source"], endpoint["sink"])
    footprint.write_text(
        f"set width {width}\nset height {height}\nset pg_offset {pg_offset}\nset families {{{' '.join(families)}}}\n"
        f"set data_count {endpoint['data_bits']}\nset return_name {endpoint['return']}\n"
        + """
set block [ord::get_db_block]
set pg [expr {[[$block getCoreArea] xMin]/double([$block getDbUnitsPerMicron])+$pg_offset}]
set ports {}
foreach bterm [$block getBTerms] {lappend ports [$bterm getName]}
set row 0
foreach prefix $families {
    set available {}
    for {set band 0} {$band < 2} {incr band} {
        set y [expr {8*($height/8)-16+.070-8*($row+3*$band)}]
        for {set x 40.095} {$x < $width-40} {set x [expr {$x+8}]} {
            set dx [expr {$x-$pg}]
            if {abs($dx-30*round($dx/30.0))>=4.0} {
                lappend available [list $x $y]
            }
        }
    }
    set selected {}
    for {set bit 0} {$bit < $data_count} {incr bit} {
        lappend selected [format {%sdata[%d]} $prefix $bit]
    }
    lappend selected "${prefix}valid" "${prefix}$return_name"
    foreach pin $selected {
        if {[lsearch -exact $ports $pin] < 0} {error "missing physical port: $pin"}
    }
    if {[llength $selected] > [llength $available]} {error "insufficient M10 landing sites"}
    set index 0
    foreach pin $selected {
        set xy [lindex $available $index]
        incr index
        place_pin -pin_name $pin -layer metal10 -location $xy -pin_size {2 2}
    }
    incr row
}
"""
    )
    std = "/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib"
    verilog = " ".join(map(str, sorted(rtl.glob("*.sv"))))
    verilog += " " + str(Path("project/rtl/block_local_s/block_local_s_arbiter.sv").resolve())
    include = ""
    if controller:
        verilog += " " + " ".join(map(str, sorted(controller.glob("*.sv"))))
        include = f"-I{controller} "
    abc = Path(shutil.which("yosys")).resolve().with_name("yosys-abc")
    batch = out / "abc-batch"
    batch.write_text(f'#!/bin/sh\nexec {shlex.quote(str(abc))} "$@"\n')
    batch.chmod(0o755)
    mapped = out / "mapped.v"
    yosys = out / "map.ys"
    yosys.write_text(
        "".join(f"read_liberty -lib {out / (name + '.lib')}\n" for name in leaves)
        + f"read_liberty -lib {std}\nread_verilog -sv {include}{verilog}\n"
        + f"hierarchy -check -top {top}\nsynth -top {top} -flatten -noabc\n"
        + f"dfflibmap -liberty {std}\nabc -exe {batch} -liberty {std}\n"
        + f"hilomap -hicell LOGIC1_X1 Z -locell LOGIC0_X1 Z\n"
        + f"clean -purge\ncheck -assert\nwrite_verilog -noattr -noexpr {mapped}\n"
    )
    run(["yosys", "-Q", "-s", str(yosys)], out / "premap.log")
    mapped.write_text(re.sub(r"(?m)^(\s*wire) signed ", r"\1 ", mapped.read_text()))
    pre_cts = out / "pre-cts.tcl"
    pre_cts.write_text(
        "rename repair_timing_helper pu_repair_timing_helper\n"
        "proc repair_timing_helper {args} { pu_repair_timing_helper {*}$args -max_buffer_percent 60 }\n"
    )
    pre_route = out / "pre-global-route.tcl"
    protection = ""
    if guard_native:
        source = Path(__file__).parents[1] / "block_v1/native_input_diodes.tcl"
        diode_hook = out / "input-diodes.tcl"
        diode_hook.write_text(source.read_text().replace('  if {[$port getName] eq "clk"} {continue}\n', ""))
        protection = f"source {{{diode_hook}}}\n"
    pre_route.write_text(
        protection +
        "rename pin_access pu_pin_access\n"
        "proc pin_access {args} { pu_pin_access {*}$args -min_access_points 1 }\n"
        "set ::env(HOLD_SLACK_MARGIN) 0.065\n"
        "rename repair_timing_helper pu_grt_repair\n"
        "proc repair_timing_helper {args} {\n"
        "    pu_grt_repair {*}$args -max_buffer_percent 60\n"
        "    repair_design -cap_margin 35 -slew_margin 20\n"
        "}\n"
    )
    cts_flags = (
        "-balance_levels -apply_ndr none -obstruction_aware -root_buf BUF_X32 -buf_list {BUF_X8 BUF_X16 BUF_X32}",
        "-balance_levels -apply_ndr none -no_insertion_delay -root_buf BUF_X32 -buf_list {BUF_X8 BUF_X16 BUF_X32}",
        "-balance_levels -apply_ndr none -no_insertion_delay -root_buf CLKBUF_X3 -buf_list {CLKBUF_X2 CLKBUF_X3}",
        "-balance_levels -apply_ndr none -obstruction_aware -root_buf BUF_X32 -buf_list {BUF_X8 BUF_X16 BUF_X32} -distance_between_buffers 200",
    )[args.slot % 4]
    cfg = {
        "PLATFORM": "nangate45",
        "DESIGN_NAME": top,
        "VERILOG_FILES": verilog,
        "SDC_FILE": sdc,
        "SYNTH_NETLIST_FILES": mapped,
        "ADDITIONAL_LEFS": " ".join(str(out / f"{name}.lef") for name in leaves),
        "ADDITIONAL_LIBS": " ".join(str(out / f"{name}.lib") for name in leaves),
        "ADDITIONAL_GDS": " ".join(str(out / f"{name}.gds") for name in leaves),
        "DIE_AREA": f"0 0 {width} {height}",
        "CORE_AREA": f"20 20 {width - 20} {height - 20}",
        "MACRO_PLACEMENT_TCL": placement,
        "PDN_TCL": pdn,
        "POST_PDN_TCL": post_pdn,
        "CAP_MARGIN": 35,
        "PRE_GLOBAL_ROUTE_TCL": pre_route,
        "GLOBAL_ROUTE_ARGS": "-allow_congestion -congestion_iterations 12",
        "GLOBAL_ROUTE_USE_CUGR": int(group == "U" and args.slot % 4 != 0),
        "VIA_IN_PIN_MIN_LAYER": "metal10",
        "VIA_IN_PIN_MAX_LAYER": "metal10",
        "DETAILED_ROUTE_ARGS": "-via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -droute_end_iter 64",
        "MACRO_PLACE_HALO": "12 12",
        "PLACE_DENSITY": ".36",
        "SYNTH_HIERARCHICAL": 0,
        "HOLD_SLACK_MARGIN": ".005",
        "CTS_ARGS": "-sink_clustering_enable -repair_clock_nets " + cts_flags,
        "CTS_SNAPSHOTS": 1,
        "DETAILED_METRICS": 1,
        "PRE_CTS_TCL": pre_cts,
        "MAX_ROUTING_LAYER": "metal10",
        "MAX_CLK_ROUTING_LAYER": "metal10",
    }
    if guard_native:
        cfg["TECH_LEF"] = conservative_tech_lef(out)
    cfg["FOOTPRINT_TCL"] = footprint
    config = out / "config.mk"
    config.write_text("".join(f"export {key} = {value}\n" for key, value in cfg.items()))
    (out / "inputs.json").write_text(json.dumps(dict(group=group, with_controller=with_controller, pg_offset=pg_offset, dimensions=dimensions,
                                                     die_um=(width,height), endpoint_contract_sha256=digest(contract),
                                                     locations=locations, files=files), indent=2))
    command = ["make", "-C", "/OpenROAD-flow-scripts/flow", f"DESIGN_CONFIG={config}",
               f"WORK_HOME={out / 'flow'}", f"NUM_CORES={args.cpus}"]
    for stage in ("synth", "do-floorplan", "do-place", "do-cts", "do-route", "do-finish", "do-gds"):
        run(command + [stage], out / f"{stage}.log")


if __name__ == "__main__":
    main()
