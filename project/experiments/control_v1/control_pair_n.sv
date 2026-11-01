// Verification-only real S + N composition; no behavioral tensor bypass.
module control_pair_n(
 input wire clk,reset,input wire task_valid,output wire task_ready,input wire [255:0] task_data,
 output wire complete_valid,input wire complete_ready,output wire [63:0] complete_data,
 input wire init_mode,init_valid,init_write,input wire [9:0] init_address,input wire [127:0] init_data,
 output wire init_ready,init_response,output wire [127:0] init_rdata,input wire init_take
);
 wire s_req,s_wr,s_ready,s_valid,s_take;wire [9:0] s_addr;wire [127:0] s_din,s_dout;
 wire cmd_valid;wire cmd_ready;wire [3:0] cmd_op,cmd_count;wire [31:0] cmd_param;
 wire [127:0] cmd_data,cmd_aux;wire rsp_valid;wire rsp_ready;
 wire [127:0] rsp_data;wire rsp_error,rsp_saturated;
 control_adapter_n adapter(.clk(clk),.reset(reset),.task_valid(task_valid),.task_ready(task_ready),.task_data(task_data),.complete_valid(complete_valid),.complete_ready(complete_ready),.complete_data(complete_data),.s_req(s_req),.s_wr(s_wr),.s_addr(s_addr),.s_din(s_din),.s_ready(s_ready),.s_valid(s_valid),.s_take(s_take),.s_dout(s_dout),.cmd_valid(cmd_valid),.cmd_ready(cmd_ready),.cmd_op(cmd_op),.cmd_count(cmd_count),.cmd_param(cmd_param),.cmd_data(cmd_data),.cmd_aux(cmd_aux),.rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_data(rsp_data),.rsp_error(rsp_error),.rsp_saturated(rsp_saturated));
 wire unused_busy;
 block_v2_n arithmetic(.clk(clk),.reset(reset),.cmd_valid(cmd_valid),.cmd_ready(cmd_ready),.cmd_op(cmd_op),.cmd_count(cmd_count),.cmd_param(cmd_param),.cmd_data(cmd_data),.cmd_aux(cmd_aux),.rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_data(rsp_data),.rsp_error(rsp_error),.rsp_saturated(rsp_saturated), .busy(unused_busy));
 wire mem_ready,mem_valid;wire [127:0] mem_data;
 assign s_ready=!init_mode && mem_ready;assign s_valid=!init_mode && mem_valid;assign s_dout=mem_data;
 assign init_ready=init_mode && mem_ready;assign init_response=init_mode && mem_valid;assign init_rdata=mem_data;
 wire unused_lr,unused_done,unused_error,unused_sb,unused_av,unused_ab,unused_aw,unused_bv,unused_bb,unused_bw,unused_bh;
 wire [2:0] unused_ar;wire [1:0] unused_at,unused_bt;wire [127:0] unused_ad;wire [511:0] unused_bd;
 block_feed_s_macro storage(.clk(clk),.reset(reset),.req(init_mode?init_valid:s_req),.wr(init_mode?init_write:s_wr),
  .addr(init_mode?init_address:s_addr),.din(init_mode?init_data:s_din),.ready(mem_ready),.valid(mem_valid),
  .take(init_mode?init_take:s_take),.dout(mem_data),.load_valid(1'b0),.load_ready(unused_lr),.load_bank(1'b0),
  .load_rows(4'd0),.load_tiles(3'd0),.load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),
  .load_a_base(10'd0),.load_b_base(10'd0),.done_valid(unused_done),.done_take(1'b1),.done_error(unused_error),.busy(unused_sb),
  .a_valid(unused_av),.a_ready(1'b1),.a_bank(unused_ab),.a_row(unused_ar),.a_tile(unused_at),.a_wide(unused_aw),.a_data(unused_ad),
  .b_valid(unused_bv),.b_ready(1'b1),.b_bank(unused_bb),.b_tile(unused_bt),.b_wide(unused_bw),.b_half(unused_bh),.b_data(unused_bd));
endmodule
