`timescale 1ns/1ps
module network_local #(parameter [7:0] BLOCK=0)(
`include "tb_network_lc_ports.svh"
  ,input wire [31:0] cycle_i,stall_i,mode_i,
  output wire [31:0] image_id_o,
  output reg link_valid_o,input wire link_ready_i,output reg [1:0] link_kind_o,
  output reg [31:0] link_job_o,link_epoch_o,link_task_o,link_sequence_o,link_edge_o,
  output reg [7:0] link_peer_o,output reg [127:0] link_data_o,
  input wire store_valid_i,output wire store_ready_o,input wire [127:0] store_data_i,
  input wire sink_commit_i,input wire done_valid_i,output wire done_ready_o,input wire [15:0] done_status_i
`ifdef TB_COMPUTE_HANDOFF
  ,input wire probe_valid_i,output wire probe_ready_o,probe_ack_o,output wire [127:0] probe_data_o
`endif
);
`include "tb_network_lc_wires.svh"
`include "tb_network_lc_trace.svh"
  reg [127:0] input_image[0:519];
  reg [2047:0] path; integer words=0,n;
  reg [31:0] image_id,topology,active_job=0;
  reg [31:0] saved_base,saved_job,saved_epoch,saved_task,saved_seq;
  reg [1:0] saved_kind;reg [127:0] ack_payload;
  wire s_req,s_write,s_ready,s_valid,s_take,adapter_poison,adapter_busy;
  wire [9:0] s_address;wire [127:0] s_data,s_result;
  wire [3:0] req_ready,rsp_valid;wire [511:0] rsp_data;
  wire response_enable=stall_i==0||cycle_i%9==0;
  wire fault_active=((mode_i==1 || mode_i==3) && BLOCK==1 && active_job==7) || (mode_i==4 && BLOCK==0 && active_job!=0);
  wire [31:0] transfer_address=input_image[3][0+:32];
  wire [31:0] fault_address=transfer_address+(mode_i==4 ? 32'd64 : 32'd0);
  assign image_id_o=image_id;
  wire tx_port=saved_kind==2;
  assign s_ready=tx_port?req_ready[3]:req_ready[2];assign s_valid=tx_port?rsp_valid[3]:rsp_valid[2];
  assign s_result=tx_port?rsp_data[384+:128]:rsp_data[256+:128];
`ifdef TB_COMPUTE_HANDOFF
  assign probe_ready_o=req_ready[0];
  assign probe_ack_o=rsp_valid[0];
  assign probe_data_o=rsp_data[0+:128];
  wire probe_req=probe_valid_i;
  wire probe_take=1'b1;
`else
  wire probe_req=1'b0;
  wire probe_take=1'b0;
`endif
  block_local_s_macro #(.CLIENTS(4),.WITH_FEEDER(1'b1)) storage(
   .clk(clk_i),.reset(!rst_ni),.req_valid({s_req&&tx_port,s_req&&!tx_port,1'b0,probe_req}),.req_write({s_write&&tx_port,s_write&&!tx_port,2'b0}),
   .req_addr({s_address,s_address,10'b0,10'd16}),.req_data({s_data,s_data,256'b0}),.req_ready(req_ready),
   .rsp_valid(rsp_valid),.rsp_ready({s_take&&tx_port,s_take&&!tx_port,1'b0,probe_take}),.rsp_data(rsp_data),
   .load_valid(1'b0),.load_ready(),.load_bank(1'b0),.load_rows(4'b0),.load_tiles(3'b0),
   .load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),.load_a_base(10'b0),.load_b_base(10'b0),
   .done_valid(),.done_take(1'b1),.done_error(),.busy(),.a_valid(),.a_ready(1'b1),.a_bank(),.a_row(),.a_tile(),.a_wide(),.a_data(),
   .b_valid(),.b_ready(1'b1),.b_bank(),.b_tile(),.b_wide(),.b_half(),.b_data());
  lc_raw16_s_adapter adapter(.clk(clk_i),.reset(!rst_ni),.admit(1'b1),.response_enable(response_enable),
   .req_valid(svc_req_valid_o),.req_ready(svc_req_ready_i),.req_kind(svc_req_kind_o),.req_resource(svc_req_resource_o),.req_token(svc_req_token_o),
   .req_sequence(svc_req_sequence_o),.req_job(svc_req_job_o),.req_epoch(svc_req_epoch_o),.req_task(svc_req_task_sequence_o),
   .req_descriptor(svc_req_descriptor_o),.req_base(svc_req_object_base_o),.req_length(svc_req_object_length_o),.req_version(svc_req_object_version_o),
   .rsp_valid(svc_rsp_valid_i),.rsp_ready(svc_rsp_ready_o),.rsp_kind(svc_rsp_kind_i),.rsp_token(svc_rsp_token_i),
   .rsp_sequence(svc_rsp_sequence_i),.rsp_job(svc_rsp_job_i),.rsp_epoch(svc_rsp_epoch_i),.rsp_task(svc_rsp_task_sequence_i),
   .rsp_status(svc_rsp_status_i),.rsp_read(svc_rsp_read_bytes_i),.rsp_write(svc_rsp_write_bytes_i),.rsp_saturated(svc_rsp_saturated_i),
   .link_valid(link_valid_o),.link_ready(link_ready_i),.link_kind(link_kind_o),.link_job(link_job_o),.link_epoch(link_epoch_o),
   .link_task(link_task_o),.link_sequence(link_sequence_o),.link_edge(link_edge_o),.link_peer(link_peer_o),.link_data(link_data_o),
   .store_valid(store_valid_i),.store_ready(store_ready_o),.store_data(store_data_i),.done_valid(done_valid_i),.done_ready(done_ready_o),.done_status(done_status_i),
   .s_req(s_req),.s_write(s_write),.s_address(s_address),.s_data(s_data),.s_ready(s_ready),.s_valid(s_valid),.s_result(s_result),.s_take(s_take),
   .poison(adapter_poison),.busy(adapter_busy));
  network_pm pm(.clk_i(clk_i),.rst_ni(rst_ni),.cycle_i(cycle_i),.stall_i(stall_i),
    .pm_req_valid_o(pm_req_valid_o),.pm_req_write_o(pm_req_write_o),.pm_req_address_o(pm_req_address_o),.pm_req_data_o(pm_req_data_o),
    .pm_req_ready_i(pm_req_ready_i),.pm_rsp_valid_i(pm_rsp_valid_i),.pm_rsp_data_i(pm_rsp_data_i),.pm_rsp_error_i(pm_rsp_error_i),.pm_rsp_ready_o(pm_rsp_ready_o),
    .fault_active_i(fault_active),.fault_address_i(fault_address),.fault_xor_i(128'b1));
  task data_event;
    input integer kind; input [127:0] data;
    begin $display("D %0d %0d %0d %0h %0h %0d %0d %0d %0d %0d",BLOCK,cycle_i,kind,saved_base,data,saved_job,saved_epoch,saved_task,saved_seq,saved_kind); end
  endtask
  always @(posedge clk_i)begin
   if(!rst_ni)active_job<=0;
   else begin
    if(adapter_poison)$fatal(1,"real S adapter protocol poison");
    if(task_valid_i&&task_ready_o&&task_packet_i[16+:8]==0)active_job<=task_packet_i[32+:32];
    if(svc_req_valid_o&&svc_req_ready_i)begin
     saved_base<=svc_req_object_base_o[31:0];saved_job<=svc_req_job_o;saved_epoch<=svc_req_epoch_o;
     saved_task<=svc_req_task_sequence_o;saved_seq<=svc_req_sequence_o;saved_kind<=svc_req_kind_o;
    end
    if(s_req&&s_ready)$display("S %0d %0d REQ %0d %0d %0h",BLOCK,cycle_i,s_write,s_address,s_data);
    if(s_valid)$display("S %0d %0d HOLD %0d %0h",BLOCK,cycle_i,s_take,s_result);
    if(s_valid&&s_take)begin
     $display("S %0d %0d RSP %0d %0d %0h",BLOCK,cycle_i,saved_kind==1,saved_base>>4,s_result);
     ack_payload<=s_result;data_event(saved_kind==1?1:2,s_result);
    end
    if(sink_commit_i)data_event(4,link_data_o);
    if(done_valid_i&&done_ready_o)data_event(3,saved_kind==1?ack_payload:link_data_o);
   end
  end
  task config_command;
    input [2:0] op; input integer address; input [127:0] data;
    begin
      @(negedge clk_i); cfg_req_valid_i=1; cfg_req_op_i=op; cfg_req_generation_i=1; cfg_req_address_i=address[13:0]; cfg_req_data_i=data;
      cfg_req_proof_i=1; cfg_req_total_bytes_i=16'(words*16); cfg_req_image_id_i=image_id; cfg_req_topology_id_i=topology;
      cfg_req_abi_id_i=65537; cfg_req_capacity_id_i=32'h17630001;
      @(posedge clk_i); while(!cfg_req_ready_o) @(posedge clk_i);
      @(negedge clk_i); cfg_req_valid_i=0; while(!cfg_rsp_valid_o) @(negedge clk_i);
      if(cfg_rsp_status_o!=0 || op==2 && cfg_rsp_data_o!==input_image[address>>4]) $fatal(1,"network LC actual config/readback");
      cfg_rsp_ready_i=1; @(negedge clk_i); cfg_rsp_ready_i=0;
    end
  endtask
  initial begin
`include "tb_network_lc_init.svh"
    if(BLOCK==0) begin
      if(!$value$plusargs("LOCAL0=%s",path) || !$value$plusargs("WORDS0=%d",words)) $fatal(1,"missing local0 image");
    end else if(!$value$plusargs("LOCAL1=%s",path) || !$value$plusargs("WORDS1=%d",words)) $fatal(1,"missing local1 image");
    $readmemh(path,input_image,0,words-1); image_id=input_image[3][96+:32]; topology=input_image[4][0+:32];
    wait(rst_ni); @(negedge clk_i); release_valid_i=1; release_sequence_i=1;
    @(negedge clk_i); release_valid_i=0;
    config_command(0,0,0); for(n=0;n<words;n=n+1) config_command(1,n*16,input_image[n]);
    for(n=0;n<words;n=n+1) config_command(2,n*16,0);
    config_command(3,0,0); config_command(4,0,0);
  end
endmodule
