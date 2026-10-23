"""Independent full GEMM and openTPU small ACT/MXU physical experiments."""
import importlib.util
import json
import os
from pathlib import Path
import sys

root = Path.cwd()
source = root / "source"
case = os.environ["LLHD_CASE"]
cap_margin = os.environ.get("LLHD_CAP_MARGIN")
if cap_margin is not None:
    assert cap_margin in ("0", "10", "20"), cap_margin

ACT_WRITE = """input logic [3:0] we,
  input logic [7:0] w_row,
  input logic [31:0] w_idx,
  input logic [3:0][7:0] w_data,
  input logic w_dup,
  input logic [7:0] w_off,
  input logic swe,
  input logic [7:0] s_row,
  input logic [15:0] s_blk,
  input logic [63:0] s_data"""
ACT_READ = """input logic [1:0] ren,
  input logic r_use,
  input logic [15:0] r_blk, r_blk2,
  input logic [1:0] r_hi,
  input logic [7:0] r_grp,
  output wire [511:0] r_data,
  output wire [127:0] r_scale"""
MXU_EXT = """input logic rst, start, go,
  input cmd_t cmd,
  output logic rdy, done, computing,
  output logic [6:0] pf_level,
  output logic pf_starve, pf_block, pf_u,
  output logic [3:0][31:0] pf_uv,
  output logic a_req,
  output logic [31:0] a_addr,
  input logic a_gnt, a_rvalid,
  input logic [255:0] a_rdata,
  output logic b_req,
  output logic [31:0] b_addr,
  input logic b_gnt, b_rvalid,
  input logic [255:0] b_rdata,
  output logic [3:0] t_ren,
  output logic [3:0][31:0] t_raddr,
  input logic [3:0][31:0] t_rdata,
  output logic [3:0] t_wen,
  output logic [3:0][31:0] t_waddr, t_wdata,
  input logic t_gnt"""
MXU_ACT = """output logic [15:0] act_blk, act_blk2,
  output logic [1:0] act_hi,
  output logic [7:0] act_grp,
  output logic [1:0] act_ren,
  input logic [511:0] act_data,
  input logic [127:0] act_scale"""
ACT_INSTANCE = """otpu_actram #(.D(32), .MCOLS(2), .ROWS(2), .BLOCKS(32), .LANES(4)) u_act (
    .clk, .we, .w_row, .w_idx, .w_data, .w_dup, .w_off, .swe, .s_row, .s_blk, .s_data,
    .ren(REN), .r_use(USE), .r_blk(BLK), .r_blk2(BLK2), .r_hi(HI), .r_grp(GRP),
    .r_data(DATA), .r_scale(SCALE));"""
MXU_INSTANCE = """otpu_mxu #(.D(32), .MCOLS(2), .ROWS(2), .DEPTH(64), .LANES(4),
    .IMPL(2), .CL(16), .E(0), .SID(0)) u_mxu (
    .clk, .rst, .start, .go, .cmd, .rdy, .done, .computing, .pf_level,
    .pf_starve, .pf_block, .pf_u, .pf_uv,
    .act_blk, .act_blk2, .act_hi, .act_grp, .act_ren, .act_data, .act_scale,
    .a_req, .a_addr, .a_gnt, .a_rvalid, .a_rdata,
    .b_req, .b_addr, .b_gnt, .b_rvalid, .b_rdata,
    .t_ren, .t_raddr, .t_rdata, .t_wen, .t_waddr, .t_wdata, .t_gnt);"""


def act_instance(merged):
    mapping = dict(REN="act_ren", USE="computing", BLK="act_blk", BLK2="act_blk2",
                   HI="act_hi", GRP="act_grp", DATA="act_data", SCALE="act_scale")
    if not merged:
        mapping = dict(REN="ren", USE="r_use", BLK="r_blk", BLK2="r_blk2",
                       HI="r_hi", GRP="r_grp", DATA="r_data", SCALE="r_scale")
    text = ACT_INSTANCE
    # Replace longer tokens first (BLK2 before BLK).
    import re
    return re.sub(r"\b(?:" + "|".join(mapping) + r")\b", lambda m: mapping[m[0]], text)


extra_config = ""
if case == "llaccel-gemm":
    top = "gemm_engine"
    period = 3.0
    delay = 0.6
    rtl = source / "rtl"
    files = [rtl / n for n in ["llaccel_pkg.sv", "llaccel_luts_pkg.sv", "sync_fifo.sv",
                              "gemm_engine.sv", "llaccel_luts_undef.sv"]]
    frontend = "read_slang -D SYNTHESIS -I" + str(rtl) + " --top " + top
    memory_note = "Original llaccel fixed v1 EPILOGUE_FUSION=0, no SRAM bank storage; original RTL inferred memories."
    params = {"EPILOGUE_FUSION": 0, "GEMM_TN": 16, "GEMM_TK": 16, "GEMM_TM": 16}
else:
    sys.path[:0] = [str(source / "tools" / "asic"), str(source)]
    import flow as F
    from opentpu import target as T
    actual = F.params("small")
    for key, value in dict(D=32, MCOLS=2, ACT_ROWS=2, ACT_BLOCKS=32, ULANES=4,
                           FIFO_DEPTH=64, MXU_IMPL=2, MXU_CL=16).items():
        assert actual[key] == value, (key, actual[key], value)
    params = {"D": 32, "MCOLS": 2, "ROWS": 2, "BLOCKS": 32, "LANES": 4,
              "DEPTH": 64, "IMPL": 2, "CL": 16, "E": 0, "SID": 0}
    top = "otpu_asic_top"  # F.probe's fixed top, only our wrapper is compiled with this name.
    period = F.clock_ns("small")
    assert period == 2.5
    delay = 0.2 * period
    if case == "opentpu-act":
        ports = "input logic clk,\n  " + ACT_WRITE + ",\n  " + ACT_READ
        body = act_instance(False)
    elif case == "opentpu-mxu":
        ports = "input logic clk,\n  " + MXU_EXT + ",\n  " + MXU_ACT
        body = MXU_INSTANCE
    elif case == "opentpu-act-mxu":
        ports = "input logic clk,\n  " + ACT_WRITE + ",\n  " + MXU_EXT
        body = """logic [15:0] act_blk, act_blk2;
  logic [1:0] act_hi, act_ren;
  logic [7:0] act_grp;
  wire [511:0] act_data;
  wire [127:0] act_scale;
  """ + act_instance(True) + "\n  " + MXU_INSTANCE
    else:
        raise ValueError(case)
    wrapper = root / "boundary.sv"
    wrapper.write_text("// Fixed small parameters; source RTL unchanged.\n"
                       "module otpu_asic_top import otpu_pkg::*; (\n  " + ports + ");\n  " + body + "\nendmodule\n")
    files = [source / "rtl" / f for f in T.sources("nangate45-small")] + [wrapper]
    assert all(p.name != "otpu_asic_top.sv" for p in files)
    # Reuse the upstream exact-revision ASIC macro generator, probing OUR wrapper only.
    # Generated files are placed in this new attempt, never in the source repository.
    model_dir = root / "memory-model"
    (model_dir / "src").mkdir(parents=True)
    F.out_dir = lambda _: model_dir
    F.sources = lambda _: files
    F.params = lambda _: {}
    macros = F.probe("small")
    for macro in macros:
        F.fakeram.write(macro, model_dir / "macros")
    mapped = model_dir / "src" / "otpu_sram_map.sv"
    mapped.write_text(F.sram_map(macros))
    if os.environ.get("LLHD_UNIQUE_TOP") == "1":
        top = "llhd_" + case.replace("-", "_")
        original = wrapper.read_text()
        assert original.count("module otpu_asic_top ") == 1
        wrapper.write_text(original.replace("module otpu_asic_top ", "module " + top + " ", 1))
    files += [mapped] + [model_dir / "macros" / (m.name + "_bb.v") for m in macros]
    lefs = " ".join(str(model_dir / "macros" / (m.name + ".lef")) for m in macros)
    libs = " ".join(str(model_dir / "macros" / (m.name + ".lib")) for m in macros)
    extra_config = (f"export ADDITIONAL_LEFS = {lefs}\nexport ADDITIONAL_LIBS = {libs}\n"
                    f"export TAPCELL_TCL = {source / 'asic/nangate45/tapcell.tcl'}\n"
                    "export MACRO_PLACE_HALO = 10 10\nexport RTLMP_MIN_CHANNEL_SIZE = 60 60\n"
                    "export CORE_MARGIN = 5\n")
    frontend = "read_slang -D SYNTHESIS --ignore-assertions --top " + top
    memory_note = ("Upstream openTPU synthetic fakeram LEF/Liberty models, not fabricated SRAM or SRAM GDS. "
                   "Same unmodified generator and small configuration for split/merged cases; no full system claim.")

commands = [frontend + " " + " ".join(map(str, files)),
            "hierarchy -check -top " + top, "proc", "flatten", "opt -full", "memory -nomap",
            "opt_clean", "bwmuxmap", "check -assert", "stat",
            "write_verilog -noattr -nohex " + str(root / "elab.v"),
            "write_json " + str(root / "elab.json")]
(root / "elab.ys").write_text("\n".join(commands) + "\n")
(root / "boundary.sdc").write_text(
    f"current_design {top}\ncreate_clock -name clk -period {period} [get_ports clk]\n"
    "set non_clock_inputs [lsearch -inline -all -not -exact [all_inputs] clk]\n"
    f"set_input_delay {delay} -clock clk $non_clock_inputs\n"
    f"set_output_delay {delay} -clock clk [all_outputs]\n")
(root / "config.mk").write_text(
    f"export DESIGN_NICKNAME = parallel_{case.replace('-', '_')}\nexport DESIGN_NAME = {top}\n"
    "export PLATFORM = nangate45\n"
    f"export VERILOG_FILES = {root / 'elab.v'}\nexport SDC_FILE = {root / 'boundary.sdc'}\n"
    "export CORE_UTILIZATION = 35\nexport PLACE_DENSITY = 0.55\n"
    "export TNS_END_PERCENT = 100\nexport SYNTH_HIERARCHICAL = 0\nexport ABC_AREA = 0\n"
    "export SKIP_GATE_CLONING = 0\nexport SYNTH_ARGS = -noshare\n"
    "export SYNTH_MEMORY_MAX_BITS = 16384\nexport LEC_CHECK = 0\n" + extra_config
    + ("export CAP_MARGIN = " + cap_margin + "\n" if cap_margin is not None else ""))
(root / "experiment.json").write_text(json.dumps({
    "case": case, "top": top, "parameters": params, "clock_ns": period, "io_delay_ns": delay,
    "cap_margin": int(cap_margin) if cap_margin is not None else None,
    "source_rtl_modified": False, "added_registers": 0, "phase_lec": "explicitly disabled physical-only route",
    "memory_model": memory_note, "external_driver_load_model": "not specified; boundary timing budget only",
    "scope": "independent block implementation; not top integration, H2, source-to-netlist equivalence or signoff"
}, indent=2) + "\n")
