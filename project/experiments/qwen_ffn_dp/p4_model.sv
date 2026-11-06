// Digital P4 wrapper with the SRAM backend explicitly selected.
module local_s_sram_p4 (
  input wire clk, reset,
  input wire [3:0] req_valid, req_write, rsp_ready,
  input wire [39:0] req_addr,
  input wire [511:0] req_data,
  output wire [3:0] req_ready, rsp_valid,
  output wire [511:0] rsp_data,
  output wire busy,
  input wire load_valid, load_bank, load_a_wide, load_b_wide, load_reuse_b,
  input wire [3:0] load_rows,
  input wire [2:0] load_tiles,
  input wire [9:0] load_a_base, load_b_base,
  output wire load_ready, done_valid, done_error,
  input wire done_take, a_ready, b_ready,
  output wire a_valid, a_bank, a_wide, b_valid, b_bank, b_wide, b_half,
  output wire [2:0] a_row,
  output wire [1:0] a_tile, b_tile,
  output wire [127:0] a_data,
  output wire [511:0] b_data
);
  block_local_s_macro #(.CLIENTS(4), .WITH_FEEDER(1), .USE_SRAM(1)) impl (.*);
endmodule
