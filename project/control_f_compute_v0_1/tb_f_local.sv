`timescale 1ns/1ps
module tb_f_local(
`include "tb_network_lc_ports.svh"
  ,input wire [31:0] cycle_i,stall_i,
  output reg [31:0] image_id,
  input wire host_valid,host_write,input wire [9:0] host_word,input wire [127:0] host_data,
  output wire host_ready,host_ack,output wire [127:0] host_result
`ifdef TB_F_HANDOFF
  ,output wire link_valid_o,input wire link_ready_i,output wire [1:0] link_kind_o,
  output wire [31:0] link_job_o,link_epoch_o,link_task_o,link_sequence_o,link_edge_o,
  output wire [7:0] link_peer_o,output wire [127:0] link_data_o,
  input wire done_valid_i,output wire done_ready_o
`endif
`ifdef TB_F_RECOVERY
  ,input wire config_go_i
`endif
);
  localparam [7:0] BLOCK=0;
`include "tb_network_lc_wires.svh"

  wire s_valid,s_ready,s_write,s_take;
  wire [9:0] s_word;
  wire [127:0] s_data;
`ifdef TB_F_HANDOFF
  localparam integer S_CLIENTS=4;
`else
  localparam integer S_CLIENTS=2;
`endif
  wire [S_CLIENTS-1:0] s_req_ready,s_rsp_valid;
  wire [128*S_CLIENTS-1:0] s_rsp_data;
  wire g_valid,g_ready,g_take,g_out_valid,g_error,g_sat;
  wire [31:0] g_x,g_y;
  wire e_valid,e_ready,e_take,e_out_valid,e_error,e_sat;
  wire [127:0] e_a,e_b,e_y;
  int g_req_age=0,g_rsp_age=0,e_req_age=0,e_rsp_age=0,write_age=0,ack_age=0;
  wire g_req_gate=g_req_age>=int'(stall_i)*2;
  wire g_rsp_gate=g_rsp_age>=int'(stall_i)*3;
  wire e_req_gate=e_req_age>=int'(stall_i)*2;
  wire e_rsp_gate=e_rsp_age>=int'(stall_i)*3;
  wire s_req_gate=!s_write || write_age>=int'(stall_i)*4;
  reg expect_write_ack=0,write_ack_seen=0;
  wire s_rsp_gate=!expect_write_ack || ack_age>=int'(stall_i)*5;
  wire [2:0] g_fn=$test$plusargs("GFAULT") ? 3'd7 : 3'd0;
  wire [3:0] e_op=$test$plusargs("EFAULT") ? 4'd14 : 4'd0;

  typedef struct packed {
    logic [1:0] kind;
    logic [2:0] token;
    logic [31:0] seq,job,epoch,task_id;
    logic [15:0] status;
    logic [31:0] bytes_read,bytes_written;
    logic saturated;
  } service_response;
  wire service_response compute_rsp,selected_rsp;
  wire compute_req_ready,compute_rsp_valid;
  assign compute_rsp.kind=0;
  assign {svc_rsp_kind_i,svc_rsp_token_i,svc_rsp_sequence_i,svc_rsp_job_i,
          svc_rsp_epoch_i,svc_rsp_task_sequence_i,svc_rsp_status_i,svc_rsp_read_bytes_i,
          svc_rsp_write_bytes_i,svc_rsp_saturated_i}=selected_rsp;
`ifdef TB_F_HANDOFF
  wire s_write_valid=s_valid,write_gate=s_req_gate,compute_s_write=s_write;
  wire s_ack_ready=s_take,ack_gate=s_rsp_gate;
  wire [9:0] s_write_word=s_word;
  wire [127:0] s_write_data=s_data;
`include "tb_p_handoff_tx.svh"
`else
  assign host_ready=s_req_ready[1];
  assign host_ack=s_rsp_valid[1];
  assign host_result=s_rsp_data[128+:128];
  assign svc_req_ready_i=compute_req_ready;
  assign svc_rsp_valid_i=compute_rsp_valid;
  assign selected_rsp=compute_rsp;
  wire [1:0] request_valid={host_valid,s_valid && s_req_gate};
  wire [1:0] request_write={host_write,s_write};
  wire [19:0] request_address={host_word,s_word};
  wire [255:0] request_data={host_data,s_data};
  wire [1:0] response_ready={1'b1,s_take && s_rsp_gate};
`endif
  assign s_ready=s_req_ready[0] && s_req_gate;
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

  lc_f_store_adapter adapter(
    .clk(clk_i),.rst_n(rst_ni),.svc_valid(svc_req_valid_o && svc_req_kind_o==0),.svc_ready(compute_req_ready),
    .svc_resource({5'b0,svc_req_resource_o}),.svc_token(svc_req_token_o),.svc_sequence(svc_req_sequence_o),
    .svc_job(svc_req_job_o),.svc_epoch(svc_req_epoch_o),.svc_task_sequence(svc_req_task_sequence_o),
    .svc_desc(svc_req_descriptor_o),.rsp_valid(compute_rsp_valid),.rsp_ready(svc_rsp_ready_o && compute_rsp_valid),
    .rsp_token(compute_rsp.token),.rsp_sequence(compute_rsp.seq),.rsp_job(compute_rsp.job),
    .rsp_epoch(compute_rsp.epoch),.rsp_task_sequence(compute_rsp.task_id),.rsp_status(compute_rsp.status),
    .rsp_read_bytes(compute_rsp.bytes_read),.rsp_write_bytes(compute_rsp.bytes_written),.rsp_saturated(compute_rsp.saturated),
    .s_valid(s_valid),.s_ready(s_ready),.s_write(s_write),.s_word(s_word),.s_data(s_data),
    .s_rsp_valid(s_rsp_valid[0] && s_rsp_gate),.s_rsp_ready(s_take),.s_rsp_data(s_rsp_data[0+:128]),
    .g_valid(g_valid),.g_ready(g_ready && g_req_gate),.g_x(g_x),
    .g_rsp_valid(g_out_valid && g_rsp_gate),.g_rsp_ready(g_take),.g_result(g_y),.g_error(g_error),.g_saturated(g_sat),
    .e_valid(e_valid),.e_ready(e_ready && e_req_gate),.e_a(e_a),.e_b(e_b),
    .e_rsp_valid(e_out_valid && e_rsp_gate),.e_rsp_ready(e_take),.e_result(e_y),.e_error(e_error),.e_saturated(e_sat));

  block_local_s_macro #(.CLIENTS(S_CLIENTS)) private_s(
    .clk(clk_i),.reset(!rst_ni),.req_valid(request_valid),
    .req_write(request_write),.req_addr(request_address),.req_data(request_data),
    .req_ready(s_req_ready),.rsp_valid(s_rsp_valid),.rsp_ready(response_ready),.rsp_data(s_rsp_data),
    .load_valid(1'b0),.load_ready(),.load_bank(1'b0),.load_rows(4'b0),.load_tiles(3'b0),
    .load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),.load_a_base(10'b0),.load_b_base(10'b0),
    .done_valid(),.done_take(1'b0),.done_error(),.busy(),
    .a_valid(),.a_ready(1'b0),.a_bank(),.a_row(),.a_tile(),.a_wide(),.a_data(),
    .b_valid(),.b_ready(1'b0),.b_bank(),.b_tile(),.b_wide(),.b_half(),.b_data());
  block_v2_g macro_g(.clk(clk_i),.reset(!rst_ni),
    .in_valid(g_valid && g_req_gate),.in_ready(g_ready),.in_fn(g_fn),.in_gated(1'b0),.in_x(g_x),.in_gate(32'b0),
    .out_valid(g_out_valid),.out_ready(g_take && g_rsp_gate),.out_data(g_y),.out_error(g_error),.out_saturated(g_sat));
  block_v2_e macro_e(.clk(clk_i),.reset(!rst_ni),
    .in_valid(e_valid && e_req_gate),.in_ready(e_ready),.in_op(e_op),.in_shift(5'b0),.in_a(e_a),.in_b(e_b),.in_c(128'b0),
    .out_valid(e_out_valid),.out_ready(e_take && e_rsp_gate),.out_data(e_y),.out_error(e_error),.out_saturated(e_sat));

  always @(posedge clk_i) if(rst_ni) begin
    if(trace_retire_o) $display("F73 %0d RETIRE %02h",cycle_i,trace_opcode_o);
    if(svc_req_valid_o && svc_req_ready_i && svc_req_kind_o==0) begin
      write_ack_seen<=0;
      $display("F73 %0d EXEC %0d %0d %0d %0d %0d %0d",cycle_i,svc_req_job_o,
        svc_req_epoch_o,svc_req_task_sequence_o,svc_req_sequence_o,svc_req_token_o,svc_req_resource_o);
    end
    if(g_valid && !g_req_gate) begin
      g_req_age<=g_req_age+1; $display("F73 %0d GIN_H %0d %08h",cycle_i,g_fn,g_x);
    end
    if(g_valid && g_ready && g_req_gate) begin
      g_req_age<=0; $display("F73 %0d GIN %0d %08h",cycle_i,g_fn,g_x);
    end
    if(g_out_valid && !g_rsp_gate) begin
      g_rsp_age<=g_rsp_age+1; $display("F73 %0d GOUT_H %0d %0d %08h",cycle_i,g_error,g_sat,g_y);
    end
    if(g_out_valid && g_take && g_rsp_gate) begin
      g_rsp_age<=0; $display("F73 %0d GOUT %0d %0d %08h",cycle_i,g_error,g_sat,g_y);
    end
    if(e_valid && !e_req_gate) begin
      e_req_age<=e_req_age+1; $display("F73 %0d EIN_H %0d %032h %032h",cycle_i,e_op,e_a,e_b);
    end
    if(e_valid && e_ready && e_req_gate) begin
      e_req_age<=0; $display("F73 %0d EIN %0d %032h %032h",cycle_i,e_op,e_a,e_b);
    end
    if(e_out_valid && !e_rsp_gate) begin
      e_rsp_age<=e_rsp_age+1; $display("F73 %0d EOUT_H %0d %0d %032h",cycle_i,e_error,e_sat,e_y);
    end
    if(e_out_valid && e_take && e_rsp_gate) begin
      e_rsp_age<=0; $display("F73 %0d EOUT %0d %0d %032h",cycle_i,e_error,e_sat,e_y);
    end
    if(s_valid && s_write && !s_req_gate) begin
      write_age<=write_age+1; $display("F73 %0d WRITE_H %0d %032h",cycle_i,s_word,s_data);
    end
    if(s_valid && s_ready) begin
      if(s_write) begin
        write_age<=0; expect_write_ack<=1; $display("F73 %0d WRITE %0d %032h",cycle_i,s_word,s_data);
      end else $display("F73 %0d READ %0d",cycle_i,s_word);
    end
    if(s_rsp_valid[0] && !s_rsp_gate) begin
      ack_age<=ack_age+1; $display("F73 %0d ACK_H %032h",cycle_i,s_rsp_data[0+:128]);
    end
    if(s_rsp_valid[0] && s_take && s_rsp_gate) begin
      if(expect_write_ack) begin
        ack_age<=0; expect_write_ack<=0; write_ack_seen<=1;
        $display("F73 %0d ACK %032h",cycle_i,s_rsp_data[0+:128]);
      end else $display("F73 %0d READ_RSP %032h",cycle_i,s_rsp_data[0+:128]);
    end
    if(compute_rsp_valid && compute_rsp.status==0 && !write_ack_seen)
      $fatal(1,"successful F completion offered before actual S write response");
    if(compute_rsp_valid && svc_rsp_ready_o)
      $display("F73 %0d SERVICE %0d %0d %0d %0d %0d %0d %0d %0d %0d",cycle_i,svc_rsp_job_i,
        svc_rsp_epoch_i,svc_rsp_task_sequence_i,svc_rsp_sequence_i,svc_rsp_token_i,svc_rsp_status_i,
        svc_rsp_read_bytes_i,svc_rsp_write_bytes_i,svc_rsp_saturated_i);
  end

  reg [127:0] image[0:519];
  string path;
  integer words,n;
  task automatic cfg(input [2:0] op,input integer address,input [127:0] data,
                     input [31:0] abi,input [15:0] status);
    @(negedge clk_i);
    cfg_req_valid_i=1; cfg_req_op_i=op; cfg_req_generation_i=
`ifdef TB_F_RECOVERY
      deploy_generation_i;
`else
      1;
`endif
       cfg_req_address_i=14'(address);
    cfg_req_data_i=data; cfg_req_proof_i=1; cfg_req_total_bytes_i=16'(words*16);
    cfg_req_image_id_i=image_id; cfg_req_topology_id_i=image[4][0+:32];
    cfg_req_abi_id_i=abi; cfg_req_capacity_id_i=image[5][32+:32];
    @(posedge clk_i); while(!cfg_req_ready_o) @(posedge clk_i);
    @(negedge clk_i); cfg_req_valid_i=0;
    while(!cfg_rsp_valid_o) @(negedge clk_i);
    if(cfg_rsp_status_o!=status || (op==2 && cfg_rsp_data_o!==image[address>>4]))
      $fatal(1,"F config/readback op=%0d expected=%0d actual=%0d",op,status,cfg_rsp_status_o);
    cfg_rsp_ready_i=1; @(negedge clk_i); cfg_rsp_ready_i=0;
  endtask

  initial begin
    release_valid_i=0; release_sequence_i=0;
    cfg_req_valid_i=0; cfg_req_op_i=0; cfg_req_generation_i=0; cfg_req_address_i=0; cfg_req_data_i=0;
    cfg_req_total_bytes_i=0; cfg_req_image_id_i=0; cfg_req_topology_id_i=0; cfg_req_abi_id_i=0;
    cfg_req_capacity_id_i=0; cfg_req_proof_i=0; cfg_rsp_ready_i=0;
    if(!$value$plusargs("LOCAL=%s",path) || !$value$plusargs("LWORDS=%d",words)) $fatal(1,"F local image");
    $readmemh(path,image,0,words-1);
    image_id=image[3][96+:32];
`ifdef TB_F_RECOVERY
    forever begin
      wait(rst_ni && config_go_i);
`endif
    wait(rst_ni); @(negedge clk_i); release_valid_i=1; release_sequence_i=release_epoch_i;
    @(negedge clk_i); release_valid_i=0;
    if($test$plusargs("BADCFG")) begin
      cfg(0,0,0,32'h00010001,3);
      if(life_o!=1 || image_valid_o) $fatal(1,"wrong F ABI granted");
      $display("F73 %0d BAD_ABI_REJECTED",cycle_i);
    end
    cfg(0,0,0,image[4][32+:32],0);
    for(n=0;n<words;n=n+1) cfg(1,n*16,image[n],image[4][32+:32],0);
    for(n=0;n<words;n=n+1) cfg(2,n*16,0,image[4][32+:32],0);
    cfg(3,0,0,image[4][32+:32],0); cfg(4,0,0,image[4][32+:32],0);
    $display("F73 %0d CONFIG_READBACK %0d",cycle_i,words);
`ifdef TB_F_RECOVERY
      $display("REC %0d RELOAD %0d %0d",cycle_i,BLOCK,deploy_generation_i);
      wait(!rst_ni);
    end
`endif
  end
endmodule
