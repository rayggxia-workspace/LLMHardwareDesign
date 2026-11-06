#!/usr/bin/env python3
"""Build a leaf-preserving, fixed-data baseline for top-level C/F/J P&R."""
import hashlib
import json
import re
import sys
import subprocess
from pathlib import Path

source, root, out = (Path(value).resolve() for value in sys.argv[1:4])
kind, variant = sys.argv[4:6]
late = len(sys.argv) > 6 and sys.argv[6] == "late"
if kind not in ("c", "f", "j") or variant not in ("compact", "room"):
    raise ValueError("expected c/f/j and compact/room")
out.mkdir(parents=True, exist_ok=True)
ge = root / "issue-201-compact-ge/2ba89c0bd/release"
s = root / "issue-200-compact-local-s"
t = root / "issue-187-p16-j16/005-leaf-views"
r = root / "issue-166-r-local-state/attempt252/delivery"
views = {
    "store.leaf": (s / "audit08/base0/local_s_base.lef", s / "audit08/base0/local_s_base.lib",
        s / "run08-base0/results/0/flow/results/nangate45/local_s_base/base/6_final.gds"),
}
g_view = ge / "g"
e_view = ge / "e_compact"
e_instance = "arithmetic.leaf" if kind == "j" else "engine[0].element.arithmetic.leaf"
views[e_instance] = (e_view / "block_v2_e_compact.lef", e_view / "block_v2_e_compact.lib", e_view / "6_final.gds")
if kind in ("c", "f"):
    views["engine[1].genblk1.activate.leaf"] = (g_view / "block_v2_g.lef", g_view / "block_v2_g.lib", g_view / "6_final.gds")
if kind == "c":
    views["engine[2].genblk1.recurrent.leaf.leaf"] = (r / "abstract/r_stream_local.lef",
        r / "abstract/r_stream_local_typ.lib", r / "native/6_final.gds")
if kind == "j":
    views["lease"] = (t / "views/T/leaf.lef", t / "views/T/leaf.lib", t / "inputs/T/6_final.gds")

# Keep the accepted pin shapes. Regenerate the OBS from the exact native ODB
# instead of using the all-layer bounding box intended for isolated leaf export.
for key, (lef, lib, gds) in views.items():
    odb = gds.with_suffix(".odb")
    exact = out / lef.name
    script = out / (lef.stem + "-abstract.tcl")
    script.write_text(f"read_db {{{odb}}}\nwrite_abstract_lef -bloat_factor 0 {{{exact}}}\n")
    with (out / (lef.stem + "-abstract.log")).open("w") as log:
        subprocess.run(["openroad", "-no_init", "-exit", str(script)], stdout=log, stderr=log, check=True)
    def pins(view):
        return view.read_text().split("\n  PIN ", 1)[-1].split("\n  OBS",1)[0]
    if pins(lef) != pins(exact):
        raise ValueError(f"{lef}: exact abstract changed accepted pin declarations")
    views[key] = exact, lib, gds

rtl = source / "project/rtl/block_cfj_v1"
top = "block_cfj_j" if kind=="j" else "block_cfj_cf"
# Compile the C parameter override explicitly and bind the prequalified R256
# physical master to the unparameterized blackbox from its Liberty view.
rtl_files = []
for path in sorted(rtl.glob("*.sv")):
    if path.name == "block_cfj_j.sv" and kind != "j" or path.name == "block_cfj_cf.sv" and kind == "j":
        continue
    target = out / path.name
    code = path.read_text(encoding="utf-8")
    if kind == "c" and path.stem == top:
        code = code.replace("parameter integer KIND = 1", "parameter integer KIND = 2")
    if late and path.stem == top:
        feature = "LATE_E_WRITEBACK" if kind == "j" else "LATE_G_E"
        code = code.replace(f"parameter bit {feature}=0", f"parameter bit {feature}=1")
        code = code.replace(f"parameter bit {feature} = 0", f"parameter bit {feature} = 1")
    if path.stem == "ucf_r256_service":
        code = code.replace("r_stream_local #(.WORDS(256))", "r_stream_local")
    target.write_text(code)
    rtl_files.append(target)

gap = 64 if variant == "compact" else 104
x = y = gap
row_height = 0
width = 0
placement = []
inventory = {}
for idx, (instance, files) in enumerate(views.items()):
    lef = files[0].read_text()
    master = re.search(r"^MACRO (\S+)", lef, re.M).group(1)
    mw, mh = (float(v) for v in re.search(r"SIZE ([\d.]+) BY ([\d.]+)", lef).groups())
    if idx == 2:
        y += row_height + gap
        row_height = 0
        x = gap
    placement.append(f"set selected [find_master {{{master}}}]")
    placement.append(f"$selected setLocation {int(x*2000)} {int(y*2000)}")
    placement.append("$selected setPlacementStatus FIRM")
    inventory[instance] = dict(master=master, xy_um=[x,y], size_um=[mw,mh],
        files={str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
    x = 8 * ((int(x+mw+gap)+7)//8)
    row_height = max(row_height, int(mh))
    width = max(width,x)
height = y+row_height+gap
placement_prologue = """proc find_master {name} {
    set selected {}
    foreach inst [[ord::get_db_block] getInsts] {
        if {[[$inst getMaster] getName] eq $name} {lappend selected $inst}
    }
    if {[llength $selected] != 1} {error "Expected one $name in this fixture"}
    return [lindex $selected 0]
}
"""
(out / "placement.tcl").write_text(placement_prologue+"\n".join(placement)+"\n")
(out / "inventory.json").write_text(json.dumps(dict(kind=kind, variant=variant, size_um=[width,height],
    instances=inventory, scope="split M10 endpoints" if late else "fixed-data baseline"), indent=2)+"\n")

(out / "input.sdc").write_text("""create_clock -name clk -period 3.333333333333333 [get_ports clk]
set_clock_uncertainty 0.1 [get_clocks clk]
set_clock_transition 0.05 [get_clocks clk]
set data_inputs [lsearch -all -inline -not -exact [all_inputs] [get_ports clk]]
set_input_delay -max 0.8 -clock clk $data_inputs
set_input_delay -min 0.2 -clock clk $data_inputs
set_driving_cell -lib_cell BUF_X2 -pin Z $data_inputs
set_output_delay -max 0.8 -clock clk [all_outputs]
set_output_delay -min 0.2 -clock clk [all_outputs]
set_load 0.05 [all_outputs]
""")
pdn = '''add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name parent -voltage_domains CORE -pins metal10
add_pdn_stripe -grid parent -layer metal1 -width 0.17 -pitch 2.4 -offset 0 -followpins
add_pdn_stripe -grid parent -layer metal4 -width 0.48 -pitch 56 -offset 2
add_pdn_stripe -grid parent -layer metal7 -width 1.40 -pitch 30 -offset 2
add_pdn_stripe -grid parent -layer metal10 -width 1.40 -pitch 60 -offset 5
add_pdn_connect -grid parent -layers {metal1 metal4}
add_pdn_connect -grid parent -layers {metal4 metal7}
add_pdn_connect -grid parent -layers {metal7 metal10}
'''
for idx, (instance, leaf) in enumerate(inventory.items()):
    pdn += f"define_pdn_grid -name grid_{idx} -voltage_domains CORE -macro -cells {{{leaf['master']}}} -grid_over_pg_pins -halo {{2 2 2 2}}\n"
    pdn += f'add_pdn_connect -grid grid_{idx} -layers {{metal7 metal10}}\n'
(out / 'pdn.tcl').write_text(pdn)

filter_script = Path(__file__).with_name("filter_pg_landings.tcl")
(out / "post-pdn.tcl").write_text(
    placement_prologue + f"source {{{filter_script}}}\n" +
    "set macros [list " + " ".join(f"[[find_master {{{leaf['master']}}}] getName]" for leaf in inventory.values()) +
    f"]\npj_filter_pg $macros {{{out / 'pg-removed.tsv'}}}\n"
)

if late:
    # Both terminal sets are real, separate native nets. All positions lie on
    # the 4 um research grid, away from the parent metal10 supply stripes.
    driver, sink, lanes = ("late_e", "late_s", 128) if kind == "j" else ("late_g", "late_e", 32)
    links = [(f"{driver}_data[{i}]", f"{sink}_data[{i}]") for i in range(lanes)]
    links += [(driver+"_valid", sink+"_valid"), (sink+"_take", driver+"_take")]
    slots = [x+0.095 for x in range(64, width-63, 8)
             if abs((x+0.095-21+15)%30-15)>=4]
    slots_count = len(slots)
    if slots_count*2 < len(links):
        raise ValueError("not enough M10 pin tracks")
    positions = {}
    bottom = 32.070
    top_y = 8*((height-32)//8) + 0.070
    commands = []
    for i, (a,b) in enumerate(links):
        x = slots[i%slots_count]
        for name,y in [(a,top_y-16*(i//slots_count)),(b,bottom+16*(i//slots_count))]:
            positions[name] = [x,y]
            commands.append(f"place_pin -pin_name {{{name}}} -layer metal10 -location {{{x:.3f} {y:.3f}}} -pin_size {{2 2}}")
    (out/"cut-pins.tcl").write_text("\n".join(commands)+"\n")
    (out/"cut-links.json").write_text(json.dumps(dict(links=links, positions_um=positions),indent=2)+"\n")

cfg = {
    "PLATFORM":"nangate45", "DESIGN_NAME":top, "DESIGN_NICKNAME":kind+"-"+variant,
    "VERILOG_FILES":" ".join(map(str,rtl_files)), "SDC_FILE":out/"input.sdc",
    "ADDITIONAL_LEFS":" ".join(str(v[0]) for v in views.values()),
    "ADDITIONAL_LIBS":" ".join(str(v[1]) for v in views.values()),
    "ADDITIONAL_GDS":" ".join(str(v[2]) for v in views.values()),
    "DIE_AREA":f"0 0 {width} {height}", "CORE_AREA":f"16 16 {width-16} {height-16}",
    "MACRO_PLACEMENT_TCL":out/"placement.tcl", "MACRO_PLACE_HALO":"12 12",
    "PDN_TCL":out/"pdn.tcl", "POST_PDN_TCL":out/"post-pdn.tcl",
    "PLACE_DENSITY":".35", "SYNTH_HIERARCHICAL":0,
    "TNS_END_PERCENT":100, "CAP_MARGIN":35,
}
if late:
    cfg["FOOTPRINT_TCL"] = out/"cut-pins.tcl"
if len(sys.argv) > 7 and sys.argv[7] == "balanced":
    cfg["CTS_ARGS"] = ("-sink_clustering_enable -repair_clock_nets -apply_ndr none "
                       "-no_insertion_delay -balance_levels -root_buf BUF_X32 "
                       "-buf_list {BUF_X8 BUF_X16 BUF_X32}")
    cfg["HOLD_SLACK_MARGIN"] = ".005"
(out / "config.mk").write_text("".join(f"export {key} = {value}\n" for key,value in cfg.items()))
