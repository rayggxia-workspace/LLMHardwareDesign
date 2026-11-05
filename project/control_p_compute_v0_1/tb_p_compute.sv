`timescale 1ns/1ps
module tb_p_compute;
`define TB_ENABLE_M_DOT_STORE
`include "tb_network_mc_wires.svh"
`undef TB_ENABLE_M_DOT_STORE
  integer cycle=0, stall=0, expected=0, runs=1, words=0;
  integer n, j, a_word, b_word, dst_word, return_age=0;
  reg [127:0] image[0:295], seed[0:17];
  string image_path, seed_path;
  reg grant=0, host_valid=0, host_write=0;
  reg [9:0] host_word=0;
  reg [127:0] host_data=0;
  wire host_ready, host_ack;
  wire [127:0] host_result;
  wire lc_ready, lc_event, lc_poison, lc_image_valid;
  wire [3:0] lc_life;
  wire [31:0] lc_id;
  wire [511:0] lc_packet;
  wire event_gate=return_age>=stall*5;
  assign deploy_valid_i=grant && !lc_poison;
  assign local_enabled_i=1;
  assign local_image_id0_i=lc_id;
  assign local_image_id1_i=0;
  assign task_ready_i=task_target_o==0 && lc_ready;
  assign return_valid_i=lc_event && event_gate;
  assign return_packet_i=lc_packet;

  initial clk_i=0;
  always #5 clk_i=~clk_i;
  always @(posedge clk_i) begin
    cycle<=cycle+1;
    if(rst_ni) begin
      if(lc_event && !event_gate) return_age<=return_age+1;
      if(return_valid_i && return_ready_o) return_age<=0;
      if(task_valid_o && task_ready_i)
        $display("A2 %0d CALL %0d %0d %0d %0d",cycle,task_packet_o[32+:32],
          task_packet_o[64+:32],task_packet_o[96+:32],task_packet_o[136+:8]);
      if(return_valid_i && return_ready_o)
        $display("A2 %0d TERMINAL %0d %0d %0d %0d %0d %0d %0d",cycle,lc_packet[32+:32],
          lc_packet[64+:32],lc_packet[96+:32],lc_packet[128+:8],lc_packet[144+:16],
          lc_packet[192+:32],lc_packet[224+:32]);
      if(result_valid_o && result_ready_i)
        $display("A2 %0d RESULT %0d %0d %0d %0d %0d %0d",cycle,result_job_o,result_epoch_o,
          result_sequence_o,result_status_o,result_confirmed_read_bytes_o,result_confirmed_write_bytes_o);
      if(poison_o || lc_poison) $fatal(1,"unexpected poison in A2");
    end
  end

  network_pm #(.BYTES(4736)) pm(.clk_i(clk_i),.rst_ni(rst_ni),.cycle_i(32'(cycle)),.stall_i(32'(stall)),
    .pm_req_valid_o(pm_req_valid_o),.pm_req_write_o(pm_req_write_o),.pm_req_address_o(pm_req_address_o),
    .pm_req_data_o(pm_req_data_o),.pm_req_ready_i(pm_req_ready_i),.pm_rsp_valid_i(pm_rsp_valid_i),
    .pm_rsp_data_i(pm_rsp_data_i),.pm_rsp_error_i(pm_rsp_error_i),.pm_rsp_ready_o(pm_rsp_ready_o),
    .fault_active_i(1'b0),.fault_address_i(32'b0),.fault_xor_i(128'b0));
  tb_p_local local_dut(.clk_i(clk_i),.rst_ni(rst_ni),.release_epoch_i(32'd1),
    .deploy_valid_i(deploy_valid_i),.deploy_generation_i(deploy_generation_i),.poison_o(lc_poison),
    .image_valid_o(lc_image_valid),.task_valid_i(task_valid_o && task_target_o==0),.task_packet_i(task_packet_o),
    .task_credit_i(task_credit_o),.task_ready_o(lc_ready),.event_ready_i(return_ready_o && event_gate),
    .event_valid_o(lc_event),.event_packet_o(lc_packet),.life_o(lc_life),.cycle_i(32'(cycle)),.stall_i(32'(stall)),
    .image_id(lc_id),.host_valid(host_valid),.host_write(host_write),.host_word(host_word),.host_data(host_data),
    .host_ready(host_ready),.host_ack(host_ack),.host_result(host_result));

  task automatic config_command(input [2:0] op, input integer address, input [127:0] data);
    @(negedge clk_i);
    cfg_req_valid_i=1; cfg_req_op_i=op; cfg_req_generation_i=1; cfg_req_address_i=address[13:0];
    cfg_req_data_i=data; cfg_req_proof_i=1; cfg_req_total_bytes_i=16'(words*16);
    cfg_req_image_id_i=image[3][96+:32]; cfg_req_topology_id_i=image[4][0+:32];
    cfg_req_abi_id_i=image[4][32+:32]; cfg_req_capacity_id_i=image[5][32+:32];
    @(posedge clk_i); while(!cfg_req_ready_o) @(posedge clk_i);
    @(negedge clk_i); cfg_req_valid_i=0;
    while(!cfg_rsp_valid_o) @(negedge clk_i);
    if(cfg_rsp_status_o!=0 || (op==2 && cfg_rsp_data_o!==image[address>>4]))
      $fatal(1,"mother config/readback op=%0d status=%0d",op,cfg_rsp_status_o);
    cfg_rsp_ready_i=1; @(negedge clk_i); cfg_rsp_ready_i=0;
  endtask

  task automatic host_access(input bit write, input integer word, input [127:0] payload);
    @(negedge clk_i);
    host_valid=1; host_write=write; host_word=10'(word); host_data=payload;
    @(posedge clk_i); while(!host_ready) @(posedge clk_i);
    @(negedge clk_i); host_valid=0;
    while(!host_ack) @(negedge clk_i);
    if(write && host_result!==payload) $fatal(1,"seed S write acknowledgement");
    if(!write) $display("A2 %0d READBACK %0d %0d %032h",cycle,7+j,word,host_result);
    @(negedge clk_i);
  endtask

  initial begin
`include "tb_network_mc_init.svh"
    if(!$value$plusargs("MOTHER=%s",image_path) || !$value$plusargs("MWORDS=%d",words) ||
       !$value$plusargs("SEED=%s",seed_path) || !$value$plusargs("A=%d",a_word) ||
       !$value$plusargs("B=%d",b_word) || !$value$plusargs("DST=%d",dst_word) ||
       !$value$plusargs("RUNS=%d",runs) || !$value$plusargs("STALL=%d",stall) ||
       !$value$plusargs("EXPECT=%d",expected)) $fatal(1,"A2 fixture arguments");
    $readmemh(image_path,image,0,words-1);
    $readmemh(seed_path,seed,0,9*runs-1);
    repeat(2) @(negedge clk_i); rst_ni=1;
    @(negedge clk_i); release_valid_i=1; release_sequence_i=1; release_epoch_i=1;
    @(negedge clk_i); release_valid_i=0;
    config_command(0,0,0);
    for(n=0;n<words;n=n+1) config_command(1,n*16,image[n]);
    for(n=0;n<words;n=n+1) config_command(2,n*16,0);
    config_command(3,0,0); config_command(4,0,0);
    while(lc_life!=4) @(negedge clk_i);
    deploy_generation_i=1; grant=1; start_credit_i=1;
    while(life_o!=5 || !lc_image_valid) @(negedge clk_i);
    for(j=0;j<runs;j=j+1) begin
      for(n=0;n<4;n=n+1) host_access(1,a_word+n,seed[9*j+n]);
      for(n=0;n<4;n=n+1) host_access(1,b_word+n,seed[9*j+4+n]);
      host_access(1,dst_word,seed[9*j+8]);
      start_job_i=32'(7+j); start_epoch_i=1; start_sequence_i=32'(j+1);
      start_generation_i=1; start_valid_i=1;
      @(posedge clk_i); while(!start_ready_o) @(posedge clk_i);
      @(negedge clk_i); start_valid_i=0;
      while(!result_valid_o) @(negedge clk_i);
      if(result_status_o!=expected[15:0]) $fatal(1,"A2 result status %0d",result_status_o);
      repeat(2+stall) @(negedge clk_i);
      result_ready_i=1; @(negedge clk_i); result_ready_i=0;
      host_access(0,dst_word,0);
    end
    $display("PASS A2 jobs=%0d status=%0d cycles=%0d",runs,expected,cycle); $finish;
  end
  initial begin #1000000; $fatal(1,"A2 watchdog"); end
endmodule

module tb_p_local(
`include "tb_network_lc_ports.svh"
  ,input wire [31:0] cycle_i,stall_i,
  output reg [31:0] image_id,
  input wire host_valid,host_write,input wire [9:0] host_word,input wire [127:0] host_data,
  output wire host_ready,host_ack,output wire [127:0] host_result
);
  localparam [7:0] BLOCK=0;
`define TB_ENABLE_M_DOT_STORE
`include "tb_network_lc_wires.svh"
`undef TB_ENABLE_M_DOT_STORE
  reg [127:0] image[0:519];
  string path;
  integer words=0,n,write_age=0,ack_age=0;
  reg ack_observed=0;
  wire load_valid,load_ready,load_done,load_error,load_take;
  wire [9:0] load_a_word,load_b_word,s_write_word;
  wire a_valid,a_ready,a_bank,a_wide,b_valid,b_ready,b_bank,b_wide,b_half;
  wire [2:0] a_row;
  wire [1:0] a_tile,b_tile;
  wire [127:0] a_data,m_rsp_data,s_write_data;
  wire [511:0] b_data;
  wire m_cmd_valid,m_cmd_ready,m_rsp_valid,m_rsp_ready,m_rsp_error,m_rsp_saturated;
  wire [3:0] m_cmd_op;
  wire [63:0] m_cmd_data;
  wire s_write_valid,s_write_ready,s_ack_ready;
  wire [3:0] s_req_ready,s_rsp_valid;
  wire [511:0] s_rsp_data;
  wire write_gate=write_age>=32'(stall_i)*3;
  wire ack_gate=ack_age>=32'(stall_i)*6;
  assign s_write_ready=s_req_ready[0] && write_gate;
  assign host_ready=s_req_ready[3];
  assign host_ack=s_rsp_valid[3];
  assign host_result=s_rsp_data[384+:128];
  assign svc_rsp_kind_i=0;
  assign svc_rsp_saturated_i=0;
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
  lc_m_dot_store_adapter adapter(.clk(clk_i),.rst_n(rst_ni),
    .svc_valid(svc_req_valid_o),.svc_ready(svc_req_ready_i),.svc_kind(svc_req_kind_o),
    .svc_resource(svc_req_resource_o),.svc_token(svc_req_token_o),.svc_sequence(svc_req_sequence_o),
    .svc_job(svc_req_job_o),.svc_epoch(svc_req_epoch_o),.svc_task_sequence(svc_req_task_sequence_o),
    .svc_desc(svc_req_descriptor_o),.rsp_valid(svc_rsp_valid_i),.rsp_ready(svc_rsp_ready_o),
    .rsp_token(svc_rsp_token_i),.rsp_sequence(svc_rsp_sequence_i),.rsp_job(svc_rsp_job_i),
    .rsp_epoch(svc_rsp_epoch_i),.rsp_task_sequence(svc_rsp_task_sequence_i),.rsp_status(svc_rsp_status_i),
    .rsp_read_bytes(svc_rsp_read_bytes_i),.rsp_write_bytes(svc_rsp_write_bytes_i),
    .load_valid(load_valid),.load_ready(load_ready),.load_a_word(load_a_word),.load_b_word(load_b_word),
    .load_done(load_done),.load_error(load_error),.load_take(load_take),
    .m_cmd_valid(m_cmd_valid),.m_cmd_ready(m_cmd_ready),.m_cmd_op(m_cmd_op),.m_cmd_data(m_cmd_data),
    .m_rsp_valid(m_rsp_valid),.m_rsp_error(m_rsp_error),.m_rsp_saturated(m_rsp_saturated),
    .m_rsp_data(m_rsp_data),.m_rsp_ready(m_rsp_ready),.s_write_valid(s_write_valid),
    .s_write_ready(s_write_ready),.s_write_word(s_write_word),.s_write_data(s_write_data),
    .s_ack_valid(s_rsp_valid[0] && ack_gate),.s_ack_data(s_rsp_data[0+:128]),.s_ack_ready(s_ack_ready));
  block_local_s_macro #(.CLIENTS(4),.WITH_FEEDER(1'b1)) private_s(
    .clk(clk_i),.reset(!rst_ni),.req_valid({host_valid,2'b0,s_write_valid && write_gate}),
    .req_write({host_write,2'b0,1'b1}),.req_addr({host_word,20'b0,s_write_word}),
    .req_data({host_data,256'b0,s_write_data}),.req_ready(s_req_ready),.rsp_valid(s_rsp_valid),
    .rsp_ready({1'b1,2'b0,s_ack_ready && ack_gate}),.rsp_data(s_rsp_data),
    .load_valid(load_valid),.load_ready(load_ready),.load_bank(1'b0),.load_rows(4'd1),.load_tiles(3'd1),
    .load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),.load_a_base(load_a_word),
    .load_b_base(load_b_word),.done_valid(load_done),.done_take(load_take),.done_error(load_error),.busy(),
    .a_valid(a_valid),.a_ready(a_ready),.a_bank(a_bank),.a_row(a_row),.a_tile(a_tile),.a_wide(a_wide),.a_data(a_data),
    .b_valid(b_valid),.b_ready(b_ready),.b_bank(b_bank),.b_tile(b_tile),.b_wide(b_wide),.b_half(b_half),.b_data(b_data));
  block_v2_m macro_m(.clk(clk_i),.reset(!rst_ni),
    .a_valid(a_valid),.a_ready(a_ready),.a_bank(a_bank),.a_row(a_row),.a_tile(a_tile),.a_wide(a_wide),.a_data(a_data),
    .b_valid(b_valid),.b_ready(b_ready),.b_bank(b_bank),.b_tile(b_tile),.b_wide(b_wide),.b_half(b_half),.b_data(b_data),
    .cmd_valid(m_cmd_valid),.cmd_ready(m_cmd_ready),.cmd_op(m_cmd_op),.cmd_index(6'b0),.cmd_data(m_cmd_data),
    .rsp_valid(m_rsp_valid),.rsp_ready(m_rsp_ready),.rsp_error(m_rsp_error),.rsp_saturated(m_rsp_saturated),
    .rsp_data(m_rsp_data),.busy());

  always @(posedge clk_i) if(rst_ni) begin
    if(s_write_valid && !write_gate) begin
      write_age<=write_age+1;
      $display("A2 %0d WHELD %0d %032h",cycle_i,s_write_word,s_write_data);
    end
    if(s_write_valid && s_write_ready) write_age<=0;
    if(s_rsp_valid[0] && !ack_gate) ack_age<=ack_age+1;
    if(s_rsp_valid[0] && s_ack_ready && ack_gate) ack_age<=0;
    if(svc_req_valid_o && svc_req_ready_i) begin
      ack_observed<=0;
      $display("A2 %0d EXEC %0d %0d %0d %0d %0d",cycle_i,svc_req_job_o,svc_req_epoch_o,
        svc_req_task_sequence_o,svc_req_sequence_o,svc_req_token_o);
    end
    if(load_valid && load_ready) $display("A2 %0d LOAD %0d %0d",cycle_i,load_a_word,load_b_word);
    if(a_valid && a_ready) $display("A2 %0d A %032h",cycle_i,a_data);
    if(b_valid && b_ready) $display("A2 %0d B %0128h",cycle_i,b_data);
    if(load_done && load_take) $display("A2 %0d FED %0d",cycle_i,load_error);
    if(m_cmd_valid && m_cmd_ready) $display("A2 %0d CMD %0d %0h",cycle_i,m_cmd_op,m_cmd_data);
    if(m_rsp_valid && m_rsp_ready) $display("A2 %0d NATIVE %0d %0d %032h",cycle_i,m_rsp_error,m_rsp_saturated,m_rsp_data);
    if(s_write_valid && s_write_ready) $display("A2 %0d WRITE %0d %032h",cycle_i,s_write_word,s_write_data);
    if(s_rsp_valid[0] && !ack_gate) $display("A2 %0d HELD %032h",cycle_i,s_rsp_data[0+:128]);
    if(s_rsp_valid[0] && s_ack_ready && ack_gate) begin
      ack_observed<=1;
      $display("A2 %0d ACK %032h",cycle_i,s_rsp_data[0+:128]);
    end
    if(svc_rsp_valid_i && svc_rsp_status_i==0 && !ack_observed)
      $fatal(1,"successful service offered before real S ACK");
    if(svc_rsp_valid_i && svc_rsp_ready_o)
      $display("A2 %0d RETURN %0d %0d %0d %0d %0d %0d %0d %0d",cycle_i,svc_rsp_job_i,
        svc_rsp_epoch_i,svc_rsp_task_sequence_i,svc_rsp_sequence_i,svc_rsp_token_i,svc_rsp_status_i,
        svc_rsp_read_bytes_i,svc_rsp_write_bytes_i);
  end

  task automatic config_command(input [2:0] op, input integer address, input [127:0] data);
    @(negedge clk_i);
    cfg_req_valid_i=1; cfg_req_op_i=op; cfg_req_generation_i=1; cfg_req_address_i=address[13:0];
    cfg_req_data_i=data; cfg_req_proof_i=1; cfg_req_total_bytes_i=16'(words*16);
    cfg_req_image_id_i=image_id; cfg_req_topology_id_i=image[4][0+:32];
    cfg_req_abi_id_i=image[4][32+:32]; cfg_req_capacity_id_i=image[5][32+:32];
    @(posedge clk_i); while(!cfg_req_ready_o) @(posedge clk_i);
    @(negedge clk_i); cfg_req_valid_i=0;
    while(!cfg_rsp_valid_o) @(negedge clk_i);
    if(cfg_rsp_status_o!=0 || (op==2 && cfg_rsp_data_o!==image[address>>4]))
      $fatal(1,"local config/readback op=%0d status=%0d",op,cfg_rsp_status_o);
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
    config_command(0,0,0);
    for(n=0;n<words;n=n+1) config_command(1,n*16,image[n]);
    for(n=0;n<words;n=n+1) config_command(2,n*16,0);
    config_command(3,0,0); config_command(4,0,0);
  end
endmodule
