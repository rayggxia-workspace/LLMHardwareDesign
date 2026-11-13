module cfj_group_c_legacy #(parameter [7:0] BLOCK_ID=0,
    parameter [31:0] TOPOLOGY_ID=32'h01930010)(
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
    input wire  pm_req_ready_i,
    input wire  pm_rsp_valid_i,
    input wire [127:0] pm_rsp_data_i,
    input wire  pm_rsp_error_i,
    output wire  pm_req_valid_o,
    output wire  pm_req_write_o,
    output wire [13:0] pm_req_address_o,
    output wire [127:0] pm_req_data_o,
    output wire  pm_rsp_ready_o,
    input wire  task_valid_i,
    input wire [511:0] task_packet_i,
    input wire  task_credit_i,
    output wire  task_ready_o,
    input wire  event_ready_i,
    output wire  event_valid_o,
    output wire [511:0] event_packet_o,
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
    output wire [9:0] rx_reserved_addr
);
    localparam integer CLIENTS=5;
    wire clk=clk_i;
    // Asynchronous assertion and two-cycle synchronous release.
    (* async_reg = "true" *) reg [1:0] reset_release;
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) reset_release <= 2'b00;
        else reset_release <= {reset_release[0], 1'b1};
    end
    wire reset=!reset_release[1];
    wire  svc_req_ready_i;
    wire  svc_rsp_valid_i;
    reg [2:0] svc_rsp_token_i;
    reg [31:0] svc_rsp_sequence_i;
    reg [31:0] svc_rsp_job_i;
    reg [31:0] svc_rsp_epoch_i;
    reg [31:0] svc_rsp_task_sequence_i;
    wire [15:0] svc_rsp_status_i;
    wire [31:0] svc_rsp_read_bytes_i;
    wire [31:0] svc_rsp_write_bytes_i;
    wire  svc_rsp_saturated_i;
    wire  svc_req_valid_o;
    wire [1:0] svc_req_kind_o;
    wire [2:0] svc_req_resource_o;
    wire [2:0] svc_req_token_o;
    wire [31:0] svc_req_sequence_o;
    wire [31:0] svc_req_job_o;
    wire [31:0] svc_req_epoch_o;
    wire [31:0] svc_req_task_sequence_o;
    wire [1023:0] svc_req_descriptor_o;
    wire [63:0] svc_req_object_base_o;
    wire [31:0] svc_req_object_length_o;
    wire [31:0] svc_req_object_version_o;
    wire  svc_rsp_ready_o;
    wire [(CLIENTS-2)*30-1:0] cmd_addresses;
    wire [(CLIENTS-2)*10-1:0] cmd_dst;
    wire [(CLIENTS-2)*64-1:0] cmd_meta;
    wire [CLIENTS-3:0] cmd_ready;
    wire [(CLIENTS-2)*2-1:0] cmd_sources;
    wire [CLIENTS-3:0] cmd_store;
    wire [CLIENTS-3:0] cmd_valid;
    wire [CLIENTS-3:0] done_error;
    wire [CLIENTS-3:0] done_ready;
    wire [CLIENTS-3:0] done_saturated;
    wire [CLIENTS-3:0] done_valid;
    wire [9:0] tx_addr;
    wire [127:0] tx_data;
    wire  tx_ready;
    wire  tx_req;
    wire  tx_take;
    wire  tx_valid;
    always @(posedge clk) begin
        if (reset) begin
            svc_rsp_token_i <= '0;
            svc_rsp_sequence_i <= '0;
            svc_rsp_job_i <= '0;
            svc_rsp_epoch_i <= '0;
            svc_rsp_task_sequence_i <= '0;
        end else if (svc_req_valid_o && svc_req_ready_i) begin
            svc_rsp_token_i <= svc_req_token_o;
            svc_rsp_sequence_i <= svc_req_sequence_o;
            svc_rsp_job_i <= svc_req_job_o;
            svc_rsp_epoch_i <= svc_req_epoch_o;
            svc_rsp_task_sequence_i <= svc_req_task_sequence_o;
        end
    end
    lc_min_controller #(.BLOCK_ID(BLOCK_ID), .ENABLE_NATIVE(1'b1), .NATIVE_BLOCK_TYPE(8'd2), .NATIVE_TOPOLOGY(TOPOLOGY_ID), .STALL_LIMIT(4096)) control(
        .clk_i(clk_i),
        .rst_ni(reset_release[1]),
        .release_valid_i(release_valid_i),
        .release_sequence_i(release_sequence_i),
        .release_epoch_i(release_epoch_i),
        .deploy_valid_i(deploy_valid_i),
        .deploy_generation_i(deploy_generation_i),
        .release_ready_o(release_ready_o),
        .poison_o(poison_o),
        .image_valid_o(image_valid_o),
        .cfg_req_valid_i(cfg_req_valid_i),
        .cfg_req_op_i(cfg_req_op_i),
        .cfg_req_generation_i(cfg_req_generation_i),
        .cfg_req_address_i(cfg_req_address_i),
        .cfg_req_data_i(cfg_req_data_i),
        .cfg_req_total_bytes_i(cfg_req_total_bytes_i),
        .cfg_req_image_id_i(cfg_req_image_id_i),
        .cfg_req_topology_id_i(cfg_req_topology_id_i),
        .cfg_req_abi_id_i(cfg_req_abi_id_i),
        .cfg_req_capacity_id_i(cfg_req_capacity_id_i),
        .cfg_req_proof_i(cfg_req_proof_i),
        .cfg_rsp_ready_i(cfg_rsp_ready_i),
        .cfg_req_ready_o(cfg_req_ready_o),
        .cfg_rsp_valid_o(cfg_rsp_valid_o),
        .cfg_rsp_status_o(cfg_rsp_status_o),
        .cfg_rsp_data_o(cfg_rsp_data_o),
        .cfg_rsp_generation_o(cfg_rsp_generation_o),
        .pm_req_ready_i(pm_req_ready_i),
        .pm_rsp_valid_i(pm_rsp_valid_i),
        .pm_rsp_data_i(pm_rsp_data_i),
        .pm_rsp_error_i(pm_rsp_error_i),
        .pm_req_valid_o(pm_req_valid_o),
        .pm_req_write_o(pm_req_write_o),
        .pm_req_address_o(pm_req_address_o),
        .pm_req_data_o(pm_req_data_o),
        .pm_rsp_ready_o(pm_rsp_ready_o),
        .task_valid_i(task_valid_i),
        .task_packet_i(task_packet_i),
        .task_credit_i(task_credit_i),
        .task_ready_o(task_ready_o),
        .svc_req_ready_i(svc_req_ready_i),
        .svc_rsp_valid_i(svc_rsp_valid_i),
        .svc_rsp_kind_i('0),
        .svc_rsp_token_i(svc_rsp_token_i),
        .svc_rsp_sequence_i(svc_rsp_sequence_i),
        .svc_rsp_job_i(svc_rsp_job_i),
        .svc_rsp_epoch_i(svc_rsp_epoch_i),
        .svc_rsp_task_sequence_i(svc_rsp_task_sequence_i),
        .svc_rsp_status_i(svc_rsp_status_i),
        .svc_rsp_read_bytes_i(svc_rsp_read_bytes_i),
        .svc_rsp_write_bytes_i(svc_rsp_write_bytes_i),
        .svc_rsp_saturated_i(svc_rsp_saturated_i),
        .svc_req_valid_o(svc_req_valid_o),
        .svc_req_kind_o(svc_req_kind_o),
        .svc_req_resource_o(svc_req_resource_o),
        .svc_req_token_o(svc_req_token_o),
        .svc_req_sequence_o(svc_req_sequence_o),
        .svc_req_job_o(svc_req_job_o),
        .svc_req_epoch_o(svc_req_epoch_o),
        .svc_req_task_sequence_o(svc_req_task_sequence_o),
        .svc_req_descriptor_o(svc_req_descriptor_o),
        .svc_req_object_base_o(svc_req_object_base_o),
        .svc_req_object_length_o(svc_req_object_length_o),
        .svc_req_object_version_o(svc_req_object_version_o),
        .svc_rsp_ready_o(svc_rsp_ready_o),
        .event_ready_i(event_ready_i),
        .event_valid_o(event_valid_o),
        .event_packet_o(event_packet_o),
        .close_req_ready_i('0),
        .close_rsp_valid_i('0),
        .close_rsp_sequence_i('0),
        .close_rsp_job_i('0),
        .close_rsp_epoch_i('0),
        .close_rsp_task_sequence_i('0),
        .close_rsp_token_i('0),
        .close_rsp_status_i('0),
        .close_req_valid_o(),
        .close_req_sequence_o(),
        .close_req_job_o(),
        .close_req_epoch_o(),
        .close_req_task_sequence_o(),
        .close_req_token_o(),
        .close_rsp_ready_o(),
        .life_o(life_o),
        .seq_o(seq_o),
        .trace_pc_o(trace_pc_o),
        .trace_retire_o(trace_retire_o),
        .trace_opcode_o(trace_opcode_o),
        .trace_pm_owner_o(trace_pm_owner_o),
        .trace_ireg_valid_o(trace_ireg_valid_o),
        .trace_cancel_token_retire_o(trace_cancel_token_retire_o),
        .trace_cancel_object_drop_o(trace_cancel_object_drop_o)
    );
    wire send_start, send_ready, send_done, native_rx_ready;
    wire [9:0] source_addr, destination_addr;
    wire rx_admitted=!deploy_valid_i || (rx_reserved && rx_addr==rx_reserved_addr);
    assign rx_ready=native_rx_ready && rx_admitted;
    ucf_native_service #(.LANES(CLIENTS-2)) dispatch(
        .clk(clk),
        .reset(reset),
        .svc_valid(svc_req_valid_o),
        .svc_ready(svc_req_ready_i),
        .descriptor(svc_req_descriptor_o),
        .rsp_valid(svc_rsp_valid_i),
        .rsp_ready(svc_rsp_ready_o),
        .status(svc_rsp_status_i),
        .saturated(svc_rsp_saturated_i),
        .read_bytes(svc_rsp_read_bytes_i),
        .write_bytes(svc_rsp_write_bytes_i),
        .cmd_addresses(cmd_addresses),
        .cmd_dst(cmd_dst),
        .done_saturated(done_saturated),
        .cmd_ready(cmd_ready),
        .cmd_sources(cmd_sources),
        .done_ready(done_ready),
        .cmd_valid(cmd_valid),
        .done_valid(done_valid),
        .done_error(done_error),
        .cmd_store(cmd_store),
        .cmd_meta(cmd_meta),
        .send_start(send_start),
        .send_ready(send_ready),
        .send_done(send_done),
        .source_addr(source_addr),
        .destination_addr(destination_addr),
        .receive_commit(rx_stored && rx_stored_ready),
        .receive_reserved(rx_reserved),
        .receive_address(rx_reserved_addr)
    );
    stored_link transport(
        .clk(clk),
        .reset(reset),
        .source_addr(source_addr),
        .destination_addr(destination_addr),
        .tx_req(tx_req),
        .tx_ready(tx_ready),
        .tx_addr(tx_addr),
        .tx_valid(tx_valid),
        .tx_take(tx_take),
        .tx_data(tx_data),
        .start(send_start),
        .ready(send_ready),
        .done(send_done),
        .rx_valid(outgoing_valid),
        .rx_ready(outgoing_ready),
        .rx_addr(outgoing_addr),
        .rx_data(outgoing_data),
        .rx_stored(outgoing_ack),
        .rx_stored_ready(outgoing_ack_ready),
        .sink_reserved(peer_reserved && peer_addr==outgoing_addr)
    );
    block_cfj_cf #(.KIND(2), .LATE_G_E(1'b1), .E32_ENABLE(1'b1)) services(
        .clk(clk),
        .reset(reset),
        .cmd_valid(cmd_valid),
        .cmd_ready(cmd_ready),
        .cmd_meta(cmd_meta),
        .cmd_sources(cmd_sources),
        .cmd_addresses(cmd_addresses),
        .cmd_store(cmd_store),
        .cmd_dst(cmd_dst),
        .done_valid(done_valid),
        .done_ready(done_ready),
        .done_data(),
        .done_error(done_error),
        .done_saturated(done_saturated),
        .rx_valid(rx_valid && rx_admitted),
        .rx_ready(native_rx_ready),
        .rx_addr(rx_addr),
        .rx_data(rx_data),
        .rx_stored(rx_stored),
        .rx_stored_ready(rx_stored_ready),
        .tx_req(tx_req),
        .tx_ready(tx_ready),
        .tx_addr(tx_addr),
        .tx_valid(tx_valid),
        .tx_take(tx_take),
        .tx_data(tx_data),
        .late_g_valid(late_g_valid),
        .late_g_data(late_g_data),
        .late_g_take(late_g_take),
        .late_e_valid(late_e_valid),
        .late_e_data(late_e_data),
        .late_e_take(late_e_take)
    );
endmodule
