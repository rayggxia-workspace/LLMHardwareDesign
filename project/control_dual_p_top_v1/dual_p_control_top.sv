`timescale 1ns/1ps
// Candidate single-clock control top, fixed P0 -> P1, external program memories.
module dual_p_control_top(
    input wire clk_i,
    input wire rst_ni,
    input wire deploy_valid_i,
    input wire [31:0] deploy_generation_i,
    input wire [2:0] release_valid_i,
    input wire [95:0] release_sequence_i,
    input wire [95:0] release_epoch_i,
    output wire [2:0] release_ready_o,
    output wire [2:0] poison_o,
    output wire [2:0] image_valid_o,
    input wire [2:0] cfg_req_valid_i,
    input wire [8:0] cfg_req_op_i,
    input wire [95:0] cfg_req_generation_i,
    input wire [41:0] cfg_req_address_i,
    input wire [383:0] cfg_req_data_i,
    input wire [47:0] cfg_req_total_bytes_i,
    input wire [95:0] cfg_req_image_id_i,
    input wire [95:0] cfg_req_topology_id_i,
    input wire [95:0] cfg_req_abi_id_i,
    input wire [95:0] cfg_req_capacity_id_i,
    input wire [2:0] cfg_req_proof_i,
    input wire [2:0] cfg_rsp_ready_i,
    output wire [2:0] cfg_req_ready_o,
    output wire [2:0] cfg_rsp_valid_o,
    output wire [47:0] cfg_rsp_status_o,
    output wire [383:0] cfg_rsp_data_o,
    output wire [95:0] cfg_rsp_generation_o,
    input wire [2:0] pm_req_ready_i,
    input wire [2:0] pm_rsp_valid_i,
    input wire [383:0] pm_rsp_data_i,
    input wire [2:0] pm_rsp_error_i,
    output wire [2:0] pm_req_valid_o,
    output wire [2:0] pm_req_write_o,
    output wire [41:0] pm_req_address_o,
    output wire [383:0] pm_req_data_o,
    output wire [2:0] pm_rsp_ready_o,
    output wire [11:0] life_o,
    output wire [11:0] seq_o,
    input wire start_valid_i,
    input wire start_credit_i,
    input wire [31:0] start_job_i,
    input wire [31:0] start_epoch_i,
    input wire [31:0] start_sequence_i,
    input wire [31:0] start_generation_i,
    input wire [255:0] start_args_i,
    output wire start_ready_o,
    output wire result_valid_o,
    input wire result_ready_i,
    output wire [31:0] result_job_o,
    output wire [31:0] result_epoch_o,
    output wire [31:0] result_sequence_o,
    output wire [15:0] result_status_o,
    output wire [31:0] result_error_pc_o,
    output wire [7:0] result_source_o,
    output wire [31:0] result_child_error_pc_o,
    output wire [31:0] result_failed_task_sequence_o,
    output wire [31:0] result_confirmed_read_bytes_o,
    output wire [31:0] result_confirmed_write_bytes_o,
    output wire result_counter_overflow_o,
    output wire result_saturated_o,
    input wire [1:0] host_req_valid_i,
    input wire [1:0] host_req_write_i,
    input wire [19:0] host_req_address_i,
    input wire [255:0] host_req_data_i,
    output wire [1:0] host_req_ready_o,
    output wire [1:0] host_rsp_valid_o,
    input wire [1:0] host_rsp_ready_i,
    output wire [255:0] host_rsp_data_o,
    output wire reset_ready_o,
    output wire deployment_ready_o,
    output wire run_active_o,
    output wire link_pending_o,
    output wire ack_rejected_o,
    output wire [31:0] commit_count_o,
    output wire [31:0] ack_count_o
);
    (* async_reg="true" *) reg [1:0] reset_release;
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) reset_release<=0;
        else reset_release<={reset_release[0],1'b1};
    end
    wire core_rst_ni=reset_release[1];
    wire reset=!core_rst_ni;
    assign reset_ready_o=core_rst_ni;
    wire prepared_cohort=(life_o[0+:4]>=4 && life_o[0+:4]<=7) &&
        (life_o[4+:4]>=4 && life_o[4+:4]<=7) && (life_o[8+:4]>=4 && life_o[8+:4]<=7);
    assign deployment_ready_o=core_rst_ni && prepared_cohort && !(|poison_o);
    wire effective_deploy=deploy_valid_i && deployment_ready_o;
    reg [31:0] image_id0,image_id1;
    reg run_active;
    reg [1:0] host_pending;
    wire host_allowed=!run_active && !start_valid_i;
    wire mother_start_ready;
    assign start_ready_o=mother_start_ready && !(|host_pending) && !run_active;
    assign run_active_o=run_active;
    always @(posedge clk_i) begin
        if(reset) begin image_id0<=0;image_id1<=0;run_active<=0;host_pending<=0;end
        else begin
            if(cfg_req_valid_i[1] && cfg_req_ready_o[1] && cfg_req_op_i[3+:3]==0)
                image_id0<=cfg_req_image_id_i[32+:32];
            if(cfg_req_valid_i[2] && cfg_req_ready_o[2] && cfg_req_op_i[6+:3]==0)
                image_id1<=cfg_req_image_id_i[64+:32];
            if(start_valid_i && start_ready_o) run_active<=1;
            else if(result_valid_o && result_ready_i) run_active<=0;
            for(integer i=0;i<2;i=i+1) begin
                if(host_req_valid_i[i] && host_req_ready_o[i]) host_pending[i]<=1;
                else if(host_rsp_valid_o[i] && host_rsp_ready_i[i]) host_pending[i]<=0;
            end
        end
    end
    wire [31:0] mc_trace_pc_o;
    wire mc_trace_retire_o;
    wire [7:0] mc_trace_opcode_o;
    wire [1:0] mc_trace_pm_owner_o;
    wire mc_trace_ireg_valid_o;
    wire mc_task_valid_o;
    wire mc_task_ready_i;
    wire [7:0] mc_task_target_o;
    wire mc_task_credit_o;
    wire [511:0] mc_task_packet_o;
    wire mc_return_valid_i;
    wire mc_return_ready_o;
    wire [511:0] mc_return_packet_i;
    wire [7:0] mc_trace_live_tokens_o;
    wire [1:0] mc_trace_block_active_o;
    wire [1:0] mc_trace_terminal_full_o;
    wire [1:0] mc_trace_READY_full_o;
    wire mc_trace_aborting_o;
    mc_min_controller #(.STALL_LIMIT(4096),.NATIVE_ABI_ID(32'h01790160)) mother(
        .clk_i(clk_i),
        .rst_ni(core_rst_ni),
        .release_valid_i(release_valid_i[0+:1]),
        .release_sequence_i(release_sequence_i[0+:32]),
        .release_epoch_i(release_epoch_i[0+:32]),
        .deploy_valid_i(effective_deploy),
        .deploy_generation_i(deploy_generation_i),
        .release_ready_o(release_ready_o[0+:1]),
        .poison_o(poison_o[0+:1]),
        .image_valid_o(image_valid_o[0+:1]),
        .cfg_req_valid_i(cfg_req_valid_i[0+:1]),
        .cfg_req_op_i(cfg_req_op_i[0+:3]),
        .cfg_req_generation_i(cfg_req_generation_i[0+:32]),
        .cfg_req_address_i(cfg_req_address_i[0+:14]),
        .cfg_req_data_i(cfg_req_data_i[0+:128]),
        .cfg_req_total_bytes_i(cfg_req_total_bytes_i[0+:16]),
        .cfg_req_image_id_i(cfg_req_image_id_i[0+:32]),
        .cfg_req_topology_id_i(cfg_req_topology_id_i[0+:32]),
        .cfg_req_abi_id_i(cfg_req_abi_id_i[0+:32]),
        .cfg_req_capacity_id_i(cfg_req_capacity_id_i[0+:32]),
        .cfg_req_proof_i(cfg_req_proof_i[0+:1]),
        .cfg_rsp_ready_i(cfg_rsp_ready_i[0+:1]),
        .cfg_req_ready_o(cfg_req_ready_o[0+:1]),
        .cfg_rsp_valid_o(cfg_rsp_valid_o[0+:1]),
        .cfg_rsp_status_o(cfg_rsp_status_o[0+:16]),
        .cfg_rsp_data_o(cfg_rsp_data_o[0+:128]),
        .cfg_rsp_generation_o(cfg_rsp_generation_o[0+:32]),
        .pm_req_ready_i(pm_req_ready_i[0+:1]),
        .pm_rsp_valid_i(pm_rsp_valid_i[0+:1]),
        .pm_rsp_data_i(pm_rsp_data_i[0+:128]),
        .pm_rsp_error_i(pm_rsp_error_i[0+:1]),
        .pm_req_valid_o(pm_req_valid_o[0+:1]),
        .pm_req_write_o(pm_req_write_o[0+:1]),
        .pm_req_address_o(pm_req_address_o[0+:14]),
        .pm_req_data_o(pm_req_data_o[0+:128]),
        .pm_rsp_ready_o(pm_rsp_ready_o[0+:1]),
        .life_o(life_o[0+:4]),
        .seq_o(seq_o[0+:4]),
        .trace_pc_o(mc_trace_pc_o),
        .trace_retire_o(mc_trace_retire_o),
        .trace_opcode_o(mc_trace_opcode_o),
        .trace_pm_owner_o(mc_trace_pm_owner_o),
        .trace_ireg_valid_o(mc_trace_ireg_valid_o),
        .start_valid_i(start_valid_i && !(|host_pending) && !run_active),
        .start_credit_i(start_credit_i),
        .start_job_i(start_job_i),
        .start_epoch_i(start_epoch_i),
        .start_sequence_i(start_sequence_i),
        .start_generation_i(start_generation_i),
        .start_args_i(start_args_i),
        .local_image_id0_i(image_id0),
        .local_image_id1_i(image_id1),
        .local_enabled_i(2'b11),
        .start_ready_o(mother_start_ready),
        .task_valid_o(mc_task_valid_o),
        .task_ready_i(mc_task_ready_i),
        .task_target_o(mc_task_target_o),
        .task_credit_o(mc_task_credit_o),
        .task_packet_o(mc_task_packet_o),
        .return_valid_i(mc_return_valid_i),
        .return_ready_o(mc_return_ready_o),
        .return_packet_i(mc_return_packet_i),
        .result_valid_o(result_valid_o),
        .result_ready_i(result_ready_i),
        .result_job_o(result_job_o),
        .result_epoch_o(result_epoch_o),
        .result_sequence_o(result_sequence_o),
        .result_status_o(result_status_o),
        .result_error_pc_o(result_error_pc_o),
        .result_source_o(result_source_o),
        .result_child_error_pc_o(result_child_error_pc_o),
        .result_failed_task_sequence_o(result_failed_task_sequence_o),
        .result_confirmed_read_bytes_o(result_confirmed_read_bytes_o),
        .result_confirmed_write_bytes_o(result_confirmed_write_bytes_o),
        .result_counter_overflow_o(result_counter_overflow_o),
        .result_saturated_o(result_saturated_o),
        .trace_live_tokens_o(mc_trace_live_tokens_o),
        .trace_block_active_o(mc_trace_block_active_o),
        .trace_terminal_full_o(mc_trace_terminal_full_o),
        .trace_READY_full_o(mc_trace_READY_full_o),
        .trace_aborting_o(mc_trace_aborting_o)
    );
    wire [1:0] local_task_valid,local_task_ready,local_event_valid,local_event_ready;
    wire task_credit;
    wire [511:0] task_packet;
    wire [1023:0] return_packets;
    two_local_link management(.clk_i,.rst_ni(core_rst_ni),
        .task_valid_i(mc_task_valid_o),.task_credit_i(mc_task_credit_o),
        .task_target_i(mc_task_target_o),.task_packet_i(mc_task_packet_o),.task_ready_o(mc_task_ready_i),
        .local_task_valid_o(local_task_valid),.local_task_credit_o(task_credit),.local_task_packet_o(task_packet),
        .local_task_ready_i(local_task_ready),.local_return_valid_i(local_event_valid),
        .local_return_packet_i(return_packets),.local_return_ready_o(local_event_ready),
        .return_valid_o(mc_return_valid_i),.return_packet_o(mc_return_packet_i),.return_ready_i(mc_return_ready_o));
    wire [1:0] rx_reserved,forward_valid,forward_ready,forward_ack,forward_ack_ready;
    wire [1:0] incoming_valid,incoming_ready,incoming_ack,incoming_ack_ready;
    wire [19:0] rx_address,forward_address,incoming_address;
    wire [255:0] forward_data,forward_identity,incoming_data;
    wire [1:0] host_ready_raw;
    assign host_req_ready_o[0]=host_ready_raw[0] && host_allowed;
    p_control_endpoint #(.BLOCK(8'd0)) p0(
        .clk_i(clk_i),
        .rst_ni(core_rst_ni),
        .release_valid_i(release_valid_i[1+:1]),
        .release_sequence_i(release_sequence_i[32+:32]),
        .release_epoch_i(release_epoch_i[32+:32]),
        .deploy_valid_i(effective_deploy),
        .deploy_generation_i(deploy_generation_i),
        .release_ready_o(release_ready_o[1+:1]),
        .poison_o(poison_o[1+:1]),
        .image_valid_o(image_valid_o[1+:1]),
        .cfg_req_valid_i(cfg_req_valid_i[1+:1]),
        .cfg_req_op_i(cfg_req_op_i[3+:3]),
        .cfg_req_generation_i(cfg_req_generation_i[32+:32]),
        .cfg_req_address_i(cfg_req_address_i[14+:14]),
        .cfg_req_data_i(cfg_req_data_i[128+:128]),
        .cfg_req_total_bytes_i(cfg_req_total_bytes_i[16+:16]),
        .cfg_req_image_id_i(cfg_req_image_id_i[32+:32]),
        .cfg_req_topology_id_i(cfg_req_topology_id_i[32+:32]),
        .cfg_req_abi_id_i(cfg_req_abi_id_i[32+:32]),
        .cfg_req_capacity_id_i(cfg_req_capacity_id_i[32+:32]),
        .cfg_req_proof_i(cfg_req_proof_i[1+:1]),
        .cfg_rsp_ready_i(cfg_rsp_ready_i[1+:1]),
        .cfg_req_ready_o(cfg_req_ready_o[1+:1]),
        .cfg_rsp_valid_o(cfg_rsp_valid_o[1+:1]),
        .cfg_rsp_status_o(cfg_rsp_status_o[16+:16]),
        .cfg_rsp_data_o(cfg_rsp_data_o[128+:128]),
        .cfg_rsp_generation_o(cfg_rsp_generation_o[32+:32]),
        .pm_req_ready_i(pm_req_ready_i[1+:1]),
        .pm_rsp_valid_i(pm_rsp_valid_i[1+:1]),
        .pm_rsp_data_i(pm_rsp_data_i[128+:128]),
        .pm_rsp_error_i(pm_rsp_error_i[1+:1]),
        .pm_req_valid_o(pm_req_valid_o[1+:1]),
        .pm_req_write_o(pm_req_write_o[1+:1]),
        .pm_req_address_o(pm_req_address_o[14+:14]),
        .pm_req_data_o(pm_req_data_o[128+:128]),
        .pm_rsp_ready_o(pm_rsp_ready_o[1+:1]),
        .task_valid_i(local_task_valid[0]),
        .task_packet_i(task_packet),
        .task_credit_i(task_credit),
        .task_ready_o(local_task_ready[0]),
        .event_ready_i(local_event_ready[0]),
        .event_valid_o(local_event_valid[0]),
        .event_packet_o(return_packets[0+:512]),
        .life_o(life_o[4+:4]),
        .seq_o(seq_o[4+:4]),
        .host_req_valid_i(host_req_valid_i[0] && host_allowed),
        .host_req_write_i(host_req_write_i[0+:1]),
        .host_req_address_i(host_req_address_i[0+:10]),
        .host_req_data_i(host_req_data_i[0+:128]),
        .host_req_ready_o(host_ready_raw[0]),
        .host_rsp_valid_o(host_rsp_valid_o[0+:1]),
        .host_rsp_ready_i(host_rsp_ready_i[0+:1]),
        .host_rsp_data_o(host_rsp_data_o[0+:128]),
        .link_rx_reserved(rx_reserved[0]),
        .link_rx_addr(rx_address[0+:10]),
        .peer_rx_reserved(rx_reserved[1]),
        .peer_rx_addr(rx_address[10+:10]),
        .outgoing_valid(forward_valid[0+:1]),
        .outgoing_ready(forward_ready[0+:1]),
        .outgoing_addr(forward_address[0+:10]),
        .outgoing_data(forward_data[0+:128]),
        .outgoing_ack(forward_ack[0+:1]),
        .outgoing_ack_ready(forward_ack_ready[0+:1]),
        .outgoing_identity(forward_identity[0+:128]),
        .incoming_valid(incoming_valid[0+:1]),
        .incoming_ready(incoming_ready[0+:1]),
        .incoming_addr(incoming_address[0+:10]),
        .incoming_data(incoming_data[0+:128]),
        .incoming_ack(incoming_ack[0+:1]),
        .incoming_ack_ready(incoming_ack_ready[0+:1])
    );
    assign host_req_ready_o[1]=host_ready_raw[1] && host_allowed;
    p_control_endpoint #(.BLOCK(8'd1)) p1(
        .clk_i(clk_i),
        .rst_ni(core_rst_ni),
        .release_valid_i(release_valid_i[2+:1]),
        .release_sequence_i(release_sequence_i[64+:32]),
        .release_epoch_i(release_epoch_i[64+:32]),
        .deploy_valid_i(effective_deploy),
        .deploy_generation_i(deploy_generation_i),
        .release_ready_o(release_ready_o[2+:1]),
        .poison_o(poison_o[2+:1]),
        .image_valid_o(image_valid_o[2+:1]),
        .cfg_req_valid_i(cfg_req_valid_i[2+:1]),
        .cfg_req_op_i(cfg_req_op_i[6+:3]),
        .cfg_req_generation_i(cfg_req_generation_i[64+:32]),
        .cfg_req_address_i(cfg_req_address_i[28+:14]),
        .cfg_req_data_i(cfg_req_data_i[256+:128]),
        .cfg_req_total_bytes_i(cfg_req_total_bytes_i[32+:16]),
        .cfg_req_image_id_i(cfg_req_image_id_i[64+:32]),
        .cfg_req_topology_id_i(cfg_req_topology_id_i[64+:32]),
        .cfg_req_abi_id_i(cfg_req_abi_id_i[64+:32]),
        .cfg_req_capacity_id_i(cfg_req_capacity_id_i[64+:32]),
        .cfg_req_proof_i(cfg_req_proof_i[2+:1]),
        .cfg_rsp_ready_i(cfg_rsp_ready_i[2+:1]),
        .cfg_req_ready_o(cfg_req_ready_o[2+:1]),
        .cfg_rsp_valid_o(cfg_rsp_valid_o[2+:1]),
        .cfg_rsp_status_o(cfg_rsp_status_o[32+:16]),
        .cfg_rsp_data_o(cfg_rsp_data_o[256+:128]),
        .cfg_rsp_generation_o(cfg_rsp_generation_o[64+:32]),
        .pm_req_ready_i(pm_req_ready_i[2+:1]),
        .pm_rsp_valid_i(pm_rsp_valid_i[2+:1]),
        .pm_rsp_data_i(pm_rsp_data_i[256+:128]),
        .pm_rsp_error_i(pm_rsp_error_i[2+:1]),
        .pm_req_valid_o(pm_req_valid_o[2+:1]),
        .pm_req_write_o(pm_req_write_o[2+:1]),
        .pm_req_address_o(pm_req_address_o[28+:14]),
        .pm_req_data_o(pm_req_data_o[256+:128]),
        .pm_rsp_ready_o(pm_rsp_ready_o[2+:1]),
        .task_valid_i(local_task_valid[1]),
        .task_packet_i(task_packet),
        .task_credit_i(task_credit),
        .task_ready_o(local_task_ready[1]),
        .event_ready_i(local_event_ready[1]),
        .event_valid_o(local_event_valid[1]),
        .event_packet_o(return_packets[512+:512]),
        .life_o(life_o[8+:4]),
        .seq_o(seq_o[8+:4]),
        .host_req_valid_i(host_req_valid_i[1] && host_allowed),
        .host_req_write_i(host_req_write_i[1+:1]),
        .host_req_address_i(host_req_address_i[10+:10]),
        .host_req_data_i(host_req_data_i[128+:128]),
        .host_req_ready_o(host_ready_raw[1]),
        .host_rsp_valid_o(host_rsp_valid_o[1+:1]),
        .host_rsp_ready_i(host_rsp_ready_i[1+:1]),
        .host_rsp_data_o(host_rsp_data_o[128+:128]),
        .link_rx_reserved(rx_reserved[1]),
        .link_rx_addr(rx_address[10+:10]),
        .peer_rx_reserved(rx_reserved[0]),
        .peer_rx_addr(rx_address[0+:10]),
        .outgoing_valid(forward_valid[1+:1]),
        .outgoing_ready(forward_ready[1+:1]),
        .outgoing_addr(forward_address[10+:10]),
        .outgoing_data(forward_data[128+:128]),
        .outgoing_ack(forward_ack[1+:1]),
        .outgoing_ack_ready(forward_ack_ready[1+:1]),
        .outgoing_identity(forward_identity[128+:128]),
        .incoming_valid(incoming_valid[1+:1]),
        .incoming_ready(incoming_ready[1+:1]),
        .incoming_addr(incoming_address[10+:10]),
        .incoming_data(incoming_data[128+:128]),
        .incoming_ack(incoming_ack[1+:1]),
        .incoming_ack_ready(incoming_ack_ready[1+:1])
    );
    wire raw_ack_valid,raw_ack_ready,store_commit,arm_ready,buffer_ready;
    wire [127:0] returned_identity;
    wire guarded_done,guard_busy,word_busy;
    assign link_pending_o=word_busy || guard_busy;
    assign forward_ready[0]=buffer_ready && arm_ready;
    assign forward_ack[0]=guarded_done;
    assign forward_ready[1]=0;
    assign forward_ack[1]=0;
    assign incoming_valid[0]=0;
    assign incoming_address[0+:10]=0;
    assign incoming_data[0+:128]=0;
    assign incoming_ack_ready[0]=0;
    p_word_link data_link(.clk(clk_i),.reset,
        .source_valid(forward_valid[0] && arm_ready),.source_ready(buffer_ready),
        .source_address(forward_address[0+:10]),.source_data(forward_data[0+:128]),
        .source_identity(forward_identity[0+:128]),
        .destination_reserved(rx_reserved[1]),.destination_reserved_address(rx_address[10+:10]),
        .destination_valid(incoming_valid[1]),.destination_ready(incoming_ready[1]),
        .destination_address(incoming_address[10+:10]),.destination_data(incoming_data[128+:128]),
        .destination_ack(incoming_ack[1]),.destination_ack_ready(incoming_ack_ready[1]),
        .ack_valid(raw_ack_valid),.ack_ready(raw_ack_ready),.ack_identity(returned_identity),
        .store_commit,.busy(word_busy));
    p_stored_ack_guard #(.ID_BITS(128)) completion(.clk(clk_i),.reset,
        .arm_valid(forward_valid[0] && forward_ready[0]),.arm_ready,
        .arm_identity(forward_identity[0+:128]),.store_commit,
        .ack_valid(raw_ack_valid),.ack_ready(raw_ack_ready),.ack_identity(returned_identity),
        .done_valid(guarded_done),.done_ready(forward_ack_ready[0]),
        .rejected(ack_rejected_o),.busy(guard_busy));
    reg [31:0] commits,acks;
    assign commit_count_o=commits;
    assign ack_count_o=acks;
    always @(posedge clk_i) begin
        if(reset) begin commits<=0;acks<=0;end
        else begin
            if(store_commit) commits<=commits+1;
            if(guarded_done && forward_ack_ready[0]) acks<=acks+1;
        end
    end
endmodule
