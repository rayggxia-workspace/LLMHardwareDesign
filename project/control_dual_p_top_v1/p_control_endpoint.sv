`timescale 1ns/1ps
// Fixed one-way P service endpoint; private SRAM is instantiated by pu_p_group.
module p_control_endpoint #(parameter [7:0] BLOCK=0)(
    input wire clk_i,
    input wire rst_ni,
    input wire release_valid_i,
    input wire [31:0] release_sequence_i,
    input wire [31:0] release_epoch_i,
    input wire deploy_valid_i,
    input wire [31:0] deploy_generation_i,
    output wire release_ready_o,
    output wire poison_o,
    output wire image_valid_o,
    input wire cfg_req_valid_i,
    input wire [2:0] cfg_req_op_i,
    input wire [31:0] cfg_req_generation_i,
    input wire [13:0] cfg_req_address_i,
    input wire [127:0] cfg_req_data_i,
    input wire [15:0] cfg_req_total_bytes_i,
    input wire [31:0] cfg_req_image_id_i,
    input wire [31:0] cfg_req_topology_id_i,
    input wire [31:0] cfg_req_abi_id_i,
    input wire [31:0] cfg_req_capacity_id_i,
    input wire cfg_req_proof_i,
    input wire cfg_rsp_ready_i,
    output wire cfg_req_ready_o,
    output wire cfg_rsp_valid_o,
    output wire [15:0] cfg_rsp_status_o,
    output wire [127:0] cfg_rsp_data_o,
    output wire [31:0] cfg_rsp_generation_o,
    input wire pm_req_ready_i,
    input wire pm_rsp_valid_i,
    input wire [127:0] pm_rsp_data_i,
    input wire pm_rsp_error_i,
    output wire pm_req_valid_o,
    output wire pm_req_write_o,
    output wire [13:0] pm_req_address_o,
    output wire [127:0] pm_req_data_o,
    output wire pm_rsp_ready_o,
    input wire task_valid_i,
    input wire [511:0] task_packet_i,
    input wire task_credit_i,
    output wire task_ready_o,
    input wire event_ready_i,
    output wire event_valid_o,
    output wire [511:0] event_packet_o,
    output wire [3:0] life_o,
    output wire [3:0] seq_o,
    input wire host_req_valid_i,
    input wire host_req_write_i,
    input wire [9:0] host_req_address_i,
    input wire [127:0] host_req_data_i,
    output wire host_req_ready_o,
    output wire host_rsp_valid_o,
    input wire host_rsp_ready_i,
    output wire [127:0] host_rsp_data_o,
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
    output reg [127:0] outgoing_identity,
    input wire incoming_valid,
    output wire incoming_ready,
    input wire [9:0] incoming_addr,
    input wire [127:0] incoming_data,
    output wire incoming_ack,
    input wire incoming_ack_ready
);
    reg svc_req_ready_i;
    reg svc_rsp_valid_i;
    wire [1:0] svc_rsp_kind_i;
    assign svc_rsp_kind_i='0;
    reg [2:0] svc_rsp_token_i;
    reg [31:0] svc_rsp_sequence_i;
    reg [31:0] svc_rsp_job_i;
    reg [31:0] svc_rsp_epoch_i;
    reg [31:0] svc_rsp_task_sequence_i;
    reg [15:0] svc_rsp_status_i;
    reg [31:0] svc_rsp_read_bytes_i;
    reg [31:0] svc_rsp_write_bytes_i;
    reg svc_rsp_saturated_i;
    wire svc_req_valid_o;
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
    wire svc_rsp_ready_o;
    wire close_req_ready_i;
    assign close_req_ready_i='0;
    wire close_rsp_valid_i;
    assign close_rsp_valid_i='0;
    wire [31:0] close_rsp_sequence_i;
    assign close_rsp_sequence_i='0;
    wire [31:0] close_rsp_job_i;
    assign close_rsp_job_i='0;
    wire [31:0] close_rsp_epoch_i;
    assign close_rsp_epoch_i='0;
    wire [31:0] close_rsp_task_sequence_i;
    assign close_rsp_task_sequence_i='0;
    wire [2:0] close_rsp_token_i;
    assign close_rsp_token_i='0;
    wire [15:0] close_rsp_status_i;
    assign close_rsp_status_i='0;
    wire close_req_valid_o;
    wire [31:0] close_req_sequence_o;
    wire [31:0] close_req_job_o;
    wire [31:0] close_req_epoch_o;
    wire [31:0] close_req_task_sequence_o;
    wire [2:0] close_req_token_o;
    wire close_rsp_ready_o;
    wire [31:0] trace_pc_o;
    wire trace_retire_o;
    wire [7:0] trace_opcode_o;
    wire [1:0] trace_pm_owner_o;
    wire trace_ireg_valid_o;
    wire trace_cancel_token_retire_o;
    wire trace_cancel_object_drop_o;
    lc_min_controller #(.BLOCK_ID(BLOCK),.ENABLE_NATIVE_P16(1'b1),.STALL_LIMIT(4096)) control(
        .clk_i(clk_i),
        .rst_ni(rst_ni),
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
        .svc_rsp_kind_i(svc_rsp_kind_i),
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
        .close_req_ready_i(close_req_ready_i),
        .close_rsp_valid_i(close_rsp_valid_i),
        .close_rsp_sequence_i(close_rsp_sequence_i),
        .close_rsp_job_i(close_rsp_job_i),
        .close_rsp_epoch_i(close_rsp_epoch_i),
        .close_rsp_task_sequence_i(close_rsp_task_sequence_i),
        .close_rsp_token_i(close_rsp_token_i),
        .close_rsp_status_i(close_rsp_status_i),
        .close_req_valid_o(close_req_valid_o),
        .close_req_sequence_o(close_req_sequence_o),
        .close_req_job_o(close_req_job_o),
        .close_req_epoch_o(close_req_epoch_o),
        .close_req_task_sequence_o(close_req_task_sequence_o),
        .close_req_token_o(close_req_token_o),
        .close_rsp_ready_o(close_rsp_ready_o),
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
    localparam bit SOURCE = BLOCK==0;
    wire [15:0] op = svc_req_descriptor_o[32+:16];
    wire link_command = SOURCE ? op==16'h101 : op==16'h102 || op==16'h103;
    wire link_ready, link_rsp, native_ready, native_rsp;
    wire [15:0] link_status, native_status;
    wire [31:0] link_reads, link_writes, native_reads, native_writes;
    wire link_sat, native_sat;
    reg active_link;
    always @* begin
        svc_req_ready_i = link_command ? link_ready : native_ready;
        svc_rsp_valid_i = active_link ? link_rsp : native_rsp;
        svc_rsp_status_i = active_link ? link_status : native_status;
        svc_rsp_read_bytes_i = active_link ? link_reads : native_reads;
        svc_rsp_write_bytes_i = active_link ? link_writes : native_writes;
        svc_rsp_saturated_i = active_link ? link_sat : native_sat;
    end
    always @(posedge clk_i) begin
        if (!rst_ni) begin
            active_link<=0;
            outgoing_identity<=0;
            svc_rsp_token_i<='0;
            svc_rsp_sequence_i<='0;
            svc_rsp_job_i<='0;
            svc_rsp_epoch_i<='0;
            svc_rsp_task_sequence_i<='0;

        end else if (svc_req_valid_o && svc_req_ready_i) begin
            if (SOURCE && link_command)
                outgoing_identity<={svc_req_job_o,svc_req_epoch_o,svc_req_task_sequence_o,svc_req_sequence_o};
            active_link<=link_command;
            svc_rsp_token_i<=svc_req_token_o;
            svc_rsp_sequence_i<=svc_req_sequence_o;
            svc_rsp_job_i<=svc_req_job_o;
            svc_rsp_epoch_i<=svc_req_epoch_o;
            svc_rsp_task_sequence_i<=svc_req_task_sequence_o;
        end
    end

    wire clk = clk_i;
    wire reset = !rst_ni;
    wire load_valid,load_take,cmd_valid,cmd_take,gate_valid,gate_take;
    wire load_ready,load_done,load_error,cmd_ready,cmd_done,cmd_error,cmd_saturated;
    wire gate_ready,gate_done,gate_error,gate_saturated;
    wire [31:0] load_fields,cmd_fields;
    wire [63:0] cmd_data;
    wire [29:0] gate_fields;
    pj_native_service compute(.clk,.reset,
        .svc_valid(svc_req_valid_o && !link_command),.svc_ready(native_ready),.descriptor(svc_req_descriptor_o),
        .rsp_valid(native_rsp),.rsp_ready(svc_rsp_ready_o && !active_link),
        .status(native_status),.saturated(native_sat),.read_bytes(native_reads),.write_bytes(native_writes),
        .load_valid,.load_ready,.load_done,.load_take,.load_error,.load_fields,
        .cmd_valid,.cmd_ready,.cmd_done,.cmd_take,.cmd_error,.cmd_saturated,.cmd_fields,.cmd_data,
        .gate_valid,.gate_ready,.gate_done,.gate_take,.gate_error,.gate_saturated,.gate_fields,
        .start(),.start_ready(1'b0),.done_take(),.done_valid(1'b0),.done_error(1'b0),
        .join_tag(),.join_fields(),.release_valid(),.release_ready(1'b0));

    wire send_start,send_ready,send_done;
    wire [9:0] source_addr,destination_addr;
    // Only the three transport commands reach this adapter. Its compute ports are idle.
    ucf_native_service #(.LANES(2)) transport_commands(.clk,.reset,
        .svc_valid(svc_req_valid_o && link_command),.svc_ready(link_ready),.descriptor(svc_req_descriptor_o),
        .rsp_valid(link_rsp),.rsp_ready(svc_rsp_ready_o && active_link),
        .status(link_status),.saturated(link_sat),.read_bytes(link_reads),.write_bytes(link_writes),
        .cmd_valid(),.cmd_store(),.done_ready(),.cmd_meta(),.cmd_sources(),.cmd_addresses(),.cmd_dst(),
        .cmd_ready(2'b0),.done_valid(2'b0),.done_error(2'b0),.done_saturated(2'b0),
        .send_start,.send_ready,.send_done,.source_addr,.destination_addr,
        .receive_commit(incoming_ack && incoming_ack_ready),
        .receive_reserved(link_rx_reserved),.receive_address(link_rx_addr));

    wire [1:0] io_req_ready,io_rsp_valid;
    wire [255:0] io_rsp_data;
    wire link_req,link_take;
    wire [9:0] link_addr;
    wire [1:0] io_req_valid={link_req,host_req_valid_i};
    wire [1:0] io_req_write={!SOURCE,host_req_write_i};
    wire [19:0] io_req_addr={link_addr,host_req_address_i};
    wire [255:0] io_req_data={SOURCE ? 128'd0 : incoming_data,host_req_data_i};
    wire [1:0] io_rsp_ready={link_take,host_rsp_ready_i};
    assign host_req_ready_o=io_req_ready[0];
    assign host_rsp_valid_o=io_rsp_valid[0];
    assign host_rsp_data_o=io_rsp_data[127:0];

    if (SOURCE) begin: source
        assign {incoming_ready,incoming_ack}=0;
        stored_link transfer(.clk,.reset,.start(send_start),.ready(send_ready),
            .source_addr,.destination_addr,.done(send_done),
            .tx_req(link_req),.tx_ready(io_req_ready[1]),.tx_addr(link_addr),
            .tx_valid(io_rsp_valid[1]),.tx_take(link_take),.tx_data(io_rsp_data[255:128]),
            .rx_valid(outgoing_valid),.rx_ready(outgoing_ready),.rx_addr(outgoing_addr),.rx_data(outgoing_data),
            .rx_stored(outgoing_ack),.rx_stored_ready(outgoing_ack_ready),
            .sink_reserved(peer_rx_reserved && peer_rx_addr==outgoing_addr));
    end else begin: sink
        assign {outgoing_valid,outgoing_addr,outgoing_data,outgoing_ack_ready,send_ready,send_done}=0;
        wire reserved_match = link_rx_reserved && incoming_addr==link_rx_addr;
        assign link_req=incoming_valid && reserved_match;
        assign link_addr=incoming_addr;
        assign incoming_ready=io_req_ready[1] && reserved_match;
        assign incoming_ack=io_rsp_valid[1];
        assign link_take=incoming_ack_ready;
    end

    pu_p_group block(.clk,.reset,.io_req_valid,.io_req_write,.io_req_addr,.io_req_data,
        .io_req_ready,.io_rsp_valid,.io_rsp_ready,.io_rsp_data,
        .load_valid,.load_ready,.load_done,.load_take,.load_error,
        .load_bank(load_fields[0]),.load_rows(load_fields[4:1]),.load_tiles(load_fields[7:5]),
        .load_a_wide(load_fields[8]),.load_b_wide(load_fields[9]),.load_reuse_b(load_fields[10]),
        .load_a_base(load_fields[20:11]),.load_b_base(load_fields[30:21]),
        .cmd_valid,.cmd_ready,.cmd_op(cmd_fields[3:0]),.cmd_index(cmd_fields[9:4]),.cmd_data,
        .cmd_store(cmd_fields[10]),.cmd_route(1'b0),.cmd_pack16(cmd_fields[11]),.cmd_dst(cmd_fields[21:12]),
        .cmd_done,.cmd_take,.cmd_error,.cmd_saturated,.cmd_result(),
        .gate_valid,.gate_route(1'b0),.gate_ready,.gate_a(gate_fields[9:0]),
        .gate_b(gate_fields[19:10]),.gate_dst(gate_fields[29:20]),
        .gate_done,.gate_take,.gate_error,.gate_saturated,
        .m_to_g_valid(),.m_to_g_data(),.m_to_g_take(1'b0),
        .g_from_m_valid(1'b0),.g_from_m_data(32'b0),.g_from_m_take());

endmodule
