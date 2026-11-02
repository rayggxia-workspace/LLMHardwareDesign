// Synchronous external state read: index/bank capture then data capture.
// Fixed latency two rising edges; read before write on collision. No ready/valid.
// Host must not consume reset/warm-up output. Compute/command ISA unchanged.
module r_stream_sync #(parameter WORDS=256)(
 input wire clk,reset,
 input wire load_valid,output wire load_ready,input wire [2:0] load_target,
 input wire [9:0] load_index,input wire [127:0] load_data,
 input wire rd_bank,input wire [9:0] rd_index,output reg [127:0] rd_data,
 input wire cmd_valid,output wire cmd_ready,input wire [2:0] cmd_op,
 input wire [8:0] cmd_rows,input wire cmd_role,cmd_clear,input wire [1:0] cmd_mode,
 output wire rsp_valid,input wire rsp_ready,output wire rsp_error,output wire [511:0] rsp_data
);
 reg rd_bank_q;
 reg [9:0] rd_index_q;
 wire [127:0] rd_comb;
 always @(posedge clk)begin
  if(reset)begin rd_bank_q<=0;rd_index_q<=0;rd_data<=0;end
  else begin rd_bank_q<=rd_bank;rd_index_q<=rd_index;rd_data<=rd_comb;end
 end
 r_stream #(.WORDS(WORDS)) core(
  .clk(clk),.reset(reset),.load_valid(load_valid),.load_ready(load_ready),
  .load_target(load_target),.load_index(load_index),.load_data(load_data),
  .rd_bank(rd_bank_q),.rd_index(rd_index_q),.rd_data(rd_comb),
  .cmd_valid(cmd_valid),.cmd_ready(cmd_ready),.cmd_op(cmd_op),.cmd_rows(cmd_rows),
  .cmd_role(cmd_role),.cmd_clear(cmd_clear),.cmd_mode(cmd_mode),
  .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_error(rsp_error),.rsp_data(rsp_data));
endmodule
