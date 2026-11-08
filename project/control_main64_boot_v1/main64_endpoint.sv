`timescale 1ns/1ps
module main64_endpoint #(parameter [7:0] BLOCK=0, parameter integer KIND=0, parameter [31:0] TOPOLOGY_ID=32'h01930011)(
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
    output wire [511:0] native_result_packet_o,output wire native_pending_o,
    input wire incoming_valid, output wire incoming_ready,
    input wire [9:0] incoming_addr, input wire [127:0] incoming_data,
    output wire incoming_ack, input wire incoming_ack_ready,
    output wire outgoing_valid, input wire outgoing_ready,
    output wire [9:0] outgoing_addr, output wire [127:0] outgoing_data,
    input wire outgoing_ack, output wire outgoing_ack_ready,
    output wire rx_reserved, output wire [9:0] rx_reserved_addr,
    input wire peer_reserved, input wire [9:0] peer_addr
);
    wire reset=!rst_ni;
    reg [31:0] task_job,task_epoch,task_sequence;
    reg [7:0] native_epoch;
    reg tx_owned;
    always @(posedge clk_i) begin
        if(reset) begin task_job<=0;task_epoch<=0;task_sequence<=0;native_epoch<=0;tx_owned<=0;end
        else begin
            if(release_valid_i && release_ready_o) native_epoch<=release_epoch_i[7:0];
            if(task_valid_i && task_ready_o && task_packet_i[16+:8]==0)begin
                task_job<=task_packet_i[32+:32];task_epoch<=task_packet_i[64+:32];task_sequence<=task_packet_i[96+:32];
            end
            if(outgoing_valid && outgoing_ready)tx_owned<=1;
            if(outgoing_ack && outgoing_ack_ready)tx_owned<=0;
        end
    end
    generate
    if(KIND==0)begin: u
    assign {fragment_ready_o,fragment_rsp_valid_o,fragment_error_o,native_result_valid_o}=0;
    assign native_result_packet_o=0;
    assign native_pending_o=tx_owned || outgoing_valid || incoming_ack;
    wire data_ready,data_stored,route_valid,route_ready;
    wire [127:0] route_data;
    wire host_write=host_req_valid_i && host_req_write_i;
    assign host_req_ready_o=host_req_write_i && data_ready;
    assign host_rsp_valid_o=data_stored && !incoming_valid;
    assign host_rsp_data_o=0;
    assign incoming_ready=data_ready && !host_write;
    assign incoming_ack=data_stored && !host_write;
r82_u_pu_u_controlled_64 implementation(
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
    .event_ready_i(event_ready_i),
    .event_valid_o(event_valid_o),
    .event_packet_o(event_packet_o),
    .life_o(life_o),
    .seq_o(seq_o),
    .clk(clk_i),
    .block_id_i(BLOCK),
    .topology_id_i(TOPOLOGY_ID),
    .late_path_enable(1'b1),
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
    .incoming_valid(host_write || incoming_valid),
    .incoming_ready(data_ready),
    .incoming_addr(host_write ? host_req_address_i : incoming_addr),
    .incoming_data(host_write ? host_req_data_i : incoming_data),
    .incoming_ack(data_stored),
    .incoming_ack_ready(host_rsp_ready_i || incoming_ack_ready),
    .link_rx_reserved(rx_reserved),
    .link_rx_addr(rx_reserved_addr),
    .peer_rx_reserved(peer_reserved),
    .peer_rx_addr(peer_addr),
    .n_to_e_valid(route_valid),
    .n_to_e_data(route_data),
    .n_to_e_ready(route_ready),
    .e_direct_a_valid(route_valid),
    .e_direct_a_data(route_data),
    .e_direct_a_ready(route_ready),
    .outgoing_valid(outgoing_valid),
    .outgoing_ready(outgoing_ready),
    .outgoing_addr(outgoing_addr),
    .outgoing_data(outgoing_data),
    .outgoing_ack(outgoing_ack),
    .outgoing_ack_ready(outgoing_ack_ready)
);
    end
    else if(KIND==1)begin: f
    assign {fragment_ready_o,fragment_rsp_valid_o,fragment_error_o,native_result_valid_o}=0;
    assign native_result_packet_o=0;
    assign native_pending_o=tx_owned || outgoing_valid || incoming_ack;
    wire data_ready,data_stored,verify_valid,route_valid,route_take;
    wire [127:0] verify_data;
    wire [31:0] route_data;
    reg [1:0] read_state;
    reg [9:0] read_address;
    wire host_write=host_req_valid_i && host_req_write_i;
    wire read_take=read_state==2 && host_rsp_ready_i;
    assign host_req_ready_o=read_state==0 && (host_req_write_i ? data_ready : 1'b1);
    assign host_rsp_valid_o=read_state==2 || data_stored && !incoming_valid;
    assign host_rsp_data_o=read_state==2 ? verify_data : 128'b0;
    assign incoming_ready=data_ready && !host_write && read_state==0;
    assign incoming_ack=data_stored && !host_write;
    always @(posedge clk_i)begin
        if(reset)begin read_state<=0;read_address<=0;end
        else case(read_state)
            0:if(host_req_valid_i && host_req_ready_o && !host_req_write_i)begin read_address<=host_req_address_i;read_state<=1;end
            1:if(verify_valid)read_state<=2;
            2:if(read_take)read_state<=0;
            default:read_state<=0;
        endcase
    end
r82_f_cfj_group_f #(.BLOCK_ID(BLOCK),.TOPOLOGY_ID(TOPOLOGY_ID)) implementation(
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
    .event_ready_i(event_ready_i),
    .event_valid_o(event_valid_o),
    .event_packet_o(event_packet_o),
    .life_o(life_o),
    .seq_o(seq_o),
    .trace_pc_o(),
    .trace_retire_o(),
    .trace_opcode_o(),
    .trace_pm_owner_o(),
    .trace_ireg_valid_o(),
    .trace_cancel_token_retire_o(),
    .trace_cancel_object_drop_o(),
    .rx_valid(host_write || incoming_valid),
    .rx_ready(data_ready),
    .rx_addr(host_write ? host_req_address_i : incoming_addr),
    .rx_data(host_write ? host_req_data_i : incoming_data),
    .rx_stored(data_stored),
    .rx_stored_ready(host_rsp_ready_i || incoming_ack_ready),
    .peer_reserved(peer_reserved),
    .peer_addr(peer_addr),
    .rx_reserved(rx_reserved),
    .rx_reserved_addr(rx_reserved_addr),
    .verify_read(read_state==1),
    .verify_addr(read_address),
    .verify_take(read_take),
    .verify_valid(verify_valid),
    .verify_data(verify_data),
    .late_g_valid(route_valid),
    .late_g_data(route_data),
    .late_g_take(route_take),
    .late_e_valid(route_valid),
    .late_e_data(route_data),
    .late_e_take(route_take),
    .outgoing_valid(outgoing_valid),
    .outgoing_ready(outgoing_ready),
    .outgoing_addr(outgoing_addr),
    .outgoing_data(outgoing_data),
    .outgoing_ack(outgoing_ack),
    .outgoing_ack_ready(outgoing_ack_ready)
);
    end
    else if(KIND==2)begin: c
    assign {fragment_ready_o,fragment_rsp_valid_o,fragment_error_o,native_result_valid_o}=0;
    assign native_result_packet_o=0;
    assign native_pending_o=tx_owned || outgoing_valid || incoming_ack;
    wire data_ready,data_stored,verify_valid,route_valid,route_take;
    wire [127:0] verify_data;
    wire [31:0] route_data;
    reg [1:0] read_state;
    reg [9:0] read_address;
    wire host_write=host_req_valid_i && host_req_write_i;
    wire read_take=read_state==2 && host_rsp_ready_i;
    assign host_req_ready_o=read_state==0 && (host_req_write_i ? data_ready : 1'b1);
    assign host_rsp_valid_o=read_state==2 || data_stored && !incoming_valid;
    assign host_rsp_data_o=read_state==2 ? verify_data : 128'b0;
    assign incoming_ready=data_ready && !host_write && read_state==0;
    assign incoming_ack=data_stored && !host_write;
    always @(posedge clk_i)begin
        if(reset)begin read_state<=0;read_address<=0;end
        else case(read_state)
            0:if(host_req_valid_i && host_req_ready_o && !host_req_write_i)begin read_address<=host_req_address_i;read_state<=1;end
            1:if(verify_valid)read_state<=2;
            2:if(read_take)read_state<=0;
            default:read_state<=0;
        endcase
    end
r82_c_cfj_group_c #(.BLOCK_ID(BLOCK),.TOPOLOGY_ID(TOPOLOGY_ID)) implementation(
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
    .event_ready_i(event_ready_i),
    .event_valid_o(event_valid_o),
    .event_packet_o(event_packet_o),
    .life_o(life_o),
    .seq_o(seq_o),
    .trace_pc_o(),
    .trace_retire_o(),
    .trace_opcode_o(),
    .trace_pm_owner_o(),
    .trace_ireg_valid_o(),
    .trace_cancel_token_retire_o(),
    .trace_cancel_object_drop_o(),
    .rx_valid(host_write || incoming_valid),
    .rx_ready(data_ready),
    .rx_addr(host_write ? host_req_address_i : incoming_addr),
    .rx_data(host_write ? host_req_data_i : incoming_data),
    .rx_stored(data_stored),
    .rx_stored_ready(host_rsp_ready_i || incoming_ack_ready),
    .peer_reserved(peer_reserved),
    .peer_addr(peer_addr),
    .rx_reserved(rx_reserved),
    .rx_reserved_addr(rx_reserved_addr),
    .verify_read(read_state==1),
    .verify_addr(read_address),
    .verify_take(read_take),
    .verify_valid(verify_valid),
    .verify_data(verify_data),
    .late_g_valid(route_valid),
    .late_g_data(route_data),
    .late_g_take(route_take),
    .late_e_valid(route_valid),
    .late_e_data(route_data),
    .late_e_take(route_take),
    .outgoing_valid(outgoing_valid),
    .outgoing_ready(outgoing_ready),
    .outgoing_addr(outgoing_addr),
    .outgoing_data(outgoing_data),
    .outgoing_ack(outgoing_ack),
    .outgoing_ack_ready(outgoing_ack_ready)
);
    end
    else if(KIND==3)begin: p
    assign {fragment_ready_o,fragment_rsp_valid_o,fragment_error_o,native_result_valid_o}=0;
    assign native_result_packet_o=0;
    assign native_pending_o=tx_owned || outgoing_valid || incoming_ack;
    wire [1:0] io_ready,io_valid;
    wire [255:0] io_data;
    wire route_valid,route_take;
    wire [31:0] route_data;
    assign host_req_ready_o=io_ready[0];assign host_rsp_valid_o=io_valid[0];assign host_rsp_data_o=io_data[127:0];
    assign incoming_ready=io_ready[1] && life_o==5;
    assign incoming_ack=io_valid[1];
    assign rx_reserved=life_o==5;assign rx_reserved_addr=incoming_addr;
    assign {outgoing_valid,outgoing_addr,outgoing_data,outgoing_ack_ready}=0;
r82_p_pu_p_controlled_64 implementation(
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
    .event_ready_i(event_ready_i),
    .event_valid_o(event_valid_o),
    .event_packet_o(event_packet_o),
    .life_o(life_o),
    .seq_o(seq_o),
    .clk(clk_i),
    .block_id_i(BLOCK),
    .topology_id_i(TOPOLOGY_ID),
    .late_path_enable(1'b1),
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
    .io_req_valid({incoming_valid && life_o==5,host_req_valid_i}),
    .io_req_write({1'b1,host_req_write_i}),
    .io_req_addr({incoming_addr,host_req_address_i}),
    .io_req_data({incoming_data,host_req_data_i}),
    .io_req_ready(io_ready),
    .io_rsp_valid(io_valid),
    .io_rsp_ready({incoming_ack_ready,host_rsp_ready_i}),
    .io_rsp_data(io_data),
    .m_to_g_valid(route_valid),
    .m_to_g_data(route_data),
    .m_to_g_take(route_take),
    .g_from_m_valid(route_valid),
    .g_from_m_data(route_data),
    .g_from_m_take(route_take)
);
    end
    else if(KIND==4)begin: j
    wire [1:0] io_ready,io_valid;
    wire [255:0] io_data;
    wire out_valid,out_take,out_last,route_valid,route_take;
    wire [127:0] out_data,route_data;
    wire [31:0] out_tag;
    wire [9:0] out_index;
    reg [511:0] packet;
    assign {host_req_ready_o,host_rsp_valid_o}=0;assign host_rsp_data_o=0;
    assign {incoming_ready,incoming_ack,outgoing_valid,outgoing_addr,outgoing_data,outgoing_ack_ready,rx_reserved,rx_reserved_addr}=0;
    assign fragment_ready_o=io_ready[0];assign fragment_rsp_valid_o=io_valid[0];
    always @*begin
        packet=0;packet[127:0]=out_data;packet[159:128]=out_tag;packet[169:160]=out_index;packet[170]=out_last;
        packet[202:171]=task_job;packet[234:203]=task_epoch;packet[266:235]=task_sequence;
    end
    native_result_fifo #(.DEPTH(4)) results(.clk_i,.rst_ni,.push_valid_i(out_valid),.push_ready_o(out_take),.push_packet_i(packet),
        .pop_valid_o(native_result_valid_o),.pop_ready_i(native_result_ready_i),.pop_packet_o(native_result_packet_o),.pending_o(native_pending_o));
r82_j_cfj_group_j #(.BLOCK_ID(BLOCK),.TOPOLOGY_ID(TOPOLOGY_ID)) implementation(
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
    .event_ready_i(event_ready_i),
    .event_valid_o(event_valid_o),
    .event_packet_o(event_packet_o),
    .life_o(life_o),
    .seq_o(seq_o),
    .trace_pc_o(),
    .trace_retire_o(),
    .trace_opcode_o(),
    .trace_pm_owner_o(),
    .trace_ireg_valid_o(),
    .trace_cancel_token_retire_o(),
    .trace_cancel_object_drop_o(),
    .io_req_valid({1'b0,fragment_valid_i}),
    .io_req_write(2'b01),
    .io_req_addr({10'b0,fragment_address_i}),
    .io_req_data({128'b0,fragment_data_i}),
    .io_req_ready(io_ready),
    .io_rsp_valid(io_valid),
    .io_rsp_ready({1'b0,fragment_rsp_ready_i}),
    .io_rsp_data(io_data),
    .active_epoch(native_epoch),
    .rx_tag(fragment_tag_i),
    .rx_slot(fragment_slot_i),
    .rx_last(fragment_last_i),
    .rx_error(fragment_error_o),
    .out_valid(out_valid),
    .out_take(out_take),
    .out_data(out_data),
    .out_tag(out_tag),
    .out_index(out_index),
    .out_last(out_last),
    .late_e_valid(route_valid),
    .late_e_take(route_take),
    .late_e_data(route_data),
    .late_s_valid(route_valid),
    .late_s_take(route_take),
    .late_s_data(route_data)
);
    end
    endgenerate
endmodule
