"""Render a full-width original VECTOR hardening baseline, without RTL edits."""
from pathlib import Path
import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--screening", action="store_true")
args = parser.parse_args()
root = Path.cwd()
source = root / "source"
rtl = source / "rtl"
files = [
    "llaccel_pkg.sv", "llaccel_luts_pkg.sv", "sync_fifo.sv", "isqrt.sv", "udiv.sv",
    "vec_engine.sv", "llaccel_luts_undef.sv",
]
commands = [
    "read_slang -I" + str(rtl) + " --top vec_engine " + " ".join(str(rtl / name) for name in files),
    "hierarchy -check -top vec_engine", "proc", "flatten", "opt -full",
    "memory -nomap", "opt_clean", "bwmuxmap", "check -assert", "stat",
    "write_verilog -noattr -nohex " + str(root / "vec-elab.v"),
    "write_json " + str(root / "vec-elab.json"),
]
(root / "vec-elab.ys").write_text("\n".join(commands) + "\n")
(root / "vec.sdc").write_text(
    "current_design vec_engine\ncreate_clock -name clk -period 3.0 [get_ports clk]\n"
    "set non_clock_inputs [lsearch -inline -all -not -exact [all_inputs] clk]\n"
    "set_input_delay 0.6 -clock clk $non_clock_inputs\n"
    "set_output_delay 0.6 -clock clk [all_outputs]\n"
)
(root / "vec-config.mk").write_text(
    "export DESIGN_NICKNAME = llhd_vec_original\nexport DESIGN_NAME = vec_engine\n"
    "export PLATFORM = nangate45\n"
    f"export VERILOG_FILES = {root / 'vec-elab.v'}\n"
    f"export SDC_FILE = {root / 'vec.sdc'}\n"
    "export CORE_UTILIZATION = 35\nexport PLACE_DENSITY = 0.55\n"
    "export TNS_END_PERCENT = 100\nexport SYNTH_HIERARCHICAL = 0\n"
    "export ABC_AREA = 0\nexport SKIP_GATE_CLONING = 0\n"
    "export SYNTH_ARGS = -noshare\nexport SYNTH_MEMORY_MAX_BITS = 16384\n"
)
