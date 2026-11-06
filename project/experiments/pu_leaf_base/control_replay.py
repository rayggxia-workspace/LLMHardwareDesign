#!/usr/bin/env python3
"""Replay the accepted #195 mother/local-controller fixtures with the new P/U groups."""
import hashlib
from pathlib import Path
import shutil
import sys

src = Path(sys.argv[1]).resolve()
run = Path(sys.argv[2]).resolve()
prior = Path("/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-193-local-control/acceptance-02")
locks = {
    "design/tb_native_local.sv": "661de91135c9a13baf367c17a263b4cb3520fe2ff3cc4c75584f42df6c1ebd12",
    "design/tb_pj_endpoint.sv": "1c0af2fc21e8bbf0329bcf8a4a388d45a1fa33fa48bc85a33ce52a25792540e2",
    "design/run.sh": "76761e268c31fa52914f23350376d2dacc3bd500c5d96eb3ef20283605fd4606",
    "staged/sources.json": "e203596fa7459733732d77de231ec7611692bf7503d78dd64cb6fcd2366067b3",
}
for name, expected in locks.items():
    if hashlib.sha256((prior / name).read_bytes()).hexdigest() != expected:
        raise ValueError(f"control baseline changed: {name}")
run.mkdir()
for folder in ("design", "staged"):
    shutil.copytree(prior / folder, run / folder)
design = run / "design"
native = run / "staged/native"

for name in ("pu_p_group", "pu_p_store_control", "pu_u_group", "pu_compact_e_service"):
    shutil.copyfile(src / f"project/rtl/pu_leaf_base/{name}.sv", design / f"{name}.sv")
for name in ("local_s_base", "local_s_p", "block_feed_s16k_sram"):
    shutil.copyfile(src / f"project/rtl/s_sram/{name}.sv", native / f"{name}.sv")
shutil.copyfile(src / "project/rtl/block_v2/block_v2_e_compact.sv", native / "block_v2_e_compact.sv")

p = design / "tb_pj_endpoint.sv"
text = p.read_text()
if text.count("block_p16 block(") != 1:
    raise ValueError("P fixture anchor drift")
p.write_text(text.replace("block_p16 block(", "pu_p_group block("))

u = design / "tb_native_local.sv"
text = u.read_text()
start = text.index("        block_ucf16 #(.KIND(KIND)) block(")
end = text.index("        stored_link transport", start)
original = text[start:end].strip()
compact = """
        if (KIND==0) begin: compact
            wire [127:0] ignored_rx;
            pu_u_group block(.clk(clk_i),.reset(!rst_ni),
                .n_cmd_valid(cmd_valid[1]),.n_cmd_ready(cmd_ready[1]),.n_cmd_store(cmd_store[1]),.n_cmd_direct(1'b0),
                .n_cmd_meta(cmd_meta[103:64]),.n_cmd_sources(cmd_sources[3:2]),
                .n_cmd_src(cmd_addresses[49:30]),.n_cmd_dst(cmd_dst[19:10]),
                .n_done_valid(done_valid[1]),.n_done_ready(done_ready[1]),
                .n_done_error(done_error[1]),.n_done_saturated(done_saturated[1]),.n_done_data(),
                .n_to_e_valid(),.n_to_e_data(),.n_to_e_ready(1'b0),
                .e_cmd_valid(cmd_valid[0]),.e_cmd_ready(cmd_ready[0]),.e_cmd_store(cmd_store[0]),
                .e_cmd_op(cmd_meta[3:0]),.e_cmd_shift(cmd_meta[8:4]),
                .e_cmd_src(cmd_addresses[29:0]),.e_cmd_dst(cmd_dst[9:0]),
                .e_done_valid(done_valid[0]),.e_done_ready(done_ready[0]),
                .e_done_error(done_error[0]),.e_done_saturated(done_saturated[0]),.e_done_data(),
                .e_cmd_direct_a(1'b0),.e_direct_a_valid(1'b0),
                .e_direct_a_ready(),.e_direct_a_data(128'b0),
                .io_req_valid({tx_req || check_read,seed_mode ? seed_valid : incoming_valid}),
                .io_req_write(2'b01),
                .io_req_addr({check_read ? check_addr : tx_addr,seed_mode ? seed_addr : incoming_addr}),
                .io_req_data({128'b0,seed_mode ? seed_data : incoming_data}),
                .io_req_ready({tx_ready,rx_ready}),.io_rsp_valid({tx_valid,rx_stored}),
                .io_rsp_ready({tx_take || check_take,seed_mode || incoming_ack_ready}),
                .io_rsp_data({tx_data,ignored_rx}));
        end else begin: reference
            """ + original + """
        end

"""
u.write_text(text[:start] + compact + text[end:])
