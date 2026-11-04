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
);
`include "tb_network_lc_wires.svh"
`include "tb_network_lc_trace.svh"
  reg [127:0] input_image[0:519],sram[0:1023];
  reg [2047:0] path; integer words=0,n;
  reg [31:0] image_id,topology,active_job=0,active_task=0;
  reg service_active=0,read_pending=0,stored=0;
  reg [1:0] saved_kind; reg [2:0] saved_token;
  reg [31:0] saved_seq,saved_job,saved_epoch,saved_task,saved_base;
  wire fault_active=(mode_i==1 || mode_i==3) && BLOCK==1 && active_job==7 || mode_i==4 && BLOCK==0 && active_job!=0;
  wire [31:0] transfer_address=input_image[3][0+:32];
  wire [31:0] fault_address=transfer_address+(mode_i==4 ? 64 : 0);
  assign image_id_o=image_id;
  assign store_ready_o=rst_ni && service_active && saved_kind==1 && !stored && !svc_rsp_valid_i;
  assign done_ready_o=rst_ni && service_active && !svc_rsp_valid_i && (saved_kind==2 || stored);
  network_pm pm(.clk_i(clk_i),.rst_ni(rst_ni),.cycle_i(cycle_i),.stall_i(stall_i),
    .pm_req_valid_o(pm_req_valid_o),.pm_req_write_o(pm_req_write_o),.pm_req_address_o(pm_req_address_o),.pm_req_data_o(pm_req_data_o),
    .pm_req_ready_i(pm_req_ready_i),.pm_rsp_valid_i(pm_rsp_valid_i),.pm_rsp_data_i(pm_rsp_data_i),.pm_rsp_error_i(pm_rsp_error_i),.pm_rsp_ready_o(pm_rsp_ready_o),
    .fault_active_i(fault_active),.fault_address_i(fault_address),.fault_xor_i(128'b1));
  task data_event;
    input integer kind; input [127:0] data;
    begin $display("D %0d %0d %0d %0h %0h %0d %0d %0d %0d %0d",BLOCK,cycle_i,kind,saved_base,data,saved_job,saved_epoch,saved_task,saved_seq,saved_kind); end
  endtask
  always @(posedge clk_i) begin
    if(!rst_ni) begin
      link_valid_o<=0; link_kind_o<=0; link_job_o<=0; link_epoch_o<=0; link_task_o<=0; link_sequence_o<=0; link_edge_o<=0; link_peer_o<=0; link_data_o<=0;
      service_active<=0; read_pending<=0; stored<=0; svc_rsp_valid_i<=0; active_job<=0; active_task<=0;
    end else begin
      if(task_valid_i && task_ready_o && task_packet_i[16+:8]==0) begin active_job<=task_packet_i[32+:32]; active_task<=task_packet_i[96+:32]; end
      if(svc_req_valid_o && svc_req_ready_i) begin
        if(service_active || svc_req_kind_o==0 || svc_req_resource_o!=5 || svc_req_object_length_o!=16 ||
           svc_req_object_version_o!=1 || svc_req_object_base_o>=16384 || svc_req_object_base_o[3:0]!=0 || svc_req_descriptor_o[1023:512]!=0)
          $fatal(1,"network finite storage service tuple");
        service_active<=1; stored<=0; saved_kind<=svc_req_kind_o; saved_token<=svc_req_token_o; saved_seq<=svc_req_sequence_o;
        saved_job<=svc_req_job_o; saved_epoch<=svc_req_epoch_o; saved_task<=svc_req_task_sequence_o; saved_base<=svc_req_object_base_o[31:0];
        link_kind_o<=svc_req_kind_o; link_job_o<=svc_req_job_o; link_epoch_o<=svc_req_epoch_o; link_task_o<=svc_req_task_sequence_o;
        link_sequence_o<=svc_req_sequence_o; link_edge_o<=svc_req_descriptor_o[192+:32]; link_peer_o<=svc_req_descriptor_o[160+:8];
        link_data_o<=0; link_valid_o<=svc_req_kind_o==1; read_pending<=svc_req_kind_o==2;
      end
      if(read_pending) begin
        read_pending<=0; link_data_o<=sram[saved_base[13:4]]; link_valid_o<=1; data_event(2,sram[saved_base[13:4]]);
      end
      if(link_valid_o && link_ready_i) link_valid_o<=0;
      if(store_valid_i && store_ready_o) begin sram[saved_base[13:4]]<=store_data_i; stored<=1; data_event(1,store_data_i); end
      if(sink_commit_i) begin
        if(!service_active || saved_kind!=2) $fatal(1,"sink commit without TX"); data_event(4,link_data_o);
      end
      if(done_valid_i && done_ready_o) begin
        data_event(3,saved_kind==1 ? sram[saved_base[13:4]] : link_data_o);
        svc_rsp_valid_i<=1; svc_rsp_kind_i<=saved_kind; svc_rsp_token_i<=saved_token; svc_rsp_sequence_i<=saved_seq;
        svc_rsp_job_i<=saved_job; svc_rsp_epoch_i<=saved_epoch; svc_rsp_task_sequence_i<=saved_task; svc_rsp_status_i<=done_status_i;
        svc_rsp_read_bytes_i<=saved_kind==2 ? 16 : 0; svc_rsp_write_bytes_i<=saved_kind==1 ? 16 : 0; svc_rsp_saturated_i<=0;
      end
      if(svc_rsp_valid_i && svc_rsp_ready_o) begin svc_rsp_valid_i<=0; service_active<=0; end
    end
  end
  always @* svc_req_ready_i=rst_ni && !service_active && !svc_rsp_valid_i && (stall_i==0 || cycle_i%7==0);
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
    for(n=0;n<1024;n=n+1) sram[n]={16{8'hcd}};
    wait(rst_ni); @(negedge clk_i); release_valid_i=1; release_sequence_i=1;
    @(negedge clk_i); release_valid_i=0;
    config_command(0,0,0); for(n=0;n<words;n=n+1) config_command(1,n*16,input_image[n]);
    for(n=0;n<words;n=n+1) config_command(2,n*16,0);
    config_command(3,0,0); config_command(4,0,0);
  end
endmodule
