`timescale 1ns/1ps
`ifndef TB_COMPUTE_HANDOFF
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
`ifdef TB_P_SILU
      if(return_valid_i && return_ready_o) $display("A2 %0d LC_SAT %0d",cycle,lc_packet[256]);
      if(result_valid_o && result_ready_i) $display("A2 %0d MC_SAT %0d",cycle,result_saturated_o);
`elsif TB_F_COMPUTE
      if(return_valid_i && return_ready_o) $display("A2 %0d LC_SAT %0d",cycle,lc_packet[256]);
      if(result_valid_o && result_ready_i) $display("A2 %0d MC_SAT %0d",cycle,result_saturated_o);
`elsif TB_U_COMPUTE
      if(return_valid_i && return_ready_o) $display("A2 %0d LC_SAT %0d",cycle,lc_packet[256]);
      if(result_valid_o && result_ready_i) $display("A2 %0d MC_SAT %0d",cycle,result_saturated_o);
`endif
      if(poison_o || lc_poison) $fatal(1,"unexpected poison in A2");
    end
  end

  network_pm #(.BYTES(4736)) pm(.clk_i(clk_i),.rst_ni(rst_ni),.cycle_i(32'(cycle)),.stall_i(32'(stall)),
    .pm_req_valid_o(pm_req_valid_o),.pm_req_write_o(pm_req_write_o),.pm_req_address_o(pm_req_address_o),
    .pm_req_data_o(pm_req_data_o),.pm_req_ready_i(pm_req_ready_i),.pm_rsp_valid_i(pm_rsp_valid_i),
    .pm_rsp_data_i(pm_rsp_data_i),.pm_rsp_error_i(pm_rsp_error_i),.pm_rsp_ready_o(pm_rsp_ready_o),
    .fault_active_i(1'b0),.fault_address_i(32'b0),.fault_xor_i(128'b0));
`ifdef TB_U_COMPUTE
  tb_u_local local_dut(
`elsif TB_F_COMPUTE
  tb_f_local local_dut(
`else
  tb_p_local local_dut(
`endif
    .clk_i(clk_i),.rst_ni(rst_ni),.release_epoch_i(32'd1),
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
`ifdef TB_U_COMPUTE
      host_access(1,a_word,seed[9*j]);
      host_access(1,b_word,seed[9*j+4]);
      host_access(1,dst_word+1,seed[9*j+8]);
`elsif TB_F_COMPUTE
      host_access(1,a_word,seed[9*j]);
      if($test$plusargs("FADD")) host_access(1,b_word,seed[9*j+4]);
`else
      for(n=0;n<4;n=n+1) host_access(1,a_word+n,seed[9*j+n]);
      for(n=0;n<4;n=n+1) host_access(1,b_word+n,seed[9*j+4+n]);
`endif
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
`ifdef TB_U_COMPUTE
      host_access(0,dst_word+1,0);
`endif
    end
    $display("PASS A2 jobs=%0d status=%0d cycles=%0d",runs,expected,cycle); $finish;
  end
  initial begin #1000000; $fatal(1,"A2 watchdog"); end
endmodule
`endif

`ifndef TB_F_COMPUTE
`ifndef TB_U_COMPUTE
module tb_p_local(
`include "tb_network_lc_ports.svh"
  ,input wire [31:0] cycle_i,stall_i,
  output reg [31:0] image_id,
  input wire host_valid,host_write,input wire [9:0] host_word,input wire [127:0] host_data,
  output wire host_ready,host_ack,output wire [127:0] host_result
`ifdef TB_COMPUTE_HANDOFF
  ,output wire link_valid_o,input wire link_ready_i,output wire [1:0] link_kind_o,
  output wire [31:0] link_job_o,link_epoch_o,link_task_o,link_sequence_o,link_edge_o,
  output wire [7:0] link_peer_o,output wire [127:0] link_data_o,
  input wire done_valid_i,output wire done_ready_o
`endif
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
  wire g_req_valid,g_req_ready,g_rsp_valid,g_rsp_ready,g_error,g_saturated;
  wire [31:0] g_req_data,g_rsp_data;
  wire s_write_valid,s_write_ready,s_ack_ready;
  wire [3:0] s_req_ready,s_rsp_valid;
  wire [511:0] s_rsp_data;
  wire write_gate=write_age>=32'(stall_i)*3;
  wire ack_gate=ack_age>=32'(stall_i)*6;
  assign s_write_ready=s_req_ready[0] && write_gate;
  typedef struct packed {
    logic [1:0] kind;
    logic [2:0] token;
    logic [31:0] seq,job,epoch,task_id;
    logic [15:0] status;
    logic [31:0] bytes_read,bytes_written;
    logic saturated;
  } service_response;
  wire service_response compute_rsp, selected_rsp;
  wire compute_req_ready,compute_rsp_valid;
  assign compute_rsp.kind=0;
  assign {svc_rsp_kind_i,svc_rsp_token_i,svc_rsp_sequence_i,svc_rsp_job_i,
          svc_rsp_epoch_i,svc_rsp_task_sequence_i,svc_rsp_status_i,svc_rsp_read_bytes_i,
          svc_rsp_write_bytes_i,svc_rsp_saturated_i}=selected_rsp;
`ifdef TB_COMPUTE_HANDOFF
  wire compute_s_write=1'b1;
`include "tb_p_handoff_tx.svh"
`else
  assign host_ready=s_req_ready[3];
  assign host_ack=s_rsp_valid[3];
  assign host_result=s_rsp_data[384+:128];
  assign svc_req_ready_i=compute_req_ready;
  assign svc_rsp_valid_i=compute_rsp_valid;
  assign selected_rsp=compute_rsp;
  wire [3:0] request_valid={host_valid,2'b0,s_write_valid && write_gate};
  wire [3:0] request_write={host_write,2'b0,1'b1};
  wire [39:0] request_address={host_word,20'b0,s_write_word};
  wire [511:0] request_data={host_data,256'b0,s_write_data};
  wire [3:0] response_ready={1'b1,2'b0,s_ack_ready && ack_gate};
`endif
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
  lc_m_dot_store_adapter
`ifdef TB_P_SILU
    #(.SILU(1'b1))
`endif
  adapter(.clk(clk_i),.rst_n(rst_ni),
    .svc_valid(svc_req_valid_o && svc_req_kind_o==0),.svc_ready(compute_req_ready),.svc_kind(svc_req_kind_o),
    .svc_resource(svc_req_resource_o),.svc_token(svc_req_token_o),.svc_sequence(svc_req_sequence_o),
    .svc_job(svc_req_job_o),.svc_epoch(svc_req_epoch_o),.svc_task_sequence(svc_req_task_sequence_o),
    .svc_desc(svc_req_descriptor_o),.rsp_valid(compute_rsp_valid),.rsp_ready(svc_rsp_ready_o && compute_rsp_valid),
    .rsp_token(compute_rsp.token),.rsp_sequence(compute_rsp.seq),.rsp_job(compute_rsp.job),
    .rsp_epoch(compute_rsp.epoch),.rsp_task_sequence(compute_rsp.task_id),.rsp_status(compute_rsp.status),
    .rsp_read_bytes(compute_rsp.bytes_read),.rsp_write_bytes(compute_rsp.bytes_written),
    .rsp_saturated(compute_rsp.saturated),
    .load_valid(load_valid),.load_ready(load_ready),.load_a_word(load_a_word),.load_b_word(load_b_word),
    .load_done(load_done),.load_error(load_error),.load_take(load_take),
    .m_cmd_valid(m_cmd_valid),.m_cmd_ready(m_cmd_ready),.m_cmd_op(m_cmd_op),.m_cmd_data(m_cmd_data),
    .m_rsp_valid(m_rsp_valid),.m_rsp_error(m_rsp_error),.m_rsp_saturated(m_rsp_saturated),
    .m_rsp_data(m_rsp_data),.m_rsp_ready(m_rsp_ready),
    .g_req_valid(g_req_valid),.g_req_ready(g_req_ready),.g_req_data(g_req_data),
    .g_rsp_valid(g_rsp_valid),.g_rsp_ready(g_rsp_ready),.g_rsp_error(g_error),
    .g_rsp_saturated(g_saturated),.g_rsp_data(g_rsp_data),.s_write_valid(s_write_valid),
    .s_write_ready(s_write_ready),.s_write_word(s_write_word),.s_write_data(s_write_data),
    .s_ack_valid(s_rsp_valid[0] && ack_gate),.s_ack_data(s_rsp_data[0+:128]),.s_ack_ready(s_ack_ready));
  block_local_s_macro #(.CLIENTS(4),.WITH_FEEDER(1'b1)) private_s(
    .clk(clk_i),.reset(!rst_ni),.req_valid(request_valid),
    .req_write(request_write),.req_addr(request_address),
    .req_data(request_data),.req_ready(s_req_ready),.rsp_valid(s_rsp_valid),
    .rsp_ready(response_ready),.rsp_data(s_rsp_data),
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

`ifdef TB_P_SILU
  integer g_request_age=0,g_response_age=0;
  wire g_in_ready,g_out_valid;
  wire g_request_gate=g_request_age>=32'(stall_i)*2;
  wire g_response_gate=g_response_age>=32'(stall_i)*4;
  wire [2:0] g_fn=$test$plusargs("GFAULT") ? 3'd7 : 3'd0;
  assign g_req_ready=g_in_ready && g_request_gate;
  assign g_rsp_valid=g_out_valid && g_response_gate;
  block_v2_g macro_g(.clk(clk_i),.reset(!rst_ni),
    .in_valid(g_req_valid && g_request_gate),.in_ready(g_in_ready),
    .in_fn(g_fn),.in_gated(1'b0),.in_x(g_req_data),.in_gate(32'b0),
    .out_valid(g_out_valid),.out_ready(g_rsp_ready && g_response_gate),
    .out_data(g_rsp_data),.out_error(g_error),.out_saturated(g_saturated));
  always @(posedge clk_i) if(rst_ni) begin
    if(g_req_valid && g_req_ready) begin
      g_request_age<=0;
      $display("A2 %0d GIN %0d %08h",cycle_i,g_fn,g_req_data);
    end else if(g_req_valid && !g_request_gate) begin
      g_request_age<=g_request_age+1;
      $display("A2 %0d GHOLD_IN %0d %08h",cycle_i,g_fn,g_req_data);
    end
    if(g_rsp_valid && g_rsp_ready) begin
      g_response_age<=0;
      $display("A2 %0d GOUT %0d %0d %08h",cycle_i,g_error,g_saturated,g_rsp_data);
    end else if(g_out_valid && !g_response_gate) begin
      g_response_age<=g_response_age+1;
      $display("A2 %0d GHOLD_OUT %0d %0d %08h",cycle_i,g_error,g_saturated,g_rsp_data);
    end
    if(svc_rsp_valid_i && svc_rsp_ready_o)
      $display("A2 %0d SVC_SAT %0d",cycle_i,svc_rsp_saturated_i);
  end
`else
  assign g_req_ready=0;
  assign g_rsp_valid=0;
  assign g_error=0;
  assign g_saturated=0;
  assign g_rsp_data=0;
`endif

  always @(posedge clk_i) if(rst_ni) begin
    if(s_write_valid && !write_gate) begin
      write_age<=write_age+1;
      $display("A2 %0d WHELD %0d %032h",cycle_i,s_write_word,s_write_data);
    end
    if(s_write_valid && s_write_ready) write_age<=0;
    if(s_rsp_valid[0] && !ack_gate) ack_age<=ack_age+1;
    if(s_rsp_valid[0] && s_ack_ready && ack_gate) ack_age<=0;
    if(svc_req_valid_o && svc_req_ready_i && svc_req_kind_o==0) begin
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
    if(compute_rsp_valid && compute_rsp.status==0 && !ack_observed)
      $fatal(1,"successful service offered before real S ACK");
    if(compute_rsp_valid && svc_rsp_ready_o)
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
`ifdef TB_COMPUTE_HANDOFF
    if(!$value$plusargs("LOCAL0=%s",path) || !$value$plusargs("WORDS0=%d",words)) $fatal(1,"source image");
`else
    if(!$value$plusargs("LOCAL=%s",path) || !$value$plusargs("LWORDS=%d",words)) $fatal(1,"local image");
`endif
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
`endif
`endif
