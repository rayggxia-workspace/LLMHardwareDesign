`timescale 1ns/1ps
module tb_jc_local(
`include "tb_network_lc_ports.svh"
  ,input wire [31:0] cycle_i,stall_i,
  output reg [31:0] image_id,
  input wire host_valid,host_write,input wire [3:0] host_device,input wire [9:0] host_word,input wire [127:0] host_data,
  output wire host_ready,host_ack,output wire [127:0] host_result
);
  localparam [7:0] BLOCK=0;
`include "tb_network_lc_wires.svh"

  wire s_valid,s_ready,s_write,s_take;
  wire [9:0] s_word;
  wire [127:0] s_data;
  wire [1:0] s_req_ready,s_rsp_valid;
  wire [255:0] s_rsp_data;
  wire extra_ready,extra_ack;
  wire [127:0] extra_result;
  wire e_valid,e_ready,e_take,e_out_valid,e_error,e_sat;
  wire [3:0] e_op;
  wire [4:0] e_shift;
  wire [127:0] e_a,e_b,e_y;
  int e_req_age=0,e_rsp_age=0,write_age=0,ack_age=0;
  wire e_req_gate=e_req_age>=int'(stall_i)*2;
  wire e_rsp_gate=e_rsp_age>=int'(stall_i)*3;
  wire s_req_gate=!s_write || write_age>=int'(stall_i)*4;
  reg expect_write_ack=0;
  wire s_rsp_gate=!expect_write_ack || ack_age>=int'(stall_i)*5;
  wire native_s_rsp_valid=s_rsp_valid[0] && s_rsp_gate;
  wire [127:0] native_s_rsp_data=s_rsp_data[0+:128];

  assign host_ready=host_device==0 ? s_req_ready[1] : extra_ready;
  assign host_ack=host_device==0 ? s_rsp_valid[1] : extra_ack;
  assign host_result=host_device==0 ? s_rsp_data[128+:128] : extra_result;
  assign s_ready=s_req_ready[0] && s_req_gate;
  assign svc_rsp_kind_i=0;
  assign close_req_ready_i=0;
  assign close_rsp_valid_i=0;
  assign close_rsp_sequence_i=0;
  assign close_rsp_job_i=0;
  assign close_rsp_epoch_i=0;
  assign close_rsp_task_sequence_i=0;
  assign close_rsp_token_i=0;
  assign close_rsp_status_i=0;

  network_pm pm(.clk_i(clk_i),.rst_ni(rst_ni),.cycle_i(cycle_i),.stall_i(stall_i),
    .pm_req_valid_o(pm_req_valid_o),.pm_req_write_o(pm_req_write_o),.pm_req_address_o(pm_req_address_o),
    .pm_req_data_o(pm_req_data_o),.pm_req_ready_i(pm_req_ready_i),.pm_rsp_valid_i(pm_rsp_valid_i),
    .pm_rsp_data_i(pm_rsp_data_i),.pm_rsp_error_i(pm_rsp_error_i),.pm_rsp_ready_o(pm_rsp_ready_o),
    .fault_active_i(1'b0),.fault_address_i(32'b0),.fault_xor_i(128'b0));
  block_local_s_macro #(.CLIENTS(2)) private_s(
    .clk(clk_i),.reset(!rst_ni),.req_valid({host_valid && host_device==0,s_valid && s_req_gate}),
    .req_write({host_write,s_write}),.req_addr({host_word,s_word}),.req_data({host_data,s_data}),
    .req_ready(s_req_ready),.rsp_valid(s_rsp_valid),.rsp_ready({1'b1,s_take && s_rsp_gate}),.rsp_data(s_rsp_data),
    .load_valid(1'b0),.load_ready(),.load_bank(1'b0),.load_rows(4'b0),.load_tiles(3'b0),
    .load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),.load_a_base(10'b0),.load_b_base(10'b0),
    .done_valid(),.done_take(1'b0),.done_error(),.busy(),
    .a_valid(),.a_ready(1'b0),.a_bank(),.a_row(),.a_tile(),.a_wide(),.a_data(),
    .b_valid(),.b_ready(1'b0),.b_bank(),.b_tile(),.b_wide(),.b_half(),.b_data());
  block_v2_e macro_e(.clk(clk_i),.reset(!rst_ni),
    .in_valid(e_valid && e_req_gate),.in_ready(e_ready),.in_op(e_op),.in_shift(e_shift),
    .in_a(e_a),.in_b(e_b),.in_c(128'b0),.out_valid(e_out_valid),.out_ready(e_take && e_rsp_gate),
    .out_data(e_y),.out_error(e_error),.out_saturated(e_sat));

`ifdef TB_C_STATE
  `include "tb_c_trial_native.svh"
`else
  `include "tb_j_trial_native.svh"
`endif

  always @(posedge clk_i) if(rst_ni) begin
    if(trace_retire_o) $display("JC %0d RETIRE %02h",cycle_i,trace_opcode_o);
    if(svc_req_valid_o && svc_req_ready_i)
      $display("JC %0d EXEC %0d %0d %0d %0d",cycle_i,svc_req_job_o,
               svc_req_epoch_o,svc_req_task_sequence_o,svc_req_resource_o);
    if(svc_rsp_valid_i && svc_rsp_ready_o)
      $display("JC %0d SERVICE %0d %0d %0d %0d %0d",cycle_i,svc_rsp_job_i,svc_rsp_status_i,
               svc_rsp_read_bytes_i,svc_rsp_write_bytes_i,svc_rsp_saturated_i);
    if(e_valid && !e_req_gate) begin
      e_req_age<=e_req_age+1; $display("JC %0d EIN_H %0d %0d %032h %032h",cycle_i,e_op,e_shift,e_a,e_b);
    end
    if(e_valid && e_ready && e_req_gate) begin
      e_req_age<=0; $display("JC %0d EIN %0d %0d %032h %032h",cycle_i,e_op,e_shift,e_a,e_b);
    end
    if(e_out_valid && !e_rsp_gate) begin
      e_rsp_age<=e_rsp_age+1; $display("JC %0d EOUT_H %0d %0d %032h",cycle_i,e_error,e_sat,e_y);
    end
    if(e_out_valid && e_take && e_rsp_gate) begin
      e_rsp_age<=0; $display("JC %0d EOUT %0d %0d %032h",cycle_i,e_error,e_sat,e_y);
    end
    if(s_valid && s_write && !s_req_gate) begin
      write_age<=write_age+1; $display("JC %0d WRITE_H %0d %032h",cycle_i,s_word,s_data);
    end
    if(s_valid && s_ready) begin
      if(s_write) begin
        write_age<=0; expect_write_ack<=1; $display("JC %0d WRITE %0d %032h",cycle_i,s_word,s_data);
      end else $display("JC %0d READ %0d",cycle_i,s_word);
    end
    if(s_rsp_valid[0] && !s_rsp_gate) begin
      ack_age<=ack_age+1; $display("JC %0d ACK_H %032h",cycle_i,native_s_rsp_data);
    end
    if(native_s_rsp_valid && s_take) begin
      if(expect_write_ack) begin
        ack_age<=0; expect_write_ack<=0; $display("JC %0d ACK %032h",cycle_i,native_s_rsp_data);
      end else $display("JC %0d READ_RSP %032h",cycle_i,native_s_rsp_data);
    end
  end

  reg [127:0] image[0:519];
  string path;
  integer words,n;
  task automatic cfg(input [2:0] op,input integer address,input [127:0] data,
                     input [31:0] abi,input [15:0] status);
    @(negedge clk_i);
    cfg_req_valid_i=1; cfg_req_op_i=op; cfg_req_generation_i=1; cfg_req_address_i=14'(address);
    cfg_req_data_i=data; cfg_req_proof_i=1; cfg_req_total_bytes_i=16'(words*16);
    cfg_req_image_id_i=image_id; cfg_req_topology_id_i=image[4][0+:32];
    cfg_req_abi_id_i=abi; cfg_req_capacity_id_i=image[5][32+:32];
    @(posedge clk_i); while(!cfg_req_ready_o) @(posedge clk_i);
    @(negedge clk_i); cfg_req_valid_i=0;
    while(!cfg_rsp_valid_o) @(negedge clk_i);
    if(cfg_rsp_status_o!=status || (op==2 && cfg_rsp_data_o!==image[address>>4]))
      $fatal(1,"local configuration op=%0d got=%0d expected=%0d",op,cfg_rsp_status_o,status);
    cfg_rsp_ready_i=1; @(negedge clk_i); cfg_rsp_ready_i=0;
  endtask
  initial begin
    release_valid_i=0; release_sequence_i=0;
    cfg_req_valid_i=0; cfg_req_op_i=0; cfg_req_generation_i=0; cfg_req_address_i=0; cfg_req_data_i=0;
    cfg_req_total_bytes_i=0; cfg_req_image_id_i=0; cfg_req_topology_id_i=0; cfg_req_abi_id_i=0;
    cfg_req_capacity_id_i=0; cfg_req_proof_i=0; cfg_rsp_ready_i=0;
    if(!$value$plusargs("LOCAL=%s",path) || !$value$plusargs("LWORDS=%d",words)) $fatal(1,"local image");
    $readmemh(path,image,0,words-1);
    image_id=image[3][96+:32];
    wait(rst_ni); @(negedge clk_i); release_valid_i=1; release_sequence_i=1;
    @(negedge clk_i); release_valid_i=0;
    if($test$plusargs("BADCFG")) begin
      cfg(0,0,0,32'h00017904,3);
      if(life_o!=1 || image_valid_o) $fatal(1,"wrong ABI granted");
      $display("JC %0d BAD_ABI_REJECTED",cycle_i);
    end
    cfg(0,0,0,image[4][32+:32],0);
    for(n=0;n<words;n=n+1) cfg(1,n*16,image[n],image[4][32+:32],0);
    for(n=0;n<words;n=n+1) cfg(2,n*16,0,image[4][32+:32],0);
    cfg(3,0,0,image[4][32+:32],0); cfg(4,0,0,image[4][32+:32],0);
    $display("JC %0d CONFIG_READBACK %0d",cycle_i,words);
  end
endmodule
