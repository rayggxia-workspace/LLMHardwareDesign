"""Use the production controller and endpoint wiring in the #195 regression."""
from group_top import CTRL, group, instance, ports


def stage_groups(bundle):
    design = bundle / "design"
    declarations = ports((bundle / CTRL / "ports.svh").read_text())
    for kind in ("c", "f", "j"):
        native = "block_cfj_j" if kind == "j" else "block_cfj_cf"
        group(design, kind, native, [design / f"{native}.sv"], declarations, verify_read=True)

    # The U counterpart remains the immutable #195 reference. Its controller
    # and the testbench's stimulus still use the original fixture.
    original = design / "tb_native_local.sv"
    text = original.read_text()
    original.write_text(text.replace("module tb_native_local", "module tb_reference_u", 1))
    ctrl_dir = bundle / CTRL
    wires = (ctrl_dir / "tb_network_lc_wires.svh").read_text()
    wires = wires[:wires.index("lc_min_controller #")]
    wires = "\n".join(line for line in wires.splitlines()
                      if "svc_" not in line and "close_" not in line) + "\n"
    start = text.index("`define TB_NATIVE")
    pm = text[text.index("    network_pm pm"):text.index("\n\n    if (KIND<3)")]
    cfg = text[text.index("    reg [127:0] image"):].replace("        svc_rsp_kind_i=0;\n", "")
    cfg = "\n".join(line for line in cfg.splitlines() if "close_" not in line) + "\n"
    control_pins = {name: name for name in declarations if not name.startswith(("svc_", "close_"))}
    wiring = []
    for kind, number in (("c", 2), ("f", 1), ("j", 4)):
        wiring.append(f"    else if (KIND=={number}) begin: group_{kind}\n")
        pins = control_pins.copy()
        if kind == "j":
            wiring.append("""
        wire [1:0] req_ready, rsp_valid;
        wire out_valid, out_last, rx_error;
        wire [31:0] out_tag;
        wire [9:0] out_index;
        wire [127:0] out_data, late_data;
        wire late_valid, late_take;
        reg [2:0] hold_age;
        reg [127:0] committed;
        reg observed;
        wire out_take=hold_age==3;
        assign {outgoing_valid,outgoing_addr,outgoing_data,outgoing_ack_ready,
                incoming_ready,incoming_ack,link_rx_reserved,link_rx_addr}=0;
        assign seed_ready=req_ready[0];
        assign seed_ack=rsp_valid[0];
        assign check_valid=observed;
        assign check_data=committed;
        always @(posedge clk_i) begin
            if (!rst_ni) begin committed<=0; observed<=0; hold_age<=0; end
            else begin
                if (seed_ack && rx_error) $fatal(1,"unexpected J RX error");
                if (out_valid && !out_take) hold_age<=hold_age+1'b1;
                if (out_valid && out_take) begin
                    if (out_tag!=32'h01000007 || out_index!=0 || !out_last)
                        $fatal(1,"incorrect J output identity");
                    committed<=out_data; observed<=1; hold_age<=0;
                end
                if (check_take) observed<=0;
            end
        end
""")
            pins.update(io_req_valid="{1'b0,seed_valid}", io_req_write="2'b01",
                        io_req_addr="{10'd0,seed_addr}", io_req_data="{128'd0,seed_data}",
                        io_req_ready="req_ready", io_rsp_valid="rsp_valid", io_rsp_ready="2'b01",
                        io_rsp_data="", active_epoch="8'd1", rx_tag="32'h01000007",
                        rx_slot="{1'b0,seed_addr[3]}", rx_last="1'b1", rx_error="rx_error",
                        out_valid="out_valid", out_take="out_take", out_data="out_data",
                        out_tag="out_tag", out_index="out_index", out_last="out_last",
                        late_e_valid="late_valid", late_e_take="late_take", late_e_data="late_data",
                        late_s_valid="late_valid", late_s_take="late_take", late_s_data="late_data")
        else:
            wiring.append("""
        wire rx_ready, rx_stored, late_valid, late_take;
        wire [31:0] late_data;
        assign seed_ready=!deploy_valid_i && rx_ready;
        assign seed_ack=!deploy_valid_i && rx_stored;
        assign incoming_ready=deploy_valid_i && rx_ready;
        assign incoming_ack=deploy_valid_i && rx_stored;
""")
            pins.update(rx_valid="deploy_valid_i ? incoming_valid : seed_valid",
                        rx_ready="rx_ready", rx_addr="deploy_valid_i ? incoming_addr : seed_addr",
                        rx_data="deploy_valid_i ? incoming_data : seed_data", rx_stored="rx_stored",
                        rx_stored_ready="!deploy_valid_i || incoming_ack_ready",
                        late_g_valid="late_valid", late_g_data="late_data", late_g_take="late_take",
                        late_e_valid="late_valid", late_e_data="late_data", late_e_take="late_take",
                        verify_read="check_read", verify_addr="check_addr", verify_take="check_take",
                        verify_valid="check_valid", verify_data="check_data",
                        peer_reserved="peer_rx_reserved", peer_addr="peer_rx_addr",
                        rx_reserved="link_rx_reserved", rx_reserved_addr="link_rx_addr")
            pins.update({n:n for n in ("outgoing_valid", "outgoing_ready", "outgoing_addr",
                                        "outgoing_data", "outgoing_ack", "outgoing_ack_ready")})
        wiring.append(instance(f"cfj_group_{kind}", "dut", pins,
                               ".BLOCK_ID(BLOCK), .TOPOLOGY_ID(TOPOLOGY_ID)"))
        wiring.append("    end\n")
    reference = """    if (KIND==0) begin: reference_u
        tb_reference_u #(.BLOCK(BLOCK), .KIND(KIND), .TOPOLOGY_ID(TOPOLOGY_ID)) dut(.*);
    end
"""
    # Move fixture state into the branch for our groups so that the legacy U
    # instance owns its image, outputs, and configuration independently.
    (design / "tb_cfj_local.sv").write_text(
        text[:start] + reference + "    else begin: group_fixture\n"
        + wires + pm + "\n"
        + "    if (KIND==255) begin end\n" + "".join(wiring)
        + cfg.removesuffix("endmodule\n") + "    end\nendmodule\n")
    pair = design / "tb_native_pair.sv"
    pair.write_text(pair.read_text().replace("tb_native_local #", "tb_cfj_local #"))
