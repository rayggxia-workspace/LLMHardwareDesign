// Simulation-only selection wrapper: original sources are never edited.
// probe_* is verification-only and is never used by the modeled data path.
module research_top #(parameter ARCH=1,WORDS=256)(
 input wire clk,reset,
 input wire r_load_valid,output wire r_load_ready,input wire [2:0] r_load_target,input wire [9:0] r_load_index,input wire [127:0] r_load_data,
 input wire r_rd_bank,input wire [9:0] r_rd_index,output wire [127:0] r_rd_data,
 input wire r_cmd_valid,output wire r_cmd_ready,input wire [2:0] r_cmd_op,input wire [8:0] r_cmd_rows,input wire r_cmd_role,r_cmd_clear,input wire [1:0] r_cmd_mode,
 output wire r_rsp_valid,input wire r_rsp_ready,output wire r_rsp_error,output wire [511:0] r_rsp_data,
 input wire a_cmd_valid,output wire a_cmd_ready,input wire [3:0] a_cmd_op,input wire [9:0] a_cmd_index,input wire [127:0] a_cmd_data,
 output wire a_rsp_valid,input wire a_rsp_ready,output wire a_rsp_error,output wire [127:0] a_rsp_data,
 input wire c_in_valid,output wire c_in_ready,input wire [255:0] c_in_a,c_in_b,input wire [1:0] c_in_kind,
 output wire c_out_valid,input wire c_out_ready,output wire [511:0] c_out_data,output wire c_out_error,output wire [31:0] c_commands,
 input wire f_in_valid,output wire f_in_ready,input wire [511:0] f_in_a,f_in_b,input wire [5:0] f_in_shift,input wire [1:0] f_in_op,
 output wire f_out_valid,input wire f_out_ready,output wire [511:0] f_out_data,output wire f_out_error,
 input wire t_dma_idle,t_cmd_valid,output wire t_cmd_ready,input wire [3:0] t_cmd_op,input wire [4:0] t_cmd_context,
 input wire [31:0] t_cmd_owner,t_cmd_epoch,t_cmd_position,t_cmd_next,
 output wire t_rsp_valid,input wire t_rsp_ready,output wire t_rsp_error,output wire [127:0] t_rsp_data,
 output wire t_pending,output wire [31:0] t_outstanding,output wire t_role,
 input wire probe_bank,input wire [9:0] probe_index,output wire [127:0] probe_data,output wire probe_role
);
 txn_ctrl transaction(.clk(clk),.reset(reset),.dma_idle(t_dma_idle),.cmd_valid(t_cmd_valid),.cmd_ready(t_cmd_ready),.cmd_op(t_cmd_op),.cmd_context(t_cmd_context),.cmd_owner(t_cmd_owner),.cmd_epoch(t_cmd_epoch),.cmd_position(t_cmd_position),.cmd_next(t_cmd_next),.rsp_valid(t_rsp_valid),.rsp_ready(t_rsp_ready),.rsp_error(t_rsp_error),.rsp_data(t_rsp_data),.pending(t_pending),.outstanding(t_outstanding),.published_role(t_role));
 generate if(ARCH==0)begin:original
  wire unused;
  block_v1_r core(.clk(clk),.reset(reset),.cmd_valid(a_cmd_valid),.cmd_ready(a_cmd_ready),.cmd_op(a_cmd_op),.cmd_index(a_cmd_index),.cmd_data(a_cmd_data),.rsp_valid(a_rsp_valid),.rsp_ready(a_rsp_ready),.rsp_error(a_rsp_error),.rsp_data(a_rsp_data),.busy(unused));
  for(genvar p=0;p<4;p=p+1)assign probe_data[32*p+:32]=probe_bank?core.bank1[probe_index*4+p]:core.bank0[probe_index*4+p];
  assign probe_role=core.bank_role;
 end else begin
  assign a_cmd_ready=0;assign a_rsp_valid=0;assign a_rsp_error=0;assign a_rsp_data=0;
 end endgenerate
 generate if(ARCH==1)begin:stream
  r_stream #(.WORDS(WORDS))core(.clk(clk),.reset(reset),.load_valid(r_load_valid),.load_ready(r_load_ready),.load_target(r_load_target),.load_index(r_load_index),.load_data(r_load_data),.rd_bank(r_rd_bank),.rd_index(r_rd_index),.rd_data(r_rd_data),.cmd_valid(r_cmd_valid),.cmd_ready(r_cmd_ready),.cmd_op(r_cmd_op),.cmd_rows(r_cmd_rows),.cmd_role(r_cmd_role),.cmd_clear(r_cmd_clear),.cmd_mode(r_cmd_mode),.rsp_valid(r_rsp_valid),.rsp_ready(r_rsp_ready),.rsp_error(r_rsp_error),.rsp_data(r_rsp_data));
  assign probe_data=r_rd_data;assign probe_role=r_cmd_role;
 end else begin
  assign r_load_ready=0;assign r_rd_data=0;assign r_cmd_ready=0;assign r_rsp_valid=0;assign r_rsp_error=0;assign r_rsp_data=0;
 end endgenerate
 generate if(ARCH==2)begin:no_r
  c_wide_m core(.clk(clk),.reset(reset),.in_valid(c_in_valid),.in_ready(c_in_ready),.in_a(c_in_a),.in_b(c_in_b),.in_kind(c_in_kind),.out_valid(c_out_valid),.out_ready(c_out_ready),.out_data(c_out_data),.out_error(c_out_error),.command_count(c_commands));
  c_finish finish(.clk(clk),.reset(reset),.in_valid(f_in_valid),.in_ready(f_in_ready),.in_a(f_in_a),.in_b(f_in_b),.in_shift(f_in_shift),.in_op(f_in_op),.out_valid(f_out_valid),.out_ready(f_out_ready),.out_data(f_out_data),.out_error(f_out_error));
  assign probe_data=0;assign probe_role=0;
 end else begin
  assign c_in_ready=0;assign c_out_valid=0;assign c_out_data=0;assign c_out_error=0;assign c_commands=0;
  assign f_in_ready=0;assign f_out_valid=0;assign f_out_data=0;assign f_out_error=0;
 end endgenerate
 endmodule
