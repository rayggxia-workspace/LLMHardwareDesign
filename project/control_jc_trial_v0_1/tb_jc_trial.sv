`timescale 1ns/1ps
module tb_jc_trial;
`include "tb_network_mc_wires.svh"
  integer cycle=0,stall=0,j,n,cursor=0,init_words=0,seed_words=0,read_words=0,runs=1,mwords;
  reg [63:0] expected;
  reg [127:0] image[0:295];
  reg [143:0] actions[0:127];
  string path;
  reg grant=0,host_valid=0,host_write=0;
  reg [3:0] host_device=0;
  reg [9:0] host_word=0;
  reg [127:0] host_data=0;
  wire host_ready,host_ack,lc_ready,lc_event,lc_poison,lc_image_valid;
  wire [127:0] host_result;
  wire [3:0] lc_life;
  wire [31:0] lc_id;
  wire [511:0] lc_packet;
  integer return_age=0;
  wire event_gate=return_age>=stall*3;

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
      if(task_valid_o && task_ready_i)
        $display("JC %0d CALL %0d %0d %0d",cycle,task_packet_o[32+:32],
                 task_packet_o[64+:32],task_packet_o[96+:32]);
      if(return_valid_i && return_ready_o) begin
        return_age<=0;
        $display("JC %0d TERMINAL %0d %0d %0d %0d %0d",cycle,lc_packet[32+:32],lc_packet[144+:16],
                 lc_packet[192+:32],lc_packet[224+:32],lc_packet[256]);
      end
      if(result_valid_o && result_ready_i)
        $display("JC %0d RESULT %0d %0d %0d %0d %0d",cycle,result_job_o,result_status_o,
                 result_confirmed_read_bytes_o,result_confirmed_write_bytes_o,result_saturated_o);
      if(poison_o || lc_poison) $fatal(1,"unexpected trial poison");
    end
  end
  network_pm #(.BYTES(4736)) pm(.clk_i(clk_i),.rst_ni(rst_ni),.cycle_i(32'(cycle)),.stall_i(32'(stall)),
    .pm_req_valid_o(pm_req_valid_o),.pm_req_write_o(pm_req_write_o),.pm_req_address_o(pm_req_address_o),
    .pm_req_data_o(pm_req_data_o),.pm_req_ready_i(pm_req_ready_i),.pm_rsp_valid_i(pm_rsp_valid_i),
    .pm_rsp_data_i(pm_rsp_data_i),.pm_rsp_error_i(pm_rsp_error_i),.pm_rsp_ready_o(pm_rsp_ready_o),
    .fault_active_i(1'b0),.fault_address_i(32'b0),.fault_xor_i(128'b0));
  tb_jc_local local_dut(.clk_i(clk_i),.rst_ni(rst_ni),.release_epoch_i(32'd1),
    .deploy_valid_i(deploy_valid_i),.deploy_generation_i(deploy_generation_i),.poison_o(lc_poison),
    .image_valid_o(lc_image_valid),.task_valid_i(task_valid_o && task_target_o==0),.task_packet_i(task_packet_o),
    .task_credit_i(task_credit_o),.task_ready_o(lc_ready),.event_ready_i(return_ready_o && event_gate),
    .event_valid_o(lc_event),.event_packet_o(lc_packet),.life_o(lc_life),.cycle_i(32'(cycle)),.stall_i(32'(stall)),
    .image_id(lc_id),.host_valid(host_valid),.host_write(host_write),.host_device(host_device),
    .host_word(host_word),.host_data(host_data),.host_ready(host_ready),.host_ack(host_ack),.host_result(host_result));

  task automatic cfg(input [2:0] op,input integer address,input [127:0] data);
    @(negedge clk_i);
    cfg_req_valid_i=1; cfg_req_op_i=op; cfg_req_generation_i=1; cfg_req_address_i=14'(address);
    cfg_req_data_i=data; cfg_req_proof_i=1; cfg_req_total_bytes_i=16'(mwords*16);
    cfg_req_image_id_i=image[3][96+:32]; cfg_req_topology_id_i=image[4][0+:32];
    cfg_req_abi_id_i=image[4][32+:32]; cfg_req_capacity_id_i=image[5][32+:32];
    @(posedge clk_i); while(!cfg_req_ready_o) @(posedge clk_i);
    @(negedge clk_i); cfg_req_valid_i=0;
    while(!cfg_rsp_valid_o) @(negedge clk_i);
    if(cfg_rsp_status_o!=0 || (op==2 && cfg_rsp_data_o!==image[address>>4]))
      $fatal(1,"MC configuration op=%0d status=%0d",op,cfg_rsp_status_o);
    cfg_rsp_ready_i=1; @(negedge clk_i); cfg_rsp_ready_i=0;
  endtask

  task automatic host_access(input bit write,input [143:0] action);
    @(negedge clk_i);
    host_valid=1; host_write=write; host_device=action[138+:4];
    host_word=action[128+:10]; host_data=action[127:0];
    @(posedge clk_i); while(!host_ready) @(posedge clk_i);
    @(negedge clk_i); host_valid=0;
    while(!host_ack) @(negedge clk_i);
    if(write && host_result!==host_data) $fatal(1,"host seed acknowledgement");
    if(!write) $display("JC %0d READBACK %0d %0d %0d %032h",cycle,7+j,host_device,host_word,host_result);
    @(negedge clk_i);
  endtask

  initial begin
`include "tb_network_mc_init.svh"
    if(!$value$plusargs("MOTHER=%s",path) || !$value$plusargs("MWORDS=%d",mwords))
      $fatal(1,"trial mother image");
    $readmemh(path,image,0,mwords-1);
    if(!$value$plusargs("ACTIONS=%s",path) || !$value$plusargs("INIT=%d",init_words) ||
       !$value$plusargs("SEEDS=%d",seed_words) || !$value$plusargs("READS=%d",read_words) ||
       !$value$plusargs("RUNS=%d",runs) || !$value$plusargs("STALL=%d",stall) ||
       !$value$plusargs("STATUSES=%h",expected) || runs<1 || runs>4 ||
       init_words+runs*(seed_words+read_words)>128)
      $fatal(1,"trial action schedule");
    $readmemh(path,actions,0,init_words+runs*(seed_words+read_words)-1);
    repeat(2) @(negedge clk_i); rst_ni=1;
    @(negedge clk_i); release_valid_i=1; release_sequence_i=1; release_epoch_i=1;
    @(negedge clk_i); release_valid_i=0;
    cfg(0,0,0);
    for(n=0;n<mwords;n=n+1) cfg(1,n*16,image[n]);
    for(n=0;n<mwords;n=n+1) cfg(2,n*16,0);
    cfg(3,0,0); cfg(4,0,0);
    while(lc_life!=4) @(negedge clk_i);
    deploy_generation_i=1; grant=1; start_credit_i=1;
    while(life_o!=5 || !lc_image_valid) @(negedge clk_i);
    for(n=0;n<init_words;n=n+1) begin host_access(1,actions[cursor]); cursor=cursor+1; end
    for(j=0;j<runs;j=j+1) begin
      for(n=0;n<seed_words;n=n+1) begin host_access(1,actions[cursor]); cursor=cursor+1; end
      start_job_i=32'(7+j); start_epoch_i=1; start_sequence_i=32'(j+1);
      start_generation_i=1; start_valid_i=1;
      @(posedge clk_i); while(!start_ready_o) @(posedge clk_i);
      @(negedge clk_i); start_valid_i=0;
      while(!result_valid_o) @(negedge clk_i);
      if(result_status_o!=expected[16*j+:16]) $fatal(1,"trial status job=%0d got=%0d expected=%0d",
                                                   7+j,result_status_o,expected[16*j+:16]);
      repeat(2+stall) @(negedge clk_i);
      result_ready_i=1; @(negedge clk_i); result_ready_i=0;
      for(n=0;n<read_words;n=n+1) begin host_access(0,actions[cursor]); cursor=cursor+1; end
    end
    $display("PASS JC jobs=%0d cycles=%0d",runs,cycle); $finish;
  end
  initial begin #1000000; $fatal(1,"trial watchdog"); end
endmodule
