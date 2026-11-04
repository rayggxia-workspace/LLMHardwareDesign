// Bounded transaction transport, NOT an AXI or JEDEC HBM controller.
// Packet layout: {write:1, tag:16, word_address:10, payload:128}.
// Request retirement waits for the real S response and space in response FIFO.
module hbm_s_endpoint #(parameter integer LGDEPTH=4)(
 input wire core_clk,mem_clk,reset,hold_core,
 input wire in_valid,output wire in_ready,input wire [154:0] in_data,
 output wire out_valid,input wire out_ready,output wire [154:0] out_data,
 input wire load_valid,output wire load_ready,input wire done_take,
 output wire done_valid,done_error,
 output wire a_valid,input wire a_ready,output wire a_bank,
 output wire [2:0] a_row,output wire [1:0] a_tile,output wire a_wide,
 output wire [127:0] a_data,
 output wire b_valid,input wire b_ready,output wire b_bank,
 output wire [1:0] b_tile,output wire b_wide,b_half,output wire [511:0] b_data
);
 wire qvalid,qready;wire [154:0] packet;
 wire ack_ready,sready,svalid;wire [127:0] sdout;
 reg waiting;
 wire request=qvalid&&!waiting&&!hold_core;
 wire response=svalid&&waiting&&ack_ready&&!hold_core;
 assign qready=response;
 hbm_async_fifo #(.LGDEPTH(LGDEPTH)) requests(
  .wclk(mem_clk),.rclk(core_clk),.reset(reset),.wvalid(in_valid),.wready(in_ready),.wdata(in_data),
  .rvalid(qvalid),.rready(qready),.rdata(packet));
 hbm_async_fifo #(.LGDEPTH(LGDEPTH)) responses(
  .wclk(core_clk),.rclk(mem_clk),.reset(reset),.wvalid(svalid&&waiting&&!hold_core),
  .wready(ack_ready),.wdata({packet[154:128],sdout}),
  .rvalid(out_valid),.rready(out_ready),.rdata(out_data));
 always @(posedge core_clk)begin
  if(reset)waiting<=0;
  else begin
   if(request&&sready)waiting<=1;
   if(response)waiting<=0;
  end
 end
 wire unused_busy;
 block_feed_s_macro storage(
  .clk(core_clk),.reset(reset),.req(request),.wr(packet[154]),.addr(packet[137:128]),.din(packet[127:0]),
  .ready(sready),.valid(svalid),.take(response),.dout(sdout),
  .load_valid(load_valid),.load_ready(load_ready),.load_bank(1'b0),.load_rows(4'd8),.load_tiles(3'd4),
  .load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),.load_a_base(10'd0),.load_b_base(10'd64),
  .done_valid(done_valid),.done_take(done_take),.done_error(done_error),.busy(unused_busy),
  .a_valid(a_valid),.a_ready(a_ready),.a_bank(a_bank),.a_row(a_row),.a_tile(a_tile),.a_wide(a_wide),.a_data(a_data),
  .b_valid(b_valid),.b_ready(b_ready),.b_bank(b_bank),.b_tile(b_tile),.b_wide(b_wide),.b_half(b_half),.b_data(b_data));
endmodule
