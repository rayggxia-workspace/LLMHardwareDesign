#!/usr/bin/env python3
"""Replay the accepted #195 mother/local-controller fixtures with the new P/U groups."""
import hashlib
import os
from pathlib import Path
import shutil
import re
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
                .e_cmd_sources(cmd_sources[1:0]),.e_cmd_op(cmd_meta[3:0]),.e_cmd_shift(cmd_meta[8:4]),
                .e_cmd_src(cmd_addresses[29:0]),.e_cmd_dst(cmd_dst[9:0]),
                .e_done_valid(done_valid[0]),.e_done_ready(done_ready[0]),
                .e_done_error(done_error[0]),.e_done_saturated(done_saturated[0]),.e_done_data(),
                .e_cmd_direct_a(1'b0),.e_direct_a_valid(1'b0),.e_direct_a_abort(1'b0),
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


if len(sys.argv) > 3:
    from controlled import stage

    group = sys.argv[3]
    if group not in {"P", "U"}:
        raise ValueError(group)
    kind = 3 if group == "P" else 0
    directory, top = stage(run, group)
    compact = os.environ.get("PU_INSTRUCTION_BITS", "128") == "64"
    if compact:
        from compact64 import controller64, stage_fetch
        stage_fetch(design)
        shutil.copyfile(Path(__file__).with_name("compact64.py"), design / "compact64.py")
        reference = run / "staged/project/control_rtl_min_v0_1"
        stage_fetch(reference)
        for controller in ("mc_min_controller.sv", "lc_min_controller.sv"):
            file = reference / controller
            file.write_text(controller64(file.read_text()))
    for name in (f"{top}.sv", "pu_native_lc.sv"):
        shutil.copyfile(directory / name, design / name)
    if group == "P":
        shutil.copyfile(directory / "pj_native_service.sv", design / "pu_p_native_service.sv")
    else:
        shutil.copyfile(src / "project/rtl/pu_leaf_base/pu_u_direct_pair.sv", design / "pu_u_direct_pair.sv")
    controller_dir = run / "staged/project/control_rtl_min_v0_1"
    fixture = controller_dir / "tb_network_lc_wires.svh"
    declarations, instance = fixture.read_text().split("lc_min_controller #", 1)
    (design / "pu_lc_wires.svh").write_text(declarations)
    (design / "pu_legacy_lc.svh").write_text("lc_min_controller #" + instance)
    text = u.read_text()
    text = text.replace(
        '`include "tb_network_lc_wires.svh"',
        '`include "pu_lc_wires.svh"\n'
        f'    if (KIND!={kind}) begin: legacy_lc\n'
        '`include "pu_legacy_lc.svh"\n'
        '    end',
    )
    control_ports = []
    for line in (directory / "ports.svh").read_text().splitlines():
        name = re.search(r"(\w+),?$", line.strip()).group(1)
        if name.startswith(("svc_", "trace_")) or name in {"clk_i", "rst_ni"}:
            continue
        control_ports.append(f"            .{name}")
    p_binding = """
    if (KIND==3) begin: programmable_p
        wire route_valid, route_take;
        wire [31:0] route_data;
        wire [1:0] request_ready, response_valid;
        wire [255:0] response_data;
        assign seed_ready=request_ready[0];
        assign seed_ack=response_valid[0];
        assign check_valid=response_valid[1];
        assign check_data=response_data[255:128];
        assign {outgoing_valid,outgoing_addr,outgoing_data,outgoing_ack_ready,
                incoming_ready,incoming_ack,link_rx_reserved,link_rx_addr,tx_take}=0;
        pu_p_controlled implementation(
            .block_id_i(BLOCK),.topology_id_i(TOPOLOGY_ID),
            .clk(clk_i),.rst_ni,.late_path_enable(1'b1),
            .m_to_g_valid(route_valid),.m_to_g_data(route_data),.m_to_g_take(route_take),
            .g_from_m_valid(route_valid),.g_from_m_data(route_data),.g_from_m_take(route_take),
            .io_req_valid({check_read,seed_valid}),.io_req_write(2'b01),
            .io_req_addr({check_addr,seed_addr}),.io_req_data({128'b0,seed_data}),
            .io_rsp_ready({check_take,1'b1}),.io_req_ready(request_ready),
            .io_rsp_valid(response_valid),.io_rsp_data(response_data),
""" + ",\n".join(control_ports) + ");\n    end else if (KIND<3) begin: ucf"
    u_binding = """
    if (KIND==0) begin: programmable_u
        wire route_valid, route_ready;
        wire [127:0] route_data;
        wire data_ready, data_stored;
        assign seed_ready=seed_mode && data_ready;
        assign seed_ack=seed_mode && data_stored;
        assign incoming_ready=!seed_mode && data_ready;
        assign incoming_ack=!seed_mode && data_stored;
        assign check_valid=0;
        assign check_data=0;
        assign tx_valid=0;
        assign tx_data=0;
        assign tx_take=outgoing_ack && outgoing_ack_ready;
        pu_u_controlled implementation(
            .block_id_i(BLOCK),.topology_id_i(TOPOLOGY_ID),
            .clk(clk_i),.rst_ni,.late_path_enable(1'b1),
            .n_to_e_valid(route_valid),.n_to_e_data(route_data),.n_to_e_ready(route_ready),
            .e_direct_a_valid(route_valid),.e_direct_a_data(route_data),.e_direct_a_ready(route_ready),
            .incoming_valid(seed_mode ? seed_valid : incoming_valid),.incoming_ready(data_ready),
            .incoming_addr(seed_mode ? seed_addr : incoming_addr),.incoming_data(seed_mode ? seed_data : incoming_data),
            .incoming_ack(data_stored),.incoming_ack_ready(seed_mode || incoming_ack_ready),
            .outgoing_valid,.outgoing_ready,.outgoing_addr,.outgoing_data,.outgoing_ack,.outgoing_ack_ready,
            .link_rx_reserved,.link_rx_addr,.peer_rx_reserved,.peer_rx_addr,
""" + ",\n".join(control_ports) + ");\n    end else if (KIND<3) begin: ucf"
    binding = p_binding if group == "P" else u_binding
    if text.count("    if (KIND<3) begin: ucf") != 1:
        raise ValueError("P replay generate anchor drift")
    text = text.replace("    if (KIND<3) begin: ucf", binding)
    if compact:
        text = text.replace(f"pu_{group.lower()}_controlled implementation(", f"{top} implementation(")
    release = "        forever begin\n            @(negedge clk_i); release_valid_i=1;"
    if text.count(release) != 1:
        raise ValueError("release ready fixture anchor drift")
    text = text.replace(release, f"        forever begin\n            if (KIND=={kind}) wait(release_ready_o);\n"
                         "            @(negedge clk_i); release_valid_i=1;")
    u.write_text(text)

    image = design / "images.py"
    text = image.read_text()
    if group == "P":
        old = "                dict(native_op=0x112, native0=12 | 13 << 10 | 14 << 20)],"
        if text.count(old) != 1:
            raise ValueError("P direct image anchor drift")
        image.write_text(text.replace(old, """
                    dict(native_op=0x111, native0=5 | 1 << 22, native1=0x101),
                    dict(native_op=0x112, native0=12 | 13 << 10 | 14 << 20 | 1 << 30)],"""))
        bench = design / "tb_native_pair.sv"
        text = bench.read_text()
        if text.count("verify(14,128'd5000)") != 1:
            raise ValueError("P direct expected-result anchor drift")
        bench.write_text(text.replace("verify(14,128'd5000)", "verify(14,128'hfffb0002)"))
    else:
        old = "command(1, 2), command(1, 0x85, (u_in, u_gamma), u_out),"
        if text.count(old) != 1:
            raise ValueError("U direct image anchor drift")
        image.write_text(text.replace(old, """command(1, 2),
         dict(native_op=0x104, native0=2, native1=u_in | u_gamma << 10,
              native2=0x85, native4=u_out << 9, native5=22),"""))
        bench = design / "tb_native_pair.sv"
        text = bench.read_text()
        if text.count("seed(1,21,128'd1);") != 1:
            raise ValueError("U direct zero-seed anchor drift")
        bench.write_text(text.replace("seed(1,21,128'd1);", "seed(1,21,128'd1); seed(1,22,0);"))
    runner = design / "run.sh"
    text = runner.read_text()
    text = text.replace('-I"$ctrl" -I"$native"', '-I"$ctrl" -I"$native" -I"$base/design"')
    text = text.replace("--binary --timing --assert", "--binary --timing --assert --x-initial unique --x-assign unique")
    start = '  "${runtime[@]}" "./obj/Vtb_native_pair"'
    end = '"+RESET_TRIAL=$reset_trial"'
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError("three-initial-state replay anchor drift")
    text = text.replace(start, '  for initial_seed in 1:143 2:143 2:144; do\n' + start)
    text = text.replace(end, end + ' \\\n    "+verilator+rand+reset+${initial_seed%:*}" "+verilator+seed+${initial_seed#*:}"\n  done')
    runner.write_text(text)

    if os.environ.get("PU_E_COUNT_REPLAY") == "1":
        if group != "U":
            raise ValueError("E operand-count replay requires the U controlled fixture")
        text = image.read_text()
        anchor = "dict(native_op=SEND, native0=u_out | c_return << 10)"
        if text.count(anchor) != 1:
            raise ValueError("E count image anchor drift")
        image.write_text(text.replace(anchor,
            "command(0, 3, (23, 24), u_out),\n         " + anchor))
        text = bench.read_text()
        replacements = {
            "seed(1,22,0);": "seed(1,22,0); seed(1,0,{8{16'd5}}); "
                "seed(1,23,{8{16'd2}}); seed(1,24,{8{16'd3}});",
            "(fault!=0 ? 48 : 80)": "(fault!=0 ? 64 : 96)",
            "verify(41,INPUT_WORD)": "verify(41,{8{16'd6}})",
            "fault!=0 ? SENTINEL : RESULT_WORD": "fault!=0 ? SENTINEL : {4{32'hfc060406}}",
        }
        for anchor, replacement in replacements.items():
            if text.count(anchor) != 1:
                raise ValueError("E count bench anchor drift: " + anchor)
            text = text.replace(anchor, replacement)
        bench.write_text(text)

    if compact:
        text = image.read_text()
        old = "from run_a2 import assemble, mem"
        if text.count(old) != 1:
            raise ValueError("compact assembler anchor drift")
        image.write_text(text.replace(old,
            "from run_a2 import assemble as assemble128, mem\n"
            "    from compact64 import compact_image\n"
            "    import os\n"
            "    def assemble(*a, **kw):\n"
            "        if os.environ.get('PU_REPLAY_EVEN') == '1' and len(a[1]) % 2:\n"
            "            a = list(a)\n"
            "            a[1] = list(a[1])\n"
            "            a[1].insert(0, dict(op='L_MOVI' if a[0]=='local' else 'G_MOVI', a=7, x=0x12345678))\n"
            "            a[2] = dict(a[2])\n"
            "            if 'task' in a[2]:\n"
            "                a[2]['task'] = [dict(t, max_steps=t['max_steps']+1) for t in a[2]['task']]\n"
            "        raw = assemble128(*a, **kw)\n"
            "        return raw if os.environ.get('PU_REPLAY_LEGACY') == '1' else compact_image(raw)"))
