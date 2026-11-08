`timescale 1ns/1ps
module main64_recovery_control #(parameter integer KIND0=0, KIND1=KIND0)(
    input wire halt_i,route_update_i,route_direction_i,
    input wire [9:0] route_base_i,input wire [2:0] route_count_i,input wire [31:0] route_first_i,route_tag_i,
    input wire [7:0] route_stride_i,
    output wire quiescent_o,fault_o,output wire [31:0] observed_reads_o,observed_writes_o,
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
    output wire [31:0] ack_count_o,
    input wire [1:0] fragment_valid_i,
    output wire [1:0] fragment_ready_o,
    input wire [19:0] fragment_address_i,
    input wire [255:0] fragment_data_i,
    input wire [63:0] fragment_tag_i,
    input wire [3:0] fragment_slot_i,
    input wire [1:0] fragment_last_i,
    output wire [1:0] fragment_rsp_valid_o,
    input wire [1:0] fragment_rsp_ready_i,
    output wire [1:0] fragment_error_o,
    output wire [1:0] native_result_valid_o,
    input wire [1:0] native_result_ready_i,
    output wire [1023:0] native_result_packet_o,
    output wire [1:0] native_pending_o
);
    wire [2:0] pm_req_ready_i;
    wire [2:0] pm_rsp_valid_i;
    wire [383:0] pm_rsp_data_i;
    wire [2:0] pm_rsp_error_i;
    wire [2:0] pm_req_valid_o;
    wire [2:0] pm_req_write_o;
    wire [41:0] pm_req_address_o;
    wire [383:0] pm_req_data_o;
    wire [2:0] pm_rsp_ready_o;
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
    reg [1:0] host_pending,fragment_pending,begin_pending;
    reg [31:0] begin_id[0:1];
    wire host_allowed=!run_active && !start_valid_i;
    wire mother_start_ready;
    assign start_ready_o=mother_start_ready && !(|host_pending) && !(|fragment_pending) && !(|native_pending_o) && !run_active;
    assign run_active_o=run_active;
    always @(posedge clk_i) begin
        if(reset) begin image_id0<=0;image_id1<=0;run_active<=0;host_pending<=0;fragment_pending<=0;begin_pending<=0;begin_id[0]<=0;begin_id[1]<=0;end
        else begin
            for(integer i=0;i<2;i=i+1)begin
                if(cfg_req_valid_i[i+1] && cfg_req_ready_o[i+1])begin
                    begin_pending[i]<=cfg_req_op_i[(i+1)*3+:3]==0;
                    begin_id[i]<=cfg_req_image_id_i[(i+1)*32+:32];
                end
                if(cfg_rsp_valid_o[i+1] && cfg_rsp_ready_i[i+1])begin
                    if(begin_pending[i] && cfg_rsp_status_o[(i+1)*16+:16]==0)begin
                        if(i==0)image_id0<=begin_id[i];else image_id1<=begin_id[i];
                    end
                    begin_pending[i]<=0;
                end
                if(fragment_valid_i[i] && fragment_ready_o[i])fragment_pending[i]<=1;
                else if(fragment_rsp_valid_o[i] && fragment_rsp_ready_i[i])fragment_pending[i]<=0;
            end
            if(start_valid_i && start_ready_o) run_active<=1;
            else if(result_valid_o && result_ready_i) run_active<=0;
            for(integer i=0;i<2;i=i+1) begin
                if(host_req_valid_i[i] && host_req_ready_o[i]) host_pending[i]<=1;
                else if(host_rsp_valid_o[i] && host_rsp_ready_i[i]) host_pending[i]<=0;
            end
        end
    end
    wire [1:0] endpoint_safe,endpoint_fault,store_commit,raw_event_valid,raw_event_ready;
    wire [63:0] endpoint_reads,endpoint_writes,task_jobs,task_epochs,task_sequences,join_tags;
    wire [261:0] send_identity,reserve_identity;
    wire [1:0] native_forward_valid,native_forward_ready,native_forward_ack,native_forward_ack_ready;
    wire [19:0] native_forward_address;
    wire [255:0] native_forward_data;
    wire [1:0] native_result_raw_valid,native_result_take;
    wire [1023:0] native_result_raw_packet;
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
    mother_control_64 #(.NATIVE_ABI_ID(32'h01930001)) mother(
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
        .life_o(life_o[0+:4]),
        .seq_o(seq_o[0+:4]),
        .trace_pc_o(mc_trace_pc_o),
        .trace_retire_o(mc_trace_retire_o),
        .trace_opcode_o(mc_trace_opcode_o),
        .trace_pm_owner_o(mc_trace_pm_owner_o),
        .trace_ireg_valid_o(mc_trace_ireg_valid_o),
        .start_valid_i(start_valid_i && !(|host_pending) && !(|fragment_pending) && !(|native_pending_o) && !run_active),
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
    main64_recovery_endpoint #(.BLOCK(8'd0),.KIND(KIND0),.TOPOLOGY_ID(32'h01938000+KIND0*16+KIND1)) local0(
        .halt_i(halt_i),.job_start_i(start_valid_i && start_ready_o),.commit_i(store_commit[1]),
        .safe_o(endpoint_safe[0]),.fault_o(endpoint_fault[0]),
        .observed_reads_o(endpoint_reads[0+:32]),.observed_writes_o(endpoint_writes[0+:32]),
        .send_identity_o(send_identity[0+:131]),.reserve_identity_o(reserve_identity[0+:131]),
        .join_tag_o(join_tags[0+:32]),.task_job_o(task_jobs[0+:32]),
        .task_epoch_o(task_epochs[0+:32]),.task_sequence_o(task_sequences[0+:32]),
        .clk_i(clk_i),
        .rst_ni(core_rst_ni),
        .release_valid_i(release_valid_i[1+:1]),
        .release_sequence_i(release_sequence_i[32+:32]),
        .release_epoch_i(release_epoch_i[32+:32]),
        .deploy_valid_i(effective_deploy),
        .deploy_generation_i(deploy_generation_i),
        .release_ready_o(release_ready_o[1+:1]),
        .poison_o(poison_o[1]),
        .image_valid_o(image_valid_o[1]),
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
        .task_valid_i(local_task_valid[0] && !halt_i),
        .task_packet_i(task_packet),
        .task_credit_i(task_credit),
        .task_ready_o(local_task_ready[0]),
        .event_ready_i(raw_event_ready[0]),
        .event_valid_o(raw_event_valid[0]),
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
        .fragment_valid_i(fragment_valid_i[0+:1]),
        .fragment_ready_o(fragment_ready_o[0+:1]),
        .fragment_address_i(fragment_address_i[0+:10]),
        .fragment_data_i(fragment_data_i[0+:128]),
        .fragment_tag_i(fragment_tag_i[0+:32]),
        .fragment_slot_i(fragment_slot_i[0+:2]),
        .fragment_last_i(fragment_last_i[0+:1]),
        .fragment_rsp_valid_o(fragment_rsp_valid_o[0+:1]),
        .fragment_rsp_ready_i(fragment_rsp_ready_i[0+:1]),
        .fragment_error_o(fragment_error_o[0+:1]),
        .native_result_valid_o(native_result_raw_valid[0]),
        .native_result_ready_i(native_result_take[0]),
        .native_result_packet_o(native_result_raw_packet[0+:512]),
        .native_pending_o(native_pending_o[0+:1]),
.incoming_valid(incoming_valid[0]),
.incoming_ready(incoming_ready[0]),
.incoming_addr(incoming_address[0+:10]),
.incoming_data(incoming_data[0+:128]),
.incoming_ack(incoming_ack[0]),
.incoming_ack_ready(incoming_ack_ready[0]),
.outgoing_valid(native_forward_valid[0]),
.outgoing_ready(native_forward_ready[0]),
.outgoing_addr(native_forward_address[0+:10]),
.outgoing_data(native_forward_data[0+:128]),
.outgoing_ack(native_forward_ack[0]),
.outgoing_ack_ready(native_forward_ack_ready[0]),
.rx_reserved(rx_reserved[0]),
.rx_reserved_addr(rx_address[0+:10]),
.peer_reserved(rx_reserved[1] || halt_i),
.peer_addr(halt_i ? native_forward_address[0+:10] : ((KIND1==3) ? route_base[0]+10'(route_done[0]) : rx_address[10+:10]))
    );
    assign host_req_ready_o[1]=host_ready_raw[1] && host_allowed;
    main64_recovery_endpoint #(.BLOCK(8'd1),.KIND(KIND1),.TOPOLOGY_ID(32'h01938000+KIND0*16+KIND1)) local1(
        .halt_i(halt_i),.job_start_i(start_valid_i && start_ready_o),.commit_i(store_commit[0]),
        .safe_o(endpoint_safe[1]),.fault_o(endpoint_fault[1]),
        .observed_reads_o(endpoint_reads[32+:32]),.observed_writes_o(endpoint_writes[32+:32]),
        .send_identity_o(send_identity[131+:131]),.reserve_identity_o(reserve_identity[131+:131]),
        .join_tag_o(join_tags[32+:32]),.task_job_o(task_jobs[32+:32]),
        .task_epoch_o(task_epochs[32+:32]),.task_sequence_o(task_sequences[32+:32]),
        .clk_i(clk_i),
        .rst_ni(core_rst_ni),
        .release_valid_i(release_valid_i[2+:1]),
        .release_sequence_i(release_sequence_i[64+:32]),
        .release_epoch_i(release_epoch_i[64+:32]),
        .deploy_valid_i(effective_deploy),
        .deploy_generation_i(deploy_generation_i),
        .release_ready_o(release_ready_o[2+:1]),
        .poison_o(poison_o[2]),
        .image_valid_o(image_valid_o[2]),
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
        .task_valid_i(local_task_valid[1] && !halt_i),
        .task_packet_i(task_packet),
        .task_credit_i(task_credit),
        .task_ready_o(local_task_ready[1]),
        .event_ready_i(raw_event_ready[1]),
        .event_valid_o(raw_event_valid[1]),
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
        .fragment_valid_i(fragment_valid_i[1+:1]),
        .fragment_ready_o(fragment_ready_o[1+:1]),
        .fragment_address_i(fragment_address_i[10+:10]),
        .fragment_data_i(fragment_data_i[128+:128]),
        .fragment_tag_i(fragment_tag_i[32+:32]),
        .fragment_slot_i(fragment_slot_i[2+:2]),
        .fragment_last_i(fragment_last_i[1+:1]),
        .fragment_rsp_valid_o(fragment_rsp_valid_o[1+:1]),
        .fragment_rsp_ready_i(fragment_rsp_ready_i[1+:1]),
        .fragment_error_o(fragment_error_o[1+:1]),
        .native_result_valid_o(native_result_raw_valid[1]),
        .native_result_ready_i(native_result_take[1]),
        .native_result_packet_o(native_result_raw_packet[512+:512]),
        .native_pending_o(native_pending_o[1+:1]),
.incoming_valid(incoming_valid[1]),
.incoming_ready(incoming_ready[1]),
.incoming_addr(incoming_address[10+:10]),
.incoming_data(incoming_data[128+:128]),
.incoming_ack(incoming_ack[1]),
.incoming_ack_ready(incoming_ack_ready[1]),
.outgoing_valid(native_forward_valid[1]),
.outgoing_ready(native_forward_ready[1]),
.outgoing_addr(native_forward_address[10+:10]),
.outgoing_data(native_forward_data[128+:128]),
.outgoing_ack(native_forward_ack[1]),
.outgoing_ack_ready(native_forward_ack_ready[1]),
.rx_reserved(rx_reserved[1]),
.rx_reserved_addr(rx_address[10+:10]),
.peer_reserved(rx_reserved[0] || halt_i),
.peer_addr(halt_i ? native_forward_address[10+:10] : ((KIND0==3) ? route_base[1]+10'(route_done[1]) : rx_address[0+:10]))
    );
    for(genvar k=1;k<3;k=k+1)begin: programs
        control_pm #(.USE_SRAM(1'b1)) pm(.clk_i,.rst_ni(core_rst_ni),
            .req_valid_i(pm_req_valid_o[k]),.req_write_i(pm_req_write_o[k]),.req_address_i(pm_req_address_o[k*14+:14]),
            .req_data_i(pm_req_data_o[k*128+:128]),.req_ready_o(pm_req_ready_i[k]),
            .rsp_valid_o(pm_rsp_valid_i[k]),.rsp_ready_i(pm_rsp_ready_o[k]),.rsp_data_o(pm_rsp_data_i[k*128+:128]),.rsp_error_o(pm_rsp_error_i[k]));
    end
    assign {pm_req_valid_o[0],pm_req_write_o[0],pm_rsp_ready_o[0],pm_req_address_o[0+:14],pm_req_data_o[0+:128]}=0;
    assign {pm_req_ready_i[0],pm_rsp_valid_i[0],pm_rsp_error_i[0],pm_rsp_data_i[0+:128]}=0;
    reg [31:0] current_job,current_epoch,current_sequence,current_generation;
    reg [1:0] route_enabled,j_owned;
    reg [9:0] route_base[0:1];reg [2:0] route_count[0:1],route_done[0:1];
    reg [31:0] route_first[0:1],route_tag[0:1];reg [7:0] route_stride[0:1];
    wire [1:0] link_busy,link_fault,link_ack_valid,link_ack_ready,link_abort,link_committed;
    wire [1023:0] ticket,ack_identity;
    reg [511:0] saved_ticket[0:1];
    reg [31:0] commits,acks;
    reg [1:0] bad_ack;
    assign observed_reads_o=endpoint_reads[31:0]+endpoint_reads[63:32];
    assign observed_writes_o=endpoint_writes[31:0]+endpoint_writes[63:32];
    assign quiescent_o=(&endpoint_safe) && !(|link_busy) && !(|host_pending) && !(|fragment_pending);
    assign fault_o=(|endpoint_fault) || (|poison_o) || mc_trace_aborting_o || (|link_fault) || (|bad_ack) || (|bad_j_packet);
    assign ack_rejected_o=|bad_ack;
    assign commit_count_o=commits;assign ack_count_o=acks;
    assign link_pending_o=|native_pending_o || |host_pending || |fragment_pending || |link_busy;
    wire [1:0] bad_j_packet;
    always @(posedge clk_i)begin
        if(reset)begin
            current_job<=0;current_epoch<=0;current_sequence<=0;current_generation<=0;
            route_enabled<=0;j_owned<=0;commits<=0;acks<=0;bad_ack<=0;
            for(integer i=0;i<2;i=i+1)begin
                route_base[i]<=0;route_count[i]<=0;route_done[i]<=0;route_first[i]<=0;route_stride[i]<=0;route_tag[i]<=0;saved_ticket[i]<=0;
            end
        end else begin
            if(route_update_i)begin
                route_enabled[route_direction_i]<=route_count_i!=0;
                route_base[route_direction_i]<=route_base_i;route_count[route_direction_i]<=route_count_i;
                route_first[route_direction_i]<=route_first_i;route_stride[route_direction_i]<=route_stride_i;route_tag[route_direction_i]<=route_tag_i;
            end
            if(start_valid_i && start_ready_o)begin
                current_job<=start_job_i;current_epoch<=start_epoch_i;current_sequence<=start_sequence_i;current_generation<=start_generation_i;
                route_done[0]<=0;route_done[1]<=0;commits<=0;acks<=0;bad_ack<=0;
            end else begin
                commits<=commits+32'(store_commit[0])+32'(store_commit[1]);
                acks<=acks+32'(link_ack_valid[0] && link_ack_ready[0] && link_committed[0])+32'(link_ack_valid[1] && link_ack_ready[1] && link_committed[1]);
            end
            for(integer i=0;i<2;i=i+1)begin
                if(forward_valid[i] && forward_ready[i])begin saved_ticket[i]<=ticket[i*512+:512];if((i==0 ? KIND0 : KIND1)==4)j_owned[i]<=1;end
                if(link_ack_valid[i] && ack_identity[i*512+:512]!=saved_ticket[i])bad_ack[i]<=1;
                if(link_ack_valid[i] && link_ack_ready[i])begin
                    j_owned[i]<=0;
                    if(link_committed[i])route_done[i]<=route_done[i]+1'b1;
                end
            end
        end
    end
    for(genvar k=0;k<2;k=k+1)begin: links
        localparam integer KIND=k==0 ? KIND0 : KIND1;
        localparam integer PEER=k==0 ? KIND1 : KIND0;
        wire routed=route_enabled[k] && route_done[k]<route_count[k];
        wire [511:0] jpacket=native_result_raw_packet[k*512+:512];
        wire [130:0] identity=send_identity[k*131+:131];
        wire [130:0] destination_identity=PEER==3 ? {current_job,current_epoch,32'b0,32'b0,3'b0} : reserve_identity[(1-k)*131+:131];
        wire [31:0] expected_sequence=route_first[k]+32'(route_done[k])*32'(route_stride[k]);
        wire jgood=jpacket[202:171]==current_job && jpacket[234:203]==current_epoch &&
                   jpacket[266:235]==task_sequences[k*32+:32] && jpacket[159:128]==route_tag[k] &&
                   join_tags[k*32+:32]==route_tag[k] && jpacket[169:160]==10'(route_done[k]) &&
                   jpacket[170]==(route_done[k]+1'b1==route_count[k]);
        assign bad_j_packet[k]=KIND==4 && run_active && routed && native_result_raw_valid[k] && !jgood;
        assign forward_valid[k]=KIND==4 ? routed && !j_owned[k] && native_result_raw_valid[k] && jgood && !halt_i :
            native_forward_valid[k] && (run_active || halt_i);
        assign forward_address[k*10+:10]=KIND==4 ? route_base[k]+10'(route_done[k]) : native_forward_address[k*10+:10];
        assign forward_data[k*128+:128]=KIND==4 ? jpacket[127:0] : native_forward_data[k*128+:128];
        assign native_forward_ready[k]=KIND!=4 && forward_ready[k];
        assign native_forward_ack[k]=KIND!=4 && link_ack_valid[k] && ack_identity[k*512+:512]==saved_ticket[k];
        assign link_ack_ready[k]=(KIND==4 ? j_owned[k] : native_forward_ack_ready[k]) && ack_identity[k*512+:512]==saved_ticket[k];
        assign native_result_take[k]=KIND==4 && route_enabled[k] ? (j_owned[k] && link_ack_valid[k] && link_ack_ready[k]) : native_result_ready_i[k];
        assign native_result_valid_o[k]=native_result_raw_valid[k] && !route_enabled[k];
        assign native_result_packet_o[k*512+:512]=native_result_raw_packet[k*512+:512];
        wire event_blocked=KIND==4 && route_enabled[k] && route_done[k]<route_count[k] && return_packets[k*512+16+:8]>=2 && !halt_i;
        assign local_event_valid[k]=raw_event_valid[k] && !event_blocked;
        assign raw_event_ready[k]=local_event_ready[k] && !event_blocked;
        wire source_legal=routed && identity[130:99]==current_job && identity[98:67]==current_epoch &&
            identity[66:35]==task_sequences[k*32+:32] && identity[34:3]==expected_sequence && identity[2:0]==0 &&
            forward_address[k*10+:10]==route_base[k]+10'(route_done[k]);
        wire destination_reserved=PEER==3 ? life_o[(2-k)*4+:4]==5 :
            rx_reserved[1-k] && rx_address[(1-k)*10+:10]==forward_address[k*10+:10] &&
            destination_identity[130:99]==current_job && destination_identity[98:67]==current_epoch &&
            destination_identity[66:35]==task_sequences[(1-k)*32+:32] && destination_identity[2:0]==0 &&
            destination_identity[34:3]==(route_done[k]==0 ? 32'd0 : route_first[1-k]+32'd2);
        reg [511:0] formed_ticket;
        always @*begin
            formed_ticket=0;formed_ticket[130:0]=identity;formed_ticket[261:131]=destination_identity;
            formed_ticket[293:262]=current_generation;formed_ticket[325:294]=current_sequence;
            formed_ticket[357:326]=32'h01938000+KIND0*16+KIND1;
            formed_ticket[389:358]=k==0 ? image_id0 : image_id1;formed_ticket[421:390]=k==0 ? image_id1 : image_id0;
            formed_ticket[429:422]=8'(k);formed_ticket[437:430]=8'(1-k);
            formed_ticket[447:438]=forward_address[k*10+:10];formed_ticket[479:448]=KIND==4 ? route_tag[k] : 32'd0;
            formed_ticket[489:480]=10'(route_done[k]);
        end
        assign ticket[k*512+:512]=formed_ticket;
        main64_guarded_link transfer(.clk_i,.rst_ni(core_rst_ni),.halt_i,.source_valid(forward_valid[k]),.source_ready(forward_ready[k]),
            .source_legal,.source_address(forward_address[k*10+:10]),.source_data(forward_data[k*128+:128]),.source_identity(ticket[k*512+:512]),
            .destination_reserved,.destination_valid(incoming_valid[1-k]),.destination_ready(incoming_ready[1-k]),
            .destination_address(incoming_address[(1-k)*10+:10]),.destination_data(incoming_data[(1-k)*128+:128]),
            .destination_ack(incoming_ack[1-k]),.destination_ack_ready(incoming_ack_ready[1-k]),
            .ack_valid(link_ack_valid[k]),.ack_ready(link_ack_ready[k]),.ack_identity(ack_identity[k*512+:512]),
            .ack_abort(link_abort[k]),.ack_committed(link_committed[k]),.store_commit(store_commit[k]),.busy(link_busy[k]),.fault_o(link_fault[k]));
    end
endmodule
