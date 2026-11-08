`timescale 1ns/1ps
module native_control_endpoint #(parameter [7:0] BLOCK=0, parameter integer KIND=0, parameter [31:0] TOPOLOGY_ID=32'h01930011)(
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
    input wire fragment_valid_i,output wire fragment_ready_o,
    input wire [9:0] fragment_address_i,input wire [127:0] fragment_data_i,
    input wire [31:0] fragment_tag_i,input wire [1:0] fragment_slot_i,input wire fragment_last_i,
    output wire fragment_rsp_valid_o,input wire fragment_rsp_ready_i,output wire fragment_error_o,
    output wire native_result_valid_o,input wire native_result_ready_i,
    output wire [511:0] native_result_packet_o,output wire native_pending_o
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
    lc_min_controller #(.BLOCK_ID(BLOCK),.ENABLE_NATIVE(1'b1),.NATIVE_BLOCK_TYPE(8'(KIND)),.NATIVE_TOPOLOGY(TOPOLOGY_ID),.STALL_LIMIT(4096)) control(
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

    wire clk=clk_i,reset=!rst_ni;
    wire [15:0] request_op=svc_req_descriptor_o[32+:16];
    wire [31:0] request_fields=svc_req_descriptor_o[512+:32];
    reg bad_response,join_used;
    reg [31:0] task_job,task_epoch,task_sequence;
    reg [7:0] native_epoch;
    wire legal=(KIND<=2 ? request_op==16'h100 && svc_req_descriptor_o[608+:32]==0 :
                KIND==3 ? request_op>=16'h110 && request_op<=16'h112 :
                (request_op==16'h121 || request_op==16'h120 && !join_used && request_fields[19:10]<=4));
    wire adapter_ready,adapter_valid;
    wire [15:0] adapter_status;
    wire [31:0] adapter_reads,adapter_writes;
    wire adapter_saturated;
    always @* begin
        svc_req_ready_i=!bad_response && adapter_ready;
        svc_rsp_valid_i=bad_response || adapter_valid;
        svc_rsp_status_i=bad_response ? 16'd4 : adapter_status;
        svc_rsp_read_bytes_i=bad_response ? 0 : adapter_reads;
        svc_rsp_write_bytes_i=bad_response ? 0 : adapter_writes;
        svc_rsp_saturated_i=!bad_response && adapter_saturated;
    end
    always @(posedge clk_i)begin
        if(!rst_ni)begin
            bad_response<=0;join_used<=0;native_epoch<=0;task_job<=0;task_epoch<=0;task_sequence<=0;
            svc_rsp_token_i<=0;svc_rsp_sequence_i<=0;svc_rsp_job_i<=0;svc_rsp_epoch_i<=0;svc_rsp_task_sequence_i<=0;
        end else begin
            if(release_valid_i && release_ready_o)native_epoch<=release_epoch_i[7:0];
            if(task_valid_i && task_ready_o && task_packet_i[16+:8]==0)begin
                task_job<=task_packet_i[32+:32];task_epoch<=task_packet_i[64+:32];task_sequence<=task_packet_i[96+:32];join_used<=0;
            end
            if(svc_req_valid_o && svc_req_ready_i)begin
                bad_response<=!legal;
                if(KIND==4 && legal && request_op==16'h120)join_used<=1;
                svc_rsp_token_i<=svc_req_token_o;svc_rsp_sequence_i<=svc_req_sequence_o;
                svc_rsp_job_i<=svc_req_job_o;svc_rsp_epoch_i<=svc_req_epoch_o;svc_rsp_task_sequence_i<=svc_req_task_sequence_o;
            end
            if(bad_response && svc_rsp_ready_o)bad_response<=0;
        end
    end
    wire adapter_request=svc_req_valid_o && legal && !bad_response;
    wire adapter_take=svc_rsp_ready_o && !bad_response;
    generate if(KIND<=2)begin: ucf
        localparam integer LANES=KIND==2 ? 3 : 2;
        wire [LANES-1:0] cmd_valid,cmd_store,done_ready,cmd_ready,done_valid,done_error,done_saturated;
        wire [LANES*64-1:0] cmd_meta;
        wire [LANES*2-1:0] cmd_sources;
        wire [LANES*30-1:0] cmd_addresses;
        wire [LANES*10-1:0] cmd_dst;
        ucf_native_service #(.LANES(LANES)) dispatch(.clk,.reset,.svc_valid(adapter_request),.svc_ready(adapter_ready),
            .descriptor(svc_req_descriptor_o),.rsp_valid(adapter_valid),.rsp_ready(adapter_take),
            .status(adapter_status),.saturated(adapter_saturated),.read_bytes(adapter_reads),.write_bytes(adapter_writes),
            .cmd_valid,.cmd_store,.done_ready,.cmd_meta,.cmd_sources,.cmd_addresses,.cmd_dst,
            .cmd_ready,.done_valid,.done_error,.done_saturated,
            .send_start(),.send_ready(1'b0),.send_done(1'b0),.source_addr(),.destination_addr(),
            .receive_commit(1'b0),.receive_reserved(),.receive_address());
        assign {native_result_valid_o,native_pending_o,fragment_ready_o,fragment_rsp_valid_o,fragment_error_o}=0;
        assign native_result_packet_o=0;
        if(KIND==0)begin: u
            wire [1:0] io_ready,io_response;
            wire [255:0] io_data;
            assign host_req_ready_o=io_ready[0];assign host_rsp_valid_o=io_response[0];assign host_rsp_data_o=io_data[127:0];
            pu_u_group services(.clk,.reset,
                .n_cmd_valid(cmd_valid[1]),.n_cmd_store(cmd_store[1]),.n_cmd_direct(1'b0),.n_done_ready(done_ready[1]),
                .n_cmd_ready(cmd_ready[1]),.n_done_valid(done_valid[1]),.n_done_error(done_error[1]),.n_done_saturated(done_saturated[1]),
                .n_cmd_meta(cmd_meta[103:64]),.n_cmd_sources(cmd_sources[3:2]),.n_cmd_src(cmd_addresses[49:30]),.n_cmd_dst(cmd_dst[19:10]),
                .n_done_data(),.n_to_e_valid(),.n_to_e_ready(1'b0),.n_to_e_data(),
                .e_cmd_valid(cmd_valid[0]),.e_cmd_store(cmd_store[0]),.e_cmd_direct_a(1'b0),.e_done_ready(done_ready[0]),
                .e_cmd_ready(cmd_ready[0]),.e_done_valid(done_valid[0]),.e_done_error(done_error[0]),.e_done_saturated(done_saturated[0]),
                .e_cmd_sources(cmd_sources[1:0]),.e_cmd_op(cmd_meta[3:0]),.e_cmd_shift(cmd_meta[8:4]),
                .e_cmd_src(cmd_addresses[29:0]),.e_cmd_dst(cmd_dst[9:0]),.e_done_data(),
                .e_direct_a_valid(1'b0),.e_direct_a_abort(1'b0),.e_direct_a_ready(),.e_direct_a_data(128'b0),
                .io_req_valid({1'b0,host_req_valid_i}),.io_req_write({1'b0,host_req_write_i}),
                .io_req_addr({10'b0,host_req_address_i}),.io_req_data({128'b0,host_req_data_i}),
                .io_req_ready(io_ready),.io_rsp_valid(io_response),.io_rsp_ready({1'b0,host_rsp_ready_i}),.io_rsp_data(io_data));
        end else begin: cf
            wire rx_ready,rx_response,tx_ready,tx_response;
            wire [127:0] tx_data;
            assign host_req_ready_o=host_req_write_i ? rx_ready : tx_ready;
            assign host_rsp_valid_o=rx_response || tx_response;
            assign host_rsp_data_o=tx_response ? tx_data : 128'b0;
            block_cfj_cf #(.KIND(KIND),.LATE_G_E(1'b0)) services(.clk,.reset,
                .cmd_valid,.cmd_ready,.cmd_meta,.cmd_sources,.cmd_addresses,.cmd_store,.cmd_dst,
                .done_valid,.done_ready,.done_data(),.done_error,.done_saturated,
                .rx_valid(host_req_valid_i && host_req_write_i),.rx_ready,.rx_addr(host_req_address_i),.rx_data(host_req_data_i),
                .rx_stored(rx_response),.rx_stored_ready(host_rsp_ready_i),
                .tx_req(host_req_valid_i && !host_req_write_i),.tx_ready,.tx_addr(host_req_address_i),
                .tx_valid(tx_response),.tx_take(host_rsp_ready_i),.tx_data,
                .late_g_valid(),.late_g_data(),.late_g_take(1'b0),.late_e_valid(1'b0),.late_e_data(32'b0),.late_e_take());
        end
    end else begin: pj
        wire load_valid,load_ready,load_done,load_take,load_error;
        wire cmd_valid,cmd_ready,cmd_done,cmd_take,cmd_error,cmd_saturated;
        wire gate_valid,gate_ready,gate_done,gate_take,gate_error,gate_saturated;
        wire [31:0] load_fields,cmd_fields,join_tag;
        wire [63:0] cmd_data;
        wire [29:0] gate_fields;
        wire start,start_ready,done_take,done_valid,done_error,release_valid,release_ready;
        wire [20:0] join_fields;
        pj_native_service #(.JOIN_BLOCK(KIND==4)) dispatch(.clk,.reset,.svc_valid(adapter_request),.svc_ready(adapter_ready),
            .descriptor(svc_req_descriptor_o),.rsp_valid(adapter_valid),.rsp_ready(adapter_take),
            .status(adapter_status),.saturated(adapter_saturated),.read_bytes(adapter_reads),.write_bytes(adapter_writes),
            .load_valid,.load_ready,.load_done,.load_take,.load_error,.load_fields,
            .cmd_valid,.cmd_ready,.cmd_done,.cmd_take,.cmd_error,.cmd_saturated,.cmd_fields,.cmd_data,
            .gate_valid,.gate_ready,.gate_done,.gate_take,.gate_error,.gate_saturated,.gate_fields,
            .start,.start_ready,.done_take,.done_valid,.done_error,.join_tag,.join_fields,.release_valid,.release_ready);
        if(KIND==3)begin: p
            wire [1:0] io_ready,io_response;
            wire [255:0] io_data;
            assign host_req_ready_o=io_ready[0];assign host_rsp_valid_o=io_response[0];assign host_rsp_data_o=io_data[127:0];
            assign {native_result_valid_o,native_pending_o,fragment_ready_o,fragment_rsp_valid_o,fragment_error_o}=0;
            assign native_result_packet_o=0;
            assign {start_ready,done_valid,done_error,release_ready}=0;
            pu_p_group services(.clk,.reset,
                .io_req_valid({1'b0,host_req_valid_i}),.io_req_write({1'b0,host_req_write_i}),
                .io_req_addr({10'b0,host_req_address_i}),.io_req_data({128'b0,host_req_data_i}),
                .io_req_ready(io_ready),.io_rsp_valid(io_response),.io_rsp_ready({1'b0,host_rsp_ready_i}),.io_rsp_data(io_data),
                .load_valid,.load_ready,.load_done,.load_take,.load_error,
                .load_bank(load_fields[0]),.load_rows(load_fields[4:1]),.load_tiles(load_fields[7:5]),
                .load_a_wide(load_fields[8]),.load_b_wide(load_fields[9]),.load_reuse_b(load_fields[10]),
                .load_a_base(load_fields[20:11]),.load_b_base(load_fields[30:21]),
                .cmd_valid,.cmd_ready,.cmd_op(cmd_fields[3:0]),.cmd_index(cmd_fields[9:4]),.cmd_data,
                .cmd_store(cmd_fields[10]),.cmd_route(1'b0),.cmd_pack16(cmd_fields[11]),.cmd_dst(cmd_fields[21:12]),
                .cmd_done,.cmd_take,.cmd_error,.cmd_saturated,.cmd_result(),
                .gate_valid,.gate_route(1'b0),.gate_ready,.gate_a(gate_fields[9:0]),
                .gate_b(gate_fields[19:10]),.gate_dst(gate_fields[29:20]),.gate_done,.gate_take,.gate_error,.gate_saturated,
                .m_to_g_valid(),.m_to_g_data(),.m_to_g_take(1'b0),.g_from_m_valid(1'b0),.g_from_m_data(32'b0),.g_from_m_take());
        end else begin: j
            wire [1:0] io_ready,io_response;
            wire [255:0] io_data;
            wire out_valid,out_take,out_last;
            wire [127:0] out_data;
            wire [31:0] out_tag;
            wire [9:0] out_index;
            reg [511:0] packet;
            assign {host_req_ready_o,host_rsp_valid_o}=0;assign host_rsp_data_o=0;
            assign fragment_ready_o=io_ready[0];assign fragment_rsp_valid_o=io_response[0];
            assign {load_ready,load_done,load_error,cmd_ready,cmd_done,cmd_error,cmd_saturated,gate_ready,gate_done,gate_error,gate_saturated}=0;
            always @* begin
                packet=0;packet[127:0]=out_data;packet[159:128]=out_tag;packet[169:160]=out_index;packet[170]=out_last;
                packet[202:171]=task_job;packet[234:203]=task_epoch;packet[266:235]=task_sequence;
            end
            native_result_fifo #(.DEPTH(4)) results(.clk_i,.rst_ni,.push_valid_i(out_valid),.push_ready_o(out_take),
                .push_packet_i(packet),.pop_valid_o(native_result_valid_o),.pop_ready_i(native_result_ready_i),
                .pop_packet_o(native_result_packet_o),.pending_o(native_pending_o));
            block_cfj_j #(.LATE_E_WRITEBACK(1'b0)) services(.clk,.reset,
                .io_req_valid({1'b0,fragment_valid_i}),.io_req_write(2'b01),
                .io_req_addr({10'b0,fragment_address_i}),.io_req_data({128'b0,fragment_data_i}),
                .io_req_ready(io_ready),.io_rsp_valid(io_response),.io_rsp_ready({1'b0,fragment_rsp_ready_i}),.io_rsp_data(io_data),
                .active_epoch(native_epoch),.rx_tag(fragment_tag_i),.rx_slot(fragment_slot_i),.rx_last(fragment_last_i),.rx_error(fragment_error_o),
                .start,.start_ready,.join_tag,.join_three(join_fields[20]),.result_addr(join_fields[9:0]),.words(join_fields[19:10]),
                .done_valid,.done_take,.done_error,.out_valid,.out_take,.out_data,.out_tag,.out_index,.out_last,
                .release_valid,.release_ready,.late_e_valid(),.late_e_take(1'b0),.late_e_data(),
                .late_s_valid(1'b0),.late_s_take(),.late_s_data(128'b0));
        end
    end endgenerate
endmodule
