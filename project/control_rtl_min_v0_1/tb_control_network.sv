`timescale 1ns/1ps
module tb_control_network;
`include "tb_network_mc_wires.svh"
  integer cycle=0,stall=0,words=0,mode=0,runs=1,n,ji,returns=0,calls=0,cancels=0;
  integer expected_calls=0,expected_cancels=0,expected_poison=0,expected_status=0,hold_target=-1,hold_cycles=0,hold_age=0,return_delay=0,return_age=0;
  reg [31:0] fault_address=32'hffffffff; reg [127:0] fault_xor=0;
  reg [127:0] input_image[0:295]; reg [2047:0] image_path;
  reg deploy_grant=0,ret_locked=0,ret_source=0,ret_rr=0,mother_return_held=0;
  wire [1:0] lc_ready,lc_valid,lc_poison,lc_event_valid;
  wire [3:0] lc_life[0:1]; wire [31:0] lc_id[0:1]; wire [511:0] lc_event[0:1];
  wire selected_source=ret_locked ? ret_source : lc_event_valid[ret_rr] ? ret_rr : !ret_rr;
  wire task_gate=task_packet_o[16+:8]!=0 || task_target_o!=hold_target[7:0] || hold_age>=hold_cycles;
  wire return_gate=mother_return_held || return_age>=return_delay && (stall==0 || cycle%11==0);
  wire cohort_valid=deploy_grant && lc_poison==0;
  wire [1:0] link_valid,link_ready,store_ready,done_ready;
  wire [1:0] link_kind[0:1]; wire [31:0] link_job[0:1],link_epoch[0:1],link_task[0:1],link_sequence[0:1],link_edge[0:1];
  wire [7:0] link_peer[0:1]; wire [127:0] link_data[0:1];
  reg [1:0] store_valid,done_valid,sink_commit; reg [127:0] route_data;
  reg [1:0] rx_armed=0; reg tx_full=0;
  reg [31:0] rx_job[0:1],rx_epoch[0:1],rx_task[0:1],rx_edge[0:1],tx_job,tx_epoch,tx_task,tx_edge;
  reg [127:0] tx_data; reg route_dst; integer route_state=0,route_delay=0,k;
`ifdef TB_COMPUTE_HANDOFF
  reg seed_valid=0,probe_valid=0;
  reg [9:0] seed_word=0;
  reg [127:0] seed_data=0,seed_image[0:17];
  wire seed_ready,seed_ack,probe_ready,probe_ack;
  wire [127:0] seed_result,probe_result;
  string seed_path;
  integer word_index;
`endif
`ifdef TB_STORED_ACK_GUARD
  wire [31:0] ack_inject=32'(mode);
`include "tb_stored_ack_guard.svh"
`endif
  function [127:0] host_pattern;
    input [31:0] job;
    begin host_pattern=128'h0f0e0d0c0b0a09080706050403020100^{4{job-32'd6}}; end
  endfunction
  initial clk_i=0; always #5 clk_i=~clk_i;
`include "tb_mc_trace.svh"
  always @* begin
    deploy_valid_i=cohort_valid; local_enabled_i=3; local_image_id0_i=lc_id[0]; local_image_id1_i=lc_id[1];
    task_ready_i=task_target_o<2 && task_gate && lc_ready[task_target_o[0]];
    return_valid_i=lc_event_valid[selected_source] && return_gate; return_packet_i=lc_event[selected_source];
    store_valid=0; done_valid=0; sink_commit=0;
    if(route_state==1 && route_delay==0 && (stall==0 || cycle%13==0)) begin
      store_valid[route_dst]=1;
      if(route_dst && store_ready[1]) sink_commit[0]=1;
    end
    if(route_state==2 && (stall==0 || cycle%13==0)) done_valid[route_dst]=1;
`ifdef TB_STORED_ACK_GUARD
    if(route_state==3) done_valid[0]=ack_guard_done && ack_done_gate;
`else
    if(route_state==3 && mode!=2 && (stall==0 || cycle%17==0)) done_valid[0]=1;
`endif
  end
  assign link_ready[0]=link_kind[0]==1 ? !rx_armed[0] : !tx_full;
  assign link_ready[1]=!rx_armed[1];
  network_pm #(.BYTES(4736)) mother_pm(.clk_i(clk_i),.rst_ni(rst_ni),.cycle_i(32'(cycle)),.stall_i(32'(stall)),
    .pm_req_valid_o(pm_req_valid_o),.pm_req_write_o(pm_req_write_o),.pm_req_address_o(pm_req_address_o),.pm_req_data_o(pm_req_data_o),
    .pm_req_ready_i(pm_req_ready_i),.pm_rsp_valid_i(pm_rsp_valid_i),.pm_rsp_data_i(pm_rsp_data_i),.pm_rsp_error_i(pm_rsp_error_i),.pm_rsp_ready_o(pm_rsp_ready_o),
    .fault_active_i(1'b0),.fault_address_i(32'b0),.fault_xor_i(128'b0));
  generate for(genvar b=0;b<2;b=b+1) begin: local_controllers
`ifdef TB_COMPUTE_HANDOFF
    if(b==0) begin: producer
      assign store_ready[b]=0;
`ifdef TB_F_HANDOFF
      tb_f_local
`else
      tb_p_local
`endif
      peer(.clk_i(clk_i),.rst_ni(rst_ni),.release_epoch_i(32'd1),
        .deploy_valid_i(cohort_valid),.deploy_generation_i(32'd1),.task_valid_i(task_valid_o && task_target_o==b && task_gate),
        .task_packet_i(task_packet_o),.task_credit_i(task_credit_o),.task_ready_o(lc_ready[b]),
        .event_ready_i(return_ready_o && return_gate && selected_source==b),.event_valid_o(lc_event_valid[b]),
        .event_packet_o(lc_event[b]),.image_valid_o(lc_valid[b]),.poison_o(lc_poison[b]),.life_o(lc_life[b]),
        .cycle_i(32'(cycle)),.stall_i(32'(stall)),.image_id(lc_id[b]),
        .host_valid(seed_valid),.host_write(1'b1),.host_word(seed_word),.host_data(seed_data),
        .host_ready(seed_ready),.host_ack(seed_ack),.host_result(seed_result),
        .link_valid_o(link_valid[b]),.link_ready_i(link_ready[b]),.link_kind_o(link_kind[b]),
        .link_job_o(link_job[b]),.link_epoch_o(link_epoch[b]),.link_task_o(link_task[b]),
        .link_sequence_o(link_sequence[b]),.link_edge_o(link_edge[b]),.link_peer_o(link_peer[b]),
        .link_data_o(link_data[b]),.done_valid_i(done_valid[b]),.done_ready_o(done_ready[b]));
    end else begin: consumer
`endif
    network_local #(.BLOCK(8'(b))) peer(.clk_i(clk_i),.rst_ni(rst_ni),.release_epoch_i(32'd1),
      .deploy_valid_i(cohort_valid),.deploy_generation_i(32'd1),.task_valid_i(task_valid_o && task_target_o==b && task_gate),
      .task_packet_i(task_packet_o),.task_credit_i(task_credit_o),.task_ready_o(lc_ready[b]),
      .event_ready_i(return_ready_o && return_gate && selected_source==b),.event_valid_o(lc_event_valid[b]),.event_packet_o(lc_event[b]),
      .image_valid_o(lc_valid[b]),.poison_o(lc_poison[b]),.life_o(lc_life[b]),.cycle_i(32'(cycle)),.stall_i(32'(stall)),.mode_i(32'(mode)),.image_id_o(lc_id[b]),
      .link_valid_o(link_valid[b]),.link_ready_i(link_ready[b]),.link_kind_o(link_kind[b]),.link_job_o(link_job[b]),.link_epoch_o(link_epoch[b]),
      .link_task_o(link_task[b]),.link_sequence_o(link_sequence[b]),.link_edge_o(link_edge[b]),.link_peer_o(link_peer[b]),.link_data_o(link_data[b]),
      .store_valid_i(store_valid[b]),.store_ready_o(store_ready[b]),.store_data_i(route_data),.sink_commit_i(sink_commit[b]),
      .done_valid_i(done_valid[b]),.done_ready_o(done_ready[b]),.done_status_i(16'b0)
`ifdef TB_COMPUTE_HANDOFF
      ,.probe_valid_i(probe_valid),.probe_ready_o(probe_ready),.probe_ack_o(probe_ack),.probe_data_o(probe_result)
`endif
    );
`ifdef TB_COMPUTE_HANDOFF
    end
`endif
  end endgenerate
  always @(posedge clk_i) begin
    if(!rst_ni) begin rx_armed<=0; tx_full<=0; route_state<=0; ret_locked<=0; ret_rr<=0; mother_return_held<=0; end
    else begin
      ret_locked<=lc_event_valid[selected_source] && !(return_valid_i && return_ready_o);
      if(lc_event_valid[selected_source]) ret_source<=selected_source;
      mother_return_held<=return_valid_i && !return_ready_o;
      if(lc_event_valid[selected_source]) return_age<=return_age+1;
      if(return_valid_i && return_ready_o) begin return_age<=0; ret_rr<=!selected_source; end
      if(task_valid_o && task_packet_o[16+:8]==0 && task_target_o==hold_target[7:0]) hold_age<=hold_age+1;
      if(!task_valid_o) hold_age<=0;
      if(task_valid_o && task_ready_i) begin if(task_packet_o[16+:8]==0) calls<=calls+1; else cancels<=cancels+1; end
`ifdef TB_COMPUTE_HANDOFF
      if(task_valid_o && task_ready_i && task_packet_o[16+:8]==0)
        $display("CHAIN %0d CALL %0d %0d %0d %0d",cycle,task_target_o,task_packet_o[32+:32],
                 task_packet_o[64+:32],task_packet_o[96+:32]);
      if(return_valid_i && return_ready_o)
        $display("CHAIN %0d EVENT %0d %0d %0d %0d",cycle,return_packet_i[24+:8],
                 return_packet_i[16+:8],return_packet_i[32+:32],return_packet_i[144+:16]);
      if(result_valid_o && result_ready_i)
        $display("CHAIN %0d RESULT %0d %0d %0d %0d",cycle,result_job_o,result_status_o,
                 result_confirmed_read_bytes_o,result_confirmed_write_bytes_o);
`endif
      for(k=0;k<2;k=k+1) if(link_valid[k] && link_ready[k]) begin
        if(link_kind[k]==1) begin
          if(rx_armed[k] || (k==0 ? link_peer[k]!=255 || link_edge[k]!=11 : link_peer[k]!=0 || link_edge[k]!=12)) $fatal(1,"RX route/credit");
          rx_armed[k]<=1; rx_job[k]<=link_job[k]; rx_epoch[k]<=link_epoch[k]; rx_task[k]<=link_task[k]; rx_edge[k]<=link_edge[k];
          $display("N %0d ARM %0d %0d %0d %0d %0d",cycle,k,link_job[k],link_epoch[k],link_task[k],link_edge[k]);
        end else begin
          if(k!=0 || link_kind[k]!=2 || tx_full || link_peer[k]!=1 || link_edge[k]!=12) $fatal(1,"TX route/credit");
          tx_full<=1; tx_job<=link_job[k]; tx_epoch<=link_epoch[k]; tx_task<=link_task[k]; tx_edge<=link_edge[k]; tx_data<=link_data[k];
          $display("N %0d TX %0d %0d %0d %0d %0d",cycle,k,link_job[k],link_epoch[k],link_task[k],link_edge[k]);
        end
      end
      if(route_state==0) begin
        if(rx_armed[0]) begin route_dst<=0; route_data<=host_pattern(rx_job[0]); route_state<=1; route_delay<=20+stall*5; end
        else if(rx_armed[1] && tx_full) begin
          if(rx_job[1]!=tx_job || rx_epoch[1]!=tx_epoch || rx_edge[1]!=tx_edge) $fatal(1,"cross-task rendezvous job/epoch/edge");
          route_dst<=1; route_data<=tx_data; route_state<=1; route_delay<=20+stall*5;
        end
      end
      if(route_state==1) begin
        if(route_delay!=0) route_delay<=route_delay-1;
        else if(store_valid[route_dst] && store_ready[route_dst]) begin
          route_state<=2; $display("N %0d STORE %0d %0d %0d %0d %0h",cycle,route_dst,rx_job[route_dst],rx_epoch[route_dst],rx_task[route_dst],route_data);
        end
      end
      if(route_state==2 && done_valid[route_dst] && done_ready[route_dst]) begin
        rx_armed[route_dst]<=0; route_state<=route_dst ? 3 : 0;
        $display("N %0d ACK_SEND %0d %0d %0d %0d",cycle,route_dst,rx_job[route_dst],rx_epoch[route_dst],rx_task[route_dst]);
      end
      if(route_state==3 && done_valid[0] && done_ready[0]) begin
        tx_full<=0; route_state<=0; $display("N %0d ACK_RECV 0 %0d %0d %0d",cycle,tx_job,tx_epoch,tx_task);
      end
      if(result_valid_o && result_ready_i) begin
        if(rx_armed!=0 || tx_full || route_state!=0 || lc_life[0]!=5 || lc_life[1]!=5) $fatal(1,"host result before actual locals/link drained");
        if(result_status_o!=(mode==3 && ji>0 ? 0 : expected_status[15:0])) $fatal(1,"network result status");
        returns<=returns+1;
      end
      if(poison_o && expected_poison==0) $fatal(1,"unexpected network mother poison");
    end
  end
  task config_command;
    input [2:0] op; input integer address; input [127:0] data;
    begin
      @(negedge clk_i); cfg_req_valid_i=1; cfg_req_op_i=op; cfg_req_generation_i=1; cfg_req_address_i=address[13:0]; cfg_req_data_i=data;
      cfg_req_proof_i=1; cfg_req_total_bytes_i=16'(words*16); cfg_req_image_id_i=input_image[3][96+:32]; cfg_req_topology_id_i=input_image[4][0+:32];
      cfg_req_abi_id_i=input_image[4][32+:32]; cfg_req_capacity_id_i=32'h17630001;
      @(posedge clk_i); while(!cfg_req_ready_o) @(posedge clk_i); @(negedge clk_i); cfg_req_valid_i=0;
      while(!cfg_rsp_valid_o) @(negedge clk_i);
      if(cfg_rsp_status_o!=0 || op==2 && cfg_rsp_data_o!==input_image[address>>4]) $fatal(1,"network mother config/readback");
      cfg_rsp_ready_i=1; @(negedge clk_i); cfg_rsp_ready_i=0;
    end
  endtask
`ifdef TB_COMPUTE_HANDOFF
  task automatic seed_source(input integer address, input [127:0] data);
    @(negedge clk_i);
    seed_valid=1; seed_word=10'(address); seed_data=data;
    @(posedge clk_i); while(!seed_ready) @(posedge clk_i);
    @(negedge clk_i); seed_valid=0;
    while(!seed_ack) @(negedge clk_i);
    if(seed_result!==data) $fatal(1,"source seed writeback");
    @(negedge clk_i);
  endtask
  task automatic read_destination;
    @(negedge clk_i); probe_valid=1;
    @(posedge clk_i); while(!probe_ready) @(posedge clk_i);
    @(negedge clk_i); probe_valid=0;
    while(!probe_ack) @(negedge clk_i);
    $display("CHAIN %0d DEST_READ %0d %032h",cycle,7+ji,probe_result);
    @(negedge clk_i);
  endtask
`endif
  initial begin
`include "tb_network_mc_init.svh"
    if(!$value$plusargs("IMAGE=%s",image_path) || !$value$plusargs("WORDS=%d",words)) $fatal(1,"missing mother image");
    n=$value$plusargs("STALL=%d",stall); n=$value$plusargs("MODE=%d",mode); n=$value$plusargs("RUNS=%d",runs);
    n=$value$plusargs("CALLS=%d",expected_calls); n=$value$plusargs("CANCELS=%d",expected_cancels); n=$value$plusargs("EXPECTED=%d",expected_status);
    n=$value$plusargs("POISON=%d",expected_poison); n=$value$plusargs("HOLD_TARGET=%d",hold_target); n=$value$plusargs("HOLD_CYCLES=%d",hold_cycles);
    n=$value$plusargs("RETURN_DELAY=%d",return_delay);
    $readmemh(image_path,input_image,0,words-1);
`ifdef TB_COMPUTE_HANDOFF
    if(!$value$plusargs("SEED=%s",seed_path) || runs<1 || runs>2) $fatal(1,"seed input missing");
    $readmemh(seed_path,seed_image,0,9*runs-1);
`endif
    repeat(2) @(negedge clk_i); rst_ni=1;
    @(negedge clk_i); release_valid_i=1; release_sequence_i=1; release_epoch_i=1;
    @(negedge clk_i); release_valid_i=0;
    config_command(0,0,0); for(n=0;n<words;n=n+1) config_command(1,n*16,input_image[n]);
    for(n=0;n<words;n=n+1) config_command(2,n*16,0); config_command(3,0,0); config_command(4,0,0);
    while(lc_life[0]!=4 || lc_life[1]!=4) @(negedge clk_i);
    deploy_generation_i=1; deploy_grant=1; start_credit_i=1;
    while(life_o!=5 || lc_valid!=3) @(negedge clk_i);
    for(ji=0;ji<runs;ji=ji+1) begin
`ifdef TB_COMPUTE_HANDOFF
      for(word_index=0;word_index<4;word_index=word_index+1) begin
        seed_source(4+word_index,seed_image[9*ji+word_index]);
        seed_source(8+word_index,seed_image[9*ji+4+word_index]);
      end
      seed_source(12,seed_image[9*ji+8]);
`endif
      start_job_i=32'(7+ji); start_epoch_i=1; start_sequence_i=32'(ji+1); start_generation_i=1; start_args_i=0; start_valid_i=1;
      @(posedge clk_i); while(!start_ready_o) @(posedge clk_i); @(negedge clk_i); start_valid_i=0;
      if(expected_poison!=0) begin
        while(!poison_o) @(negedge clk_i); repeat(10) @(negedge clk_i);
        if(result_valid_o || start_ready_o || cfg_req_ready_o) $fatal(1,"poison fabricated global result/credit");
      end else begin
        while(!result_valid_o) @(negedge clk_i); repeat(5+stall*4) @(negedge clk_i);
        result_ready_i=1; @(negedge clk_i); result_ready_i=0;
        while(returns!=ji+1) @(negedge clk_i);
`ifdef TB_COMPUTE_HANDOFF
        read_destination();
`endif
      end
    end
    if(calls!=expected_calls || cancels!=expected_cancels || returns!=(expected_poison!=0 ? 0 : runs)) $fatal(1,"network counts CALL=%0d CANCEL=%0d results=%0d",calls,cancels,returns);
    $display("PASS network actualMother=1 actualLC=2 CALL=%0d CANCEL=%0d results=%0d poison=%0d",calls,cancels,returns,poison_o); $finish;
  end
  initial begin #1000000; $fatal(1,"network watchdog"); end
endmodule
