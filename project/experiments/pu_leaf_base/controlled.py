#!/usr/bin/env python3
"""Stage the pinned #195 controller and bind it to the P/U native services."""

import hashlib
from pathlib import Path
import re
import shutil

BASE = Path("/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-193-local-control/acceptance-02")
CORE = "staged/project/control_rtl_min_v0_1/"
SOURCES = {
    CORE + "lc_min_controller.sv": "08c84235b661964e8dc3ede585e950113f2830aec8b11a10c5ee61f4723c3341",
    CORE + "ports.svh": "bbbfc288dca616e2876b4c6237f94e118aa7aa7a1f5d250cd4fd06aa1e2bc4b2",
    CORE + "m_dot_store_desc.svh": "4d0fa9dc38d530651162c4f2a5e60493cc28bfdd429b2ed86c68dd0600655ace",
    CORE + "f_store_desc.svh": "50aa47dda5351973133841c0ffc617dde01ca4a82b5b4f78c9358e17d99087c8",
    CORE + "u_rms_desc.svh": "98a8dd29b0fccb53078e72ae2084237d7d264eb45ad4868f25e48fa3abb50b86",
    "design/pj_native_service.sv": "67feffb4ae2a9c20ab94a3c7a780b123d6b6eda64e0d80e5588162eaf3835e73",
    "design/ucf_native_service.sv": "60240e9ecc6e92576b33d528618abba46153f092d553e2295bfe4324aa04fd45",
    "design/stored_link.sv": "7a852eebeb6988b2dc448bec9f4dfd48cdad56728c7ad07633008ed614c15571",
}

P_ENDPOINT = """
    wire load_valid,load_take,cmd_valid,cmd_take,gate_valid,gate_take;
    wire load_ready,load_done,load_error,cmd_ready,cmd_done,cmd_error,cmd_saturated;
    wire gate_ready,gate_done,gate_error,gate_saturated;
    wire [31:0] load_fields,cmd_fields;
    wire [63:0] cmd_data;
    wire [30:0] gate_fields;
    pu_p_native_service adapter(.late_path_enable,.clk,.reset,.svc_valid,.svc_ready,.descriptor,.rsp_valid,.rsp_ready,
        .status,.saturated,.read_bytes,.write_bytes,
        .load_valid,.load_ready,.load_take,.load_done,.load_error,.load_fields,
        .cmd_valid,.cmd_ready,.cmd_take,.cmd_done,.cmd_error,.cmd_saturated,.cmd_fields,.cmd_data,
        .gate_valid,.gate_ready,.gate_take,.gate_done,.gate_error,.gate_saturated,.gate_fields,
        .start(),.start_ready(1'b0),.done_take(),.done_valid(1'b0),.done_error(1'b0),
        .join_tag(),.join_fields(),.release_valid(),.release_ready(1'b0));
    pu_p_group datapath(.clk,.reset,.io_req_valid,.io_req_write,.io_req_addr,.io_req_data,
        .io_req_ready,.io_rsp_valid,.io_rsp_ready,.io_rsp_data,
        .load_valid,.load_ready,.load_done,.load_take,.load_error,
        .load_bank(load_fields[0]),.load_rows(load_fields[4:1]),.load_tiles(load_fields[7:5]),
        .load_a_wide(load_fields[8]),.load_b_wide(load_fields[9]),.load_reuse_b(load_fields[10]),
        .load_a_base(load_fields[20:11]),.load_b_base(load_fields[30:21]),
        .cmd_valid,.cmd_ready,.cmd_op(cmd_fields[3:0]),.cmd_index(cmd_fields[9:4]),.cmd_data,
        .cmd_store(cmd_fields[10]),.cmd_route(cmd_fields[22]),.cmd_pack16(cmd_fields[11]),.cmd_dst(cmd_fields[21:12]),
        .cmd_done,.cmd_take,.cmd_error,.cmd_saturated,.cmd_result(),
        .gate_valid,.gate_route(gate_fields[30]),.gate_ready,.gate_a(gate_fields[9:0]),
        .gate_b(gate_fields[19:10]),.gate_dst(gate_fields[29:20]),
        .gate_done,.gate_take,.gate_error,.gate_saturated,
        .m_to_g_valid,.m_to_g_data,.m_to_g_take,
        .g_from_m_valid,.g_from_m_data,.g_from_m_take);
"""

U_ENDPOINT = """
    wire [1:0] cmd_valid, cmd_store, done_ready, cmd_ready, done_valid, done_error, done_saturated;
    wire [127:0] cmd_meta, tx_data;
    wire [3:0] cmd_sources;
    wire [59:0] cmd_addresses;
    wire [19:0] cmd_dst;
    wire tx_ready, tx_valid, tx_req, tx_take;
    wire [9:0] tx_addr, source_addr, destination_addr;
    wire send_start, send_ready, send_done;
    wire [127:0] unused_rx;
    wire pair_selected = pair_active || (svc_valid && descriptor[32+:16]==16'h104);
    reg pair_active;
    wire pair_ready, pair_rsp, pair_saturated, pair_abort;
    wire normal_ready, normal_rsp, normal_saturated;
    wire [15:0] pair_status, normal_status;
    wire [31:0] pair_reads, pair_writes, normal_reads, normal_writes;
    wire [1:0] pair_cmd, pair_store, pair_take, normal_cmd, normal_store, normal_take;
    wire [127:0] pair_meta, normal_meta;
    wire [3:0] pair_sources, normal_sources;
    wire [59:0] pair_addresses, normal_addresses;
    wire [19:0] pair_dst, normal_dst;
    assign svc_ready = pair_selected ? pair_ready : normal_ready;
    assign rsp_valid = pair_active ? pair_rsp : normal_rsp;
    assign status = pair_active ? pair_status : normal_status;
    assign saturated = pair_active ? pair_saturated : normal_saturated;
    assign read_bytes = pair_active ? pair_reads : normal_reads;
    assign write_bytes = pair_active ? pair_writes : normal_writes;
    assign cmd_valid = pair_active ? pair_cmd : normal_cmd;
    assign cmd_store = pair_active ? pair_store : normal_store;
    assign done_ready = pair_active ? pair_take : normal_take;
    assign cmd_meta = pair_active ? pair_meta : normal_meta;
    assign cmd_sources = pair_active ? pair_sources : normal_sources;
    assign cmd_addresses = pair_active ? pair_addresses : normal_addresses;
    assign cmd_dst = pair_active ? pair_dst : normal_dst;
    always @(posedge clk) begin
        if (reset || (pair_rsp && rsp_ready)) pair_active <= 0;
        else if (pair_selected && svc_valid && pair_ready) pair_active <= 1;
    end
    pu_u_direct_pair pair_service(.clk,.reset,.enable(late_path_enable),
        .svc_valid(svc_valid && pair_selected && !pair_active),.svc_ready(pair_ready),.descriptor,
        .rsp_valid(pair_rsp),.rsp_ready(rsp_ready && pair_active),
        .status(pair_status),.saturated(pair_saturated),.read_bytes(pair_reads),.write_bytes(pair_writes),
        .cmd_valid(pair_cmd),.cmd_store(pair_store),.done_ready(pair_take),
        .cmd_meta(pair_meta),.cmd_sources(pair_sources),.cmd_addresses(pair_addresses),.cmd_dst(pair_dst),
        .cmd_ready,.done_valid,.done_error,.done_saturated,.abort_direct_a(pair_abort));
    ucf_native_service adapter(.clk,.reset,.svc_valid(svc_valid && !pair_selected),
        .svc_ready(normal_ready),.descriptor,.rsp_valid(normal_rsp),.rsp_ready(rsp_ready && !pair_active),
        .status(normal_status),.saturated(normal_saturated),.read_bytes(normal_reads),.write_bytes(normal_writes),
        .cmd_valid(normal_cmd),.cmd_store(normal_store),.done_ready(normal_take),
        .cmd_ready,.done_valid,.done_error,.done_saturated,
        .cmd_meta(normal_meta),.cmd_sources(normal_sources),.cmd_addresses(normal_addresses),.cmd_dst(normal_dst),
        .send_start,.send_ready,.send_done,.source_addr,.destination_addr,
        .receive_commit(incoming_ack && incoming_ack_ready),
        .receive_reserved(link_rx_reserved),.receive_address(link_rx_addr));
    stored_link transport(.clk,.reset,.start(send_start),.ready(send_ready),.source_addr,.destination_addr,
        .done(send_done),.tx_req,.tx_ready,.tx_addr,.tx_valid,.tx_take,.tx_data,
        .rx_valid(outgoing_valid),.rx_ready(outgoing_ready),.rx_addr(outgoing_addr),.rx_data(outgoing_data),
        .rx_stored(outgoing_ack),.rx_stored_ready(outgoing_ack_ready),
        .sink_reserved(peer_rx_reserved && peer_rx_addr == outgoing_addr));
    pu_u_group datapath(.clk,.reset,
        .n_cmd_valid(cmd_valid[1]),.n_cmd_ready(cmd_ready[1]),.n_cmd_store(cmd_store[1]),.n_cmd_direct(pair_active),
        .n_cmd_meta(cmd_meta[103:64]),.n_cmd_sources(cmd_sources[3:2]),
        .n_cmd_src(cmd_addresses[49:30]),.n_cmd_dst(cmd_dst[19:10]),
        .n_done_valid(done_valid[1]),.n_done_ready(done_ready[1]),
        .n_done_error(done_error[1]),.n_done_saturated(done_saturated[1]),.n_done_data(),
        .n_to_e_valid,.n_to_e_data,.n_to_e_ready,
        .e_cmd_valid(cmd_valid[0]),.e_cmd_ready(cmd_ready[0]),.e_cmd_store(cmd_store[0]),
        .e_cmd_sources(cmd_sources[1:0]),.e_cmd_op(cmd_meta[3:0]),.e_cmd_shift(cmd_meta[8:4]),
        .e_cmd_src(cmd_addresses[29:0]),.e_cmd_dst(cmd_dst[9:0]),
        .e_done_valid(done_valid[0]),.e_done_ready(done_ready[0]),
        .e_done_error(done_error[0]),.e_done_saturated(done_saturated[0]),.e_done_data(),
        .e_cmd_direct_a(pair_active),.e_direct_a_valid,.e_direct_a_abort(pair_abort),.e_direct_a_ready,.e_direct_a_data,
        .io_req_valid({tx_req,incoming_valid}),.io_req_write(2'b01),
        .io_req_addr({tx_addr,incoming_addr}),.io_req_data({128'b0,incoming_data}),
        .io_req_ready({tx_ready,incoming_ready}),.io_rsp_valid({tx_valid,incoming_ack}),
        .io_rsp_ready({tx_take,incoming_ack_ready}),.io_rsp_data({tx_data,unused_rx}));
"""

P_PORTS = """
    input wire [1:0] io_req_valid, io_req_write, io_rsp_ready,
    input wire [19:0] io_req_addr,
    input wire [255:0] io_req_data,
    output wire [1:0] io_req_ready, io_rsp_valid,
    output wire [255:0] io_rsp_data,
    input wire late_path_enable,
    output wire m_to_g_valid,
    output wire [31:0] m_to_g_data,
    input wire m_to_g_take,
    input wire g_from_m_valid,
    input wire [31:0] g_from_m_data,
    output wire g_from_m_take
"""

U_PORTS = """
    output wire link_rx_reserved,
    output wire [9:0] link_rx_addr,
    input wire peer_rx_reserved,
    input wire [9:0] peer_rx_addr,
    output wire outgoing_valid,
    input wire outgoing_ready,
    output wire [9:0] outgoing_addr,
    output wire [127:0] outgoing_data,
    input wire outgoing_ack,
    output wire outgoing_ack_ready,
    input wire incoming_valid,
    output wire incoming_ready,
    input wire [9:0] incoming_addr,
    input wire [127:0] incoming_data,
    output wire incoming_ack,
    input wire incoming_ack_ready,
    input wire late_path_enable,
    output wire n_to_e_valid,
    output wire [127:0] n_to_e_data,
    input wire n_to_e_ready,
    input wire e_direct_a_valid,
    input wire [127:0] e_direct_a_data,
    output wire e_direct_a_ready
"""

CONTROL_LINK = {
    "svc_req_valid_o": "svc_valid",
    "svc_req_ready_i": "svc_ready",
    "svc_req_descriptor_o": "descriptor",
    "svc_rsp_valid_i": "rsp_valid",
    "svc_rsp_ready_o": "rsp_ready",
    "svc_rsp_status_i": "status",
    "svc_rsp_saturated_i": "saturated",
    "svc_rsp_read_bytes_i": "read_bytes",
    "svc_rsp_write_bytes_i": "write_bytes",
    "svc_rsp_kind_i": "2'b0",
}
IDENTITY_FIELDS = {"token": 3, "sequence": 32, "job": 32, "epoch": 32, "task_sequence": 32}


def stage(out, group):
    """Build an explicit LC/adapter netlist boundary, with program memory exposed."""
    directory = out / "lc"
    directory.mkdir()
    for name, expected in SOURCES.items():
        source = BASE / name
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError(f"controller baseline drift: {name}")
        shutil.copyfile(source, directory / source.name)

    baseline = directory / "lc_min_controller.sv"
    controller = baseline.read_text()
    for old, new in (
        ("module lc_min_controller #(parameter [7:0] BLOCK_ID = 0,",
         "module pu_native_lc #("),
        ("parameter [7:0] NATIVE_BLOCK_TYPE = 0,\n                           parameter [31:0] NATIVE_TOPOLOGY = 0) (",
         "parameter [7:0] NATIVE_BLOCK_TYPE = 0) (\n"
         "    input wire [7:0] block_id_i,\n"
         "    input wire [31:0] topology_id_i,"),
    ):
        if controller.count(old) != 1:
            raise ValueError(f"native identity anchor drift: {old}")
        controller = controller.replace(old, new)
    controller = re.sub(r"\bBLOCK_ID\b", "block_id_i", controller)
    controller = re.sub(r"\bNATIVE_TOPOLOGY\b", "topology_id_i", controller)
    baseline.unlink()
    (directory / "pu_native_lc.sv").write_text(controller)

    p_adapter = directory / "pj_native_service.sv"
    adapter = p_adapter.read_text()
    for old, new in (
        ("module pj_native_service #", "module pu_p_native_service #"),
        ("    input wire clk, reset,", "    input wire clk, reset, late_path_enable,"),
        ("output wire [29:0] gate_fields", "output wire [30:0] gate_fields"),
        ("assign gate_fields = fields[29:0];", "assign gate_fields = fields[30:0];"),
        ("request_fields[31:22]==0", "request_fields[31:23]==0 && "
         "(!request_fields[22] || (late_path_enable && !request_fields[10] && request_fields[3:0]==5))"),
        ("request_fields[31:30]==0", "request_fields[31]==0 && (!request_fields[30] || late_path_enable)"),
    ):
        if adapter.count(old) != 1:
            raise ValueError(f"native P adapter anchor drift: {old}")
        adapter = adapter.replace(old, new)
    p_adapter.write_text(adapter)

    ports, connections, internal, identity = [], [], [], []
    mapping = dict(CONTROL_LINK, clk_i="clk", rst_ni="local_rst_ni")
    for field, width in IDENTITY_FIELDS.items():
        mapping[f"svc_req_{field}_o"] = f"request_{field}"
        mapping[f"svc_rsp_{field}_i"] = f"response_{field}"
        internal.append(f"    reg [{width-1}:0] response_{field};")
        identity.append(f"        response_{field} <= request_{field};")
    for declaration in (directory / "ports.svh").read_text().splitlines():
        direction, width, name = re.fullmatch(
            r"(input|output) wire\s*(\[\d+:\d+\])?\s*(\w+),?", declaration.strip()
        ).groups()
        width = (width + " ") if width else ""
        if name in {"clk_i", "rst_ni"}:
            signal = mapping[name]
        elif name in mapping:
            signal = mapping[name]
            if direction == "output" or signal in {"svc_ready", "rsp_valid", "status", "saturated", "read_bytes", "write_bytes"}:
                internal.append(f"    wire {width}{signal};")
        elif name.startswith(("svc_", "trace_")):
            if direction != "output":
                raise ValueError(f"unbound controller input {name}")
            signal = ""
        else:
            ports.append(f"    {direction} wire {width}{name}")
            signal = name
        connections.append(f"        .{name}({signal})")

    kind = 3 if group == "P" else 0
    extra_ports, endpoint = (P_PORTS, P_ENDPOINT) if group == "P" else (U_PORTS, U_ENDPOINT)
    name = f"pu_{group.lower()}_controlled"
    wrapper = directory / (name + ".sv")
    wrapper.write_text(
        f"module {name}(\n"
        "    input wire clk, rst_ni,\n"
        "    input wire [7:0] block_id_i,\n"
        "    input wire [31:0] topology_id_i,\n" + ",\n".join(ports) + ",\n" + extra_ports + ");\n"
        "    (* async_reg = \"true\", keep = 1 *) reg [1:0] reset_release;\n"
        "    always @(posedge clk or negedge rst_ni) begin\n"
        "        if (!rst_ni) reset_release <= 2'b00;\n"
        "        else reset_release <= {reset_release[0],1'b1};\n"
        "    end\n"
        "    wire local_rst_ni = reset_release[1];\n"
        "    wire reset = !local_rst_ni;\n" + "\n".join(internal)
        + "\n    always @(posedge clk) if (svc_valid && svc_ready) begin\n"
        + "\n".join(identity) + "\n    end\n"
        + f"    pu_native_lc #(.ENABLE_NATIVE(1'b1),.STALL_LIMIT(4096),.NATIVE_BLOCK_TYPE(8'd{kind})) controller(\n"
        "        .block_id_i,.topology_id_i,\n"
        + ",\n".join(connections) + ");\n" + endpoint + "endmodule\n"
    )
    return directory, name
