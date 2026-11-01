// Separate SRAM S variant: four256x128 1RW banks plus the unchanged M feeder.
// One extra registered response stage; feeder waits for actual mem_valid.
// Legacy128 accesses remain available to V/R/T or initialization. They contend
// with feeder reads for the same real banks; they are not additional RAM ports.
module block_feed_s_macro_sram (
 input wire clk,reset,
 input wire req,wr,input wire [9:0] addr,input wire [127:0] din,
 output wire ready,valid,input wire take,output wire [127:0] dout,
 input wire load_valid,output wire load_ready,
 input wire load_bank,input wire [3:0] load_rows,input wire [2:0] load_tiles,
 input wire load_a_wide,load_b_wide,load_reuse_b,
 input wire [9:0] load_a_base,load_b_base,
 output wire done_valid,input wire done_take,output wire done_error,busy,
 output wire a_valid,input wire a_ready,output wire a_bank,
 output wire [2:0] a_row,output wire [1:0] a_tile,
 output wire a_wide,output wire [127:0] a_data,
 output wire b_valid,input wire b_ready,output wire b_bank,
 output wire [1:0] b_tile,output wire b_wide,b_half,output wire [511:0] b_data
`ifdef USE_POWER_PINS
 ,inout wire vdd,gnd
`endif
);
 wire mem_req,mem_ready,mem_valid,mem_take;wire [7:0] mem_addr;wire [511:0] mem_data;
 block_feed_s16k_sram storage(.clk(clk),.reset(reset),.req(req),.wr(wr),.addr(addr),.din(din),
   .ready(ready),.valid(valid),.take(take),.dout(dout),.wide_req(mem_req),.wide_addr(mem_addr),
   .wide_ready(mem_ready),.wide_valid(mem_valid),.wide_take(mem_take),.wide_dout(mem_data)
`ifdef USE_POWER_PINS
   ,.vdd(vdd),.gnd(gnd)
`endif
   );
 block_feed_loader feeder(.clk(clk),.reset(reset),.load_valid(load_valid),.load_ready(load_ready),
   .load_bank(load_bank),.load_rows(load_rows),.load_tiles(load_tiles),.load_a_wide(load_a_wide),
   .load_b_wide(load_b_wide),.load_reuse_b(load_reuse_b),.load_a_base(load_a_base),.load_b_base(load_b_base),
   .done_valid(done_valid),.done_take(done_take),.done_error(done_error),.busy(busy),
   .mem_req(mem_req),.mem_addr(mem_addr),.mem_ready(mem_ready),.mem_valid(mem_valid),.mem_take(mem_take),.mem_data(mem_data),
   .a_valid(a_valid),.a_ready(a_ready),.a_bank(a_bank),.a_row(a_row),.a_tile(a_tile),.a_wide(a_wide),.a_data(a_data),
   .b_valid(b_valid),.b_ready(b_ready),.b_bank(b_bank),.b_tile(b_tile),.b_wide(b_wide),.b_half(b_half),.b_data(b_data));
endmodule
