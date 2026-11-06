"""Build the native-layer Qwen transport block with actual M10 terminal shapes."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("top", choices=("qwen_c0_receive", "qwen_nine_transport"))
    parser.add_argument("out", type=Path)
    parser.add_argument("--size", type=int, default=1792)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    out = args.out.resolve()
    out.mkdir(parents=True)
    size = args.size
    if size % 8:
        parser.error("--size must be a multiple of 8 um")
    sources = repo / "project/rtl/qwen_transport"
    top_file = {"qwen_c0_receive": "c0_receive.sv", "qwen_nine_transport": "nine_transport.sv"}[args.top]
    rtl = [sources / name for name in ("word_switch.sv", "sram_port_adapter.sv", top_file)]
    (out / "switch.sdc").write_text(
        "create_clock -name clk -period 3.333333333 [get_ports clk]\n"
        "set inputs [all_inputs]\n"
        "foreach p $inputs {if {[get_full_name $p] ne \"clk\"} {set_input_delay -clock clk 0.30 $p}}\n"
        "set_output_delay -clock clk 0.30 [all_outputs]\n"
        "set_load 20 [all_outputs]\n"
    )
    (out / "pins.tcl").write_text(f"set size {size}\n" + r"""
set names {}
foreach term [[ord::get_db_block] getBTerms] {
    if {[$term getSigType] ni {POWER GROUND}} {lappend names [$term getName]}
}
set slots [expr {($size-144)/8}]
set k 0
foreach name [lsort -dictionary $names] {
    set edge [expr {$k % 4}]
    set slot [expr {$k / 4}]
    set row [expr {$slot / $slots}]
    set pos [expr {72+8*($slot % $slots)}]
    set inset [expr {24+8*$row}]
    if {$inset > 64} {error "No room for another row of M10 terminals"}
    switch $edge {
        0 {set xy [list [expr {$pos+.095}] [expr {$inset+.070}]]}
        1 {set xy [list [expr {$size-$inset+.095}] [expr {$pos+.070}]]}
        2 {set xy [list [expr {$pos+.095}] [expr {$size-$inset+.070}]]}
        3 {set xy [list [expr {$inset+.095}] [expr {$pos+.070}]]}
    }
    place_pin -pin_name $name -layer metal10 -location $xy -pin_size {2 2}
    incr k
}
""")
    (out / "pdn.tcl").write_text("""
add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name switch -voltage_domains CORE -pins metal7
add_pdn_stripe -grid switch -layer metal1 -width 0.17 -pitch 2.4 -offset 0 -followpins
add_pdn_stripe -grid switch -layer metal4 -width 0.48 -pitch 56 -offset 2
add_pdn_stripe -grid switch -layer metal7 -width 1.40 -pitch 30 -offset 2
add_pdn_connect -grid switch -layers {metal1 metal4}
add_pdn_connect -grid switch -layers {metal4 metal7}
""")
    config = {
        "PLATFORM": "nangate45", "DESIGN_NAME": args.top, "DESIGN_NICKNAME": args.top,
        "VERILOG_FILES": " ".join(map(str, rtl)), "SDC_FILE": out / "switch.sdc",
        "DIE_AREA": f"0 0 {size} {size}", "CORE_AREA": f"20 20 {size-20} {size-20}",
        "FOOTPRINT_TCL": out / "pins.tcl", "PDN_TCL": out / "pdn.tcl",
        "PLACE_DENSITY": ".25", "SYNTH_HIERARCHICAL": 0, "KEEP_VARS": 1,
        "GLOBAL_ROUTE_ARGS": "-allow_congestion -congestion_iterations 12",
    }
    mk = out / "config.mk"
    mk.write_text("".join(f"export {name} = {value}\n" for name, value in config.items()))
    # The image's ABC persistent worker waits on the completion pipe in Slurm.
    # An explicit executable path selects Yosys's batch mode for the same ABC.
    abc = out / "abc-batch"
    abc.symlink_to(shutil.which("yosys-abc") or
                   "/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys-abc")
    upstream = Path("/OpenROAD-flow-scripts/flow/scripts/synth.tcl").read_text()
    needle = "log_cmd abc {*}$abc_args"
    if upstream.count(needle) != 1:
        raise RuntimeError("Expected exactly one ORFS Liberty ABC invocation")
    synth = out / "synth-batch.tcl"
    synth.write_text(upstream.replace(needle, f"log_cmd abc -exe {{{abc}}} {{*}}$abc_args"))
    command = ["make", "-C", "/OpenROAD-flow-scripts/flow", f"DESIGN_CONFIG={mk}",
               f"WORK_HOME={out/'flow'}", f"NUM_CORES={os.environ['SLURM_CPUS_PER_TASK']}",
               f"SYNTH_SCRIPT={synth}",
               "MAX_ROUTING_LAYER=metal10", "MAX_CLK_ROUTING_LAYER=metal10"]
    receipt = dict(top=args.top, size_um=size, stages={},
                   sources={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in rtl})
    for stage in ("synth", "do-floorplan", "do-place", "do-cts", "do-route", "do-finish", "do-gds"):
        with (out / f"{stage}.log").open("w") as log:
            result = subprocess.run(command+[stage], stdout=log, stderr=subprocess.STDOUT)
        receipt["stages"][stage] = result.returncode
        (out / "build.json").write_text(json.dumps(receipt, indent=2)+"\n")
        result.check_returncode()
    results = out / "flow/results/nangate45" / args.top / "base"
    (out / "abstract.tcl").write_text(
        f"read_db {{{results/'6_final.odb'}}}\n"
        f"write_abstract_lef -bloat_factor 0 {{{out/'switch.lef'}}}\n"
    )
    with (out / "abstract.log").open("w") as log:
        subprocess.run(["openroad", "-no_init", "-exit", str(out/"abstract.tcl")],
                       stdout=log, stderr=subprocess.STDOUT, check=True)


if __name__ == "__main__":
    main()
