#!/usr/bin/env python3
"""Build a leaf-preserving, fixed-data baseline for top-level C/F/J P&R."""
import hashlib
import json
import re
import sys
from pathlib import Path

source, root, out = (Path(value).resolve() for value in sys.argv[1:4])
kind, variant = sys.argv[4:6]
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
e_instance = "arithmetic.leaf" if kind == "j" else "engine[0].arithmetic.leaf"
views[e_instance] = (e_view / "block_v2_e_compact.lef", e_view / "block_v2_e_compact.lib", e_view / "6_final.gds")
if kind in ("c", "f"):
    views["engine[1].activate.leaf"] = (g_view / "block_v2_g.lef", g_view / "block_v2_g.lib", g_view / "6_final.gds")
if kind == "c":
    views["engine[2].recurrent.leaf.leaf"] = (r / "abstract/r_stream_local.lef",
        r / "abstract/r_stream_local_typ.lib", r / "native/6_final.gds")
if kind == "j":
    views["lease"] = (t / "views/T/leaf.lef", t / "views/T/leaf.lib", t / "inputs/T/6_final.gds")

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
    placement.append(f"place_macro -macro_name {{{instance}}} -location {{{x} {y}}} -orientation R0 -exact")
    placement.append(f"[[ord::get_db_block] findInst {{{instance}}}] setPlacementStatus FIRM")
    inventory[instance] = dict(master=master, xy_um=[x,y], size_um=[mw,mh],
        files={str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
    x = 8 * ((int(x+mw+gap)+7)//8)
    row_height = max(row_height, int(mh))
    width = max(width,x)
height = y+row_height+gap
(out / "placement.tcl").write_text("\n".join(placement)+"\n")
(out / "inventory.json").write_text(json.dumps(dict(kind=kind, variant=variant, size_um=[width,height],
    instances=inventory, scope="fixed-data baseline, not a late-metal product"), indent=2)+"\n")

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
cfg = {
    "PLATFORM":"nangate45", "DESIGN_NAME":top, "DESIGN_NICKNAME":kind+"-"+variant,
    "VERILOG_FILES":" ".join(map(str,rtl_files)), "SDC_FILE":out/"input.sdc",
    "ADDITIONAL_LEFS":" ".join(str(v[0]) for v in views.values()),
    "ADDITIONAL_LIBS":" ".join(str(v[1]) for v in views.values()),
    "ADDITIONAL_GDS":" ".join(str(v[2]) for v in views.values()),
    "DIE_AREA":f"0 0 {width} {height}", "CORE_AREA":f"16 16 {width-16} {height-16}",
    "MACRO_PLACEMENT_TCL":out/"placement.tcl", "MACRO_PLACE_HALO":"12 12",
    "PLACE_DENSITY":".35", "SYNTH_HIERARCHICAL":0,
    "TNS_END_PERCENT":100, "CAP_MARGIN":35,
}
(out / "config.mk").write_text("".join(f"export {key} = {value}\n" for key,value in cfg.items()))
