// Verification-only combinational wiring; no new state or qualified hardware.
module pair_re(
 input wire clk,reset,
 input wire load_valid,output wire load_ready,input wire [2:0] load_target,
 input wire [9:0] load_index,input wire [127:0] load_data,
 input wire rd_bank,input wire [9:0] rd_index,input wire rd_valid,output wire rd_ready,
 input wire [4:0] shift,
 output wire out_valid,input wire out_ready,output wire [127:0] out_data,
 output wire out_error,out_saturated,
 output wire raw_valid,raw_ready,output wire [127:0] raw_data
);
 r_stream_local #(.WORDS(256)) r(
  .clk(clk),.reset(reset),.load_valid(load_valid),.load_ready(load_ready),
  .load_target(load_target),.load_index(load_index),.load_data(load_data),
  .rd_bank(rd_bank),.rd_index(rd_index),.rd_valid(rd_valid),.rd_ready(rd_ready),
  .rd_rsp_valid(raw_valid),.rd_rsp_ready(raw_ready),.rd_data(raw_data),
  .cmd_valid(1'b0),.cmd_ready(),.cmd_op(3'b0),.cmd_rows(9'b0),
  .cmd_role(1'b0),.cmd_clear(1'b0),.cmd_mode(2'b0),
  .rsp_valid(),.rsp_ready(1'b1),.rsp_error(),.rsp_data()
 );
 block_v2_e e(.clk(clk),.reset(reset),.in_valid(raw_valid),.in_ready(raw_ready),
  .in_op(4'd13),.in_shift(shift),.in_a(raw_data),.in_b(128'b0),.in_c(128'b0),
  .out_valid(out_valid),.out_ready(out_ready),.out_data(out_data),
  .out_error(out_error),.out_saturated(out_saturated));
endmodule
