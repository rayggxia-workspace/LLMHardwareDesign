"""Generate a port-for-port direct wrapper around exactly one hardened VECTOR.

This is an engineering integration harness, not the llaccel core or a reusable
prefabricated base. There is no extra register, changed width or protocol delay.
"""
from pathlib import Path
import json
import os
import re

root = Path.cwd()
block = Path(os.environ["LLHD_BLOCK"])
result = block / "flow/results/nangate45/llhd_vec_original/base"
ports = json.loads((block / "vec-elab.json").read_text())["modules"]["vec_engine"]["ports"]
assert len(ports) == 26 and sum(len(p["bits"]) for p in ports.values()) == 2246
assert ports["instr"]["direction"] == "input" and len(ports["instr"]["bits"]) == 512
for name in ("vec_rd0_rdata", "vec_rd1_rdata", "vec_wr_wdata"):
    assert len(ports[name]["bits"]) == 512
declarations = []
for name, port in ports.items():
    assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
    width = len(port["bits"])
    dimension = f"[{width - 1}:0] " if width > 1 else ""
    declarations.append(f"  {port['direction']} wire {dimension}{name}")
connections = [f"    .{name}({name})" for name in ports]
(root / "top.v").write_text(
    "module llhd_vec_harness (\n" + ",\n".join(declarations) + ");\n"
    "  vec_engine u_vec (\n" + ",\n".join(connections) + ");\nendmodule\n"
)
lef = result / "vec_engine.lef"
lib = result / "vec_engine_typ.lib"
text = lef.read_text()
match = re.search(r"\bSIZE\s+([0-9.eE+-]+)\s+BY\s+([0-9.eE+-]+)\s*;", text)
assert match, "hardened LEF lacks macro SIZE"
width, height = (float(x) for x in match.groups())
origin = re.search(r"\bORIGIN\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s*;", text)
assert not origin or tuple(float(x) for x in origin.groups()) == (0.0, 0.0)
# Generous access channel; fixed location is checked again from the final ODB.
macro_x = 80.0
macro_y = 80.0
die_w, die_h = width + 160, height + 160
(root / "macro_place.tcl").write_text(
    "place_macro -macro_name u_vec -location {80 80} -orientation R0 -exact\n"
    "set block [ord::get_db_block]\nset inst [$block findInst u_vec]\n"
    "$inst setPlacementStatus FIRM\n"
)
(root / "top.sdc").write_text(
    "current_design llhd_vec_harness\ncreate_clock -name clk -period 3.0 [get_ports clk]\n"
    "set non_clock_inputs [lsearch -inline -all -not -exact [all_inputs] clk]\n"
    "set_input_delay 0.6 -clock clk $non_clock_inputs\n"
    "set_output_delay 0.6 -clock clk [all_outputs]\n"
)
(root / "top-config.mk").write_text(
    "export DESIGN_NICKNAME = llhd_vec_harness\nexport DESIGN_NAME = llhd_vec_harness\n"
    "export PLATFORM = nangate45\n"
    f"export VERILOG_FILES = {root / 'top.v'}\nexport SDC_FILE = {root / 'top.sdc'}\n"
    f"export ADDITIONAL_LEFS = {lef}\nexport ADDITIONAL_LIBS = {lib}\n"
    f"export ADDITIONAL_GDS = {result / '6_final.gds'}\n"
    f"export DIE_AREA = 0 0 {die_w:.6f} {die_h:.6f}\n"
    f"export CORE_AREA = 10 10 {die_w-10:.6f} {die_h-10:.6f}\n"
    f"export MACRO_PLACEMENT_TCL = {root / 'macro_place.tcl'}\n"
    "export PLACE_DENSITY = 0.30\nexport TNS_END_PERCENT = 100\n"
    "export SYNTH_HIERARCHICAL = 0\nexport LEC_CHECK = 0\n"
    f"export POST_FINAL_REPORT_TCL = {root / 'report_top_timing.tcl'}\n"
)
(root / "harness-contract.json").write_text(json.dumps({
    "kind": "direct engineering harness, not llaccel_core",
    "latency_added_cycles": 0,
    "block": str(block),
    "macro_master": "vec_engine",
    "macro_instance": "u_vec",
    "macro_origin_um": [macro_x, macro_y],
    "orientation": "R0",
    "dimensions_um": [width, height],
    "ports": {name: {"direction": p["direction"], "width": len(p["bits"])} for name, p in ports.items()},
    "timing_assumption": "3 ns clock and 0.6 ns top IO budget; no system signoff claim",
}, indent=2))
