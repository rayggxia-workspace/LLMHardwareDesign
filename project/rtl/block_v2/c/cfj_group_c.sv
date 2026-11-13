`timescale 1ns/1ps
module cfj_group_c #(
    parameter [7:0] GLOBAL_TARGET=0,
    parameter [7:0] LEGACY_BLOCK_ID=0,
    parameter [31:0] LEGACY_TOPOLOGY=32'h01930010
)(
    input wire  clk_i,
    input wire  rst_ni,
    input wire  release_valid_i,
    input wire [31:0] release_sequence_i,
    input wire [31:0] release_epoch_i,
    input wire  deploy_valid_i,
    input wire [31:0] deploy_generation_i,
    output wire  release_ready_o,
    output wire  poison_o,
    output wire  image_valid_o,
    input wire  cfg_req_valid_i,
    input wire [2:0] cfg_req_op_i,
    input wire [31:0] cfg_req_generation_i,
    input wire [13:0] cfg_req_address_i,
    input wire [127:0] cfg_req_data_i,
    input wire [15:0] cfg_req_total_bytes_i,
    input wire [31:0] cfg_req_image_id_i,
    input wire [31:0] cfg_req_topology_id_i,
    input wire [31:0] cfg_req_abi_id_i,
    input wire [31:0] cfg_req_capacity_id_i,
    input wire  cfg_req_proof_i,
    input wire  cfg_rsp_ready_i,
    output wire  cfg_req_ready_o,
    output wire  cfg_rsp_valid_o,
    output wire [15:0] cfg_rsp_status_o,
    output wire [127:0] cfg_rsp_data_o,
    output wire [31:0] cfg_rsp_generation_o,
    output wire [3:0] life_o,
    output wire [3:0] seq_o,
    output wire [31:0] trace_pc_o,
    output wire  trace_retire_o,
    output wire [7:0] trace_opcode_o,
    output wire [1:0] trace_pm_owner_o,
    output wire  trace_ireg_valid_o,
    output wire  trace_cancel_token_retire_o,
    output wire  trace_cancel_object_drop_o,
    input wire  rx_valid,
    output wire  rx_ready,
    input wire [9:0] rx_addr,
    input wire [127:0] rx_data,
    output wire  rx_stored,
    input wire  rx_stored_ready,
    output wire  late_g_valid,
    output wire [31:0] late_g_data,
    input wire  late_g_take,
    input wire  late_e_valid,
    input wire [31:0] late_e_data,
    output wire  late_e_take,
    input wire  peer_reserved,
    input wire [9:0] peer_addr,
    output wire  outgoing_valid,
    input wire  outgoing_ready,
    output wire [9:0] outgoing_addr,
    output wire [127:0] outgoing_data,
    input wire  outgoing_ack,
    output wire  outgoing_ack_ready,
    output wire  rx_reserved,
    output wire [9:0] rx_reserved_addr,
    input wire native_rx_valid_i, native_rx_sop_i, native_rx_eop_i, native_rx_credit_i,
    input wire [127:0] native_rx_data_i,
    input wire [7:0] native_rx_target_i,
    output wire native_rx_ready_o,
    output wire native_tx_valid_o, native_tx_sop_o, native_tx_eop_o,
    output wire [127:0] native_tx_data_o,
    input wire native_tx_ready_i,
    input wire [31:0] native_image_i, native_topology_i, legacy_image_i,
    output wire native_link_drained_o, native_link_fault_o
);
    wire  pm_req_ready_i;
    wire  pm_rsp_valid_i;
    wire [127:0] pm_rsp_data_i;
    wire  pm_rsp_error_i;
    wire  pm_req_valid_o;
    wire  pm_req_write_o;
    wire [13:0] pm_req_address_o;
    wire [127:0] pm_req_data_o;
    wire  pm_rsp_ready_o;
    wire  task_valid_i;
    wire [511:0] task_packet_i;
    wire  task_credit_i;
    wire  task_ready_o;
    wire  event_ready_i;
    wire  event_valid_o;
    wire [511:0] event_packet_o;
    (* async_reg = "true" *) reg [1:0] reset_release;
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) reset_release <= 2'b00;
        else reset_release <= {reset_release[0], 1'b1};
    end
    wire local_rst_ni = reset_release[1];
    wire [15:0] bounded_total_bytes = cfg_req_total_bytes_i > 16'd4096 ?
                                      16'd0 : cfg_req_total_bytes_i;

    wire native_task_valid, native_task_credit, native_task_ready;
    wire native_event_valid, native_event_ready;
    wire [511:0] native_task, native_event;
    wire frame_drained, record_drained, record_fault;
    wire [31:0] frame_fault_count;
    assign native_link_drained_o = frame_drained && record_drained;
    assign native_link_fault_o = record_fault || (|frame_fault_count);

    lc_packet128_bridge #(.GLOBAL_TARGET(GLOBAL_TARGET)) frame (
        .clk(clk_i), .reset(!local_rst_ni),
        .rx_valid(native_rx_valid_i), .rx_sop(native_rx_sop_i),
        .rx_eop(native_rx_eop_i), .rx_credit(native_rx_credit_i),
        .rx_data(native_rx_data_i), .rx_target(native_rx_target_i),
        .rx_ready(native_rx_ready_o),
        .native_task_valid, .native_task_credit, .native_task, .native_task_ready,
        .native_event_valid, .native_event, .native_event_ready,
        .tx_valid(native_tx_valid_o), .tx_sop(native_tx_sop_o),
        .tx_eop(native_tx_eop_o), .tx_data(native_tx_data_o), .tx_ready(native_tx_ready_i),
        .drained(frame_drained), .frame_fault_count
    );

    // The coordinator keeps the native and legacy image identities stable
    // from deployment until the switch and all endpoint records have drained.
    mc_lc_legacy_v1_records #(.GLOBAL_TARGET(GLOBAL_TARGET), .LEGACY_BLOCK_ID(LEGACY_BLOCK_ID)) records (
        .clk(clk_i), .reset(!local_rst_ni), .binding_valid(deploy_valid_i && image_valid_o),
        .native_image(native_image_i), .native_topology(native_topology_i),
        .native_generation(deploy_generation_i), .legacy_image(legacy_image_i),
        .legacy_topology(LEGACY_TOPOLOGY),
        .native_task_valid, .native_task_credit, .native_task, .native_task_ready,
        .native_event_valid, .native_event, .native_event_ready,
        .legacy_task_valid(task_valid_i), .legacy_task_credit(task_credit_i),
        .legacy_task(task_packet_i), .legacy_task_ready(task_ready_o),
        .legacy_event_valid(event_valid_o), .legacy_event(event_packet_o),
        .legacy_event_ready(event_ready_i), .drained(record_drained), .protocol_fault(record_fault)
    );

    control_pm #(.BYTES(4096), .USE_SRAM(1'b1)) program_store (
        .clk_i, .rst_ni(local_rst_ni), .req_valid_i(pm_req_valid_o),
        .req_write_i(pm_req_write_o), .req_address_i(pm_req_address_o),
        .req_data_i(pm_req_data_o), .req_ready_o(pm_req_ready_i),
        .rsp_valid_o(pm_rsp_valid_i), .rsp_ready_i(pm_rsp_ready_o),
        .rsp_data_o(pm_rsp_data_i), .rsp_error_o(pm_rsp_error_i)
    );

    cfj_group_c_legacy #(.BLOCK_ID(LEGACY_BLOCK_ID), .TOPOLOGY_ID(LEGACY_TOPOLOGY)) local_group (
        .clk_i,
        .rst_ni,
        .release_valid_i,
        .release_sequence_i,
        .release_epoch_i,
        .deploy_valid_i,
        .deploy_generation_i,
        .release_ready_o,
        .poison_o,
        .image_valid_o,
        .cfg_req_valid_i,
        .cfg_req_op_i,
        .cfg_req_generation_i,
        .cfg_req_address_i,
        .cfg_req_data_i,
        .cfg_req_total_bytes_i(bounded_total_bytes),
        .cfg_req_image_id_i,
        .cfg_req_topology_id_i,
        .cfg_req_abi_id_i,
        .cfg_req_capacity_id_i,
        .cfg_req_proof_i,
        .cfg_rsp_ready_i,
        .cfg_req_ready_o,
        .cfg_rsp_valid_o,
        .cfg_rsp_status_o,
        .cfg_rsp_data_o,
        .cfg_rsp_generation_o,
        .pm_req_ready_i,
        .pm_rsp_valid_i,
        .pm_rsp_data_i,
        .pm_rsp_error_i,
        .pm_req_valid_o,
        .pm_req_write_o,
        .pm_req_address_o,
        .pm_req_data_o,
        .pm_rsp_ready_o,
        .task_valid_i,
        .task_packet_i,
        .task_credit_i,
        .task_ready_o,
        .event_ready_i,
        .event_valid_o,
        .event_packet_o,
        .life_o,
        .seq_o,
        .trace_pc_o,
        .trace_retire_o,
        .trace_opcode_o,
        .trace_pm_owner_o,
        .trace_ireg_valid_o,
        .trace_cancel_token_retire_o,
        .trace_cancel_object_drop_o,
        .rx_valid,
        .rx_ready,
        .rx_addr,
        .rx_data,
        .rx_stored,
        .rx_stored_ready,
        .late_g_valid,
        .late_g_data,
        .late_g_take,
        .late_e_valid,
        .late_e_data,
        .late_e_take,
        .peer_reserved,
        .peer_addr,
        .outgoing_valid,
        .outgoing_ready,
        .outgoing_addr,
        .outgoing_data,
        .outgoing_ack,
        .outgoing_ack_ready,
        .rx_reserved,
        .rx_reserved_addr
    );
endmodule
