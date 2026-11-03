// Private 16KiB S per Block. The accepted legacy storage and loader are reused
// byte-for-byte. All added arbitration state belongs to this physical wrapper.
module block_local_s_macro #(
 parameter integer CLIENTS=4,
 parameter bit WITH_FEEDER=1'b0
)(
 input wire clk,reset,
 input wire [CLIENTS-1:0] req_valid,req_write,
 input wire [CLIENTS*10-1:0] req_addr,
 input wire [CLIENTS*128-1:0] req_data,
 output wire [CLIENTS-1:0] req_ready,rsp_valid,
 input wire [CLIENTS-1:0] rsp_ready,
 output wire [CLIENTS*128-1:0] rsp_data,
 input wire load_valid, output wire load_ready,
 input wire load_bank,input wire [3:0] load_rows,input wire [2:0] load_tiles,
 input wire load_a_wide,load_b_wide,load_reuse_b,
 input wire [9:0] load_a_base,load_b_base,
 output wire done_valid,input wire done_take,output wire done_error,
 output wire busy,
 output wire a_valid,input wire a_ready,output wire a_bank,
 output wire [2:0] a_row,output wire [1:0] a_tile,
 output wire a_wide,output wire [127:0] a_data,
 output wire b_valid,input wire b_ready,output wire b_bank,
 output wire [1:0] b_tile,
 output wire b_wide,b_half,output wire [511:0] b_data
);
 wire narrow_req,narrow_write,narrow_ready,narrow_valid,narrow_take,arb_busy;
 wire [9:0] narrow_addr;
 wire [127:0] narrow_data,narrow_result;
 wire feed_req,feed_ready,feed_valid,feed_take,feed_busy;
 wire [7:0] feed_addr;
 wire [511:0] feed_data;
 wire wide_ready,wide_req,wide_fire;
 reg prefer_wide;
 // Alternate accepted narrow/wide operations when both are eligible. A held
 // wide response cannot monopolize banks; no extra RAM port is introduced.
 assign wide_req=feed_req && (!narrow_req || prefer_wide);
 assign feed_ready=wide_ready && (!narrow_req || prefer_wide);
 assign wide_fire=wide_req && wide_ready;
 always @(posedge clk) begin
  if(reset) prefer_wide<=0;
  else if(wide_fire) prefer_wide<=0;
  else if(narrow_req && narrow_ready) prefer_wide<=1;
 end
 block_local_s_arbiter #(.CLIENTS(CLIENTS)) local_port(
  .clk(clk),.reset(reset),.req_valid(req_valid),.req_write(req_write),
  .req_addr(req_addr),.req_data(req_data),.req_ready(req_ready),
  .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_data(rsp_data),
  .mem_req(narrow_req),.mem_write(narrow_write),.mem_addr(narrow_addr),
  .mem_data(narrow_data),.mem_ready(narrow_ready),.mem_valid(narrow_valid),
  .mem_result(narrow_result),.mem_take(narrow_take),.busy(arb_busy));
 block_feed_s16k storage(
  .clk(clk),.reset(reset),.req(narrow_req),.wr(narrow_write),.addr(narrow_addr),
  .din(narrow_data),.ready(narrow_ready),.valid(narrow_valid),.take(narrow_take),
  .dout(narrow_result),.wide_req(wide_req),.wide_addr(feed_addr),
  .wide_ready(wide_ready),.wide_valid(feed_valid),.wide_take(feed_take),.wide_dout(feed_data));
 generate if(WITH_FEEDER) begin: with_feeder
  block_feed_loader feeder(
   .clk(clk),.reset(reset),.load_valid(load_valid),.load_ready(load_ready),
   .load_bank(load_bank),.load_rows(load_rows),.load_tiles(load_tiles),
   .load_a_wide(load_a_wide),.load_b_wide(load_b_wide),.load_reuse_b(load_reuse_b),
   .load_a_base(load_a_base),.load_b_base(load_b_base),
   .done_valid(done_valid),.done_take(done_take),.done_error(done_error),.busy(feed_busy),
   .mem_req(feed_req),.mem_addr(feed_addr),.mem_ready(feed_ready),
   .mem_valid(feed_valid),.mem_take(feed_take),.mem_data(feed_data),
   .a_valid(a_valid),.a_ready(a_ready),.a_bank(a_bank),.a_row(a_row),.a_tile(a_tile),
   .a_wide(a_wide),.a_data(a_data),.b_valid(b_valid),.b_ready(b_ready),.b_bank(b_bank),
   .b_tile(b_tile),.b_wide(b_wide),.b_half(b_half),.b_data(b_data));
 end else begin: without_feeder
  assign feed_req=0; assign feed_addr=0; assign feed_take=0; assign feed_busy=0;
  assign load_ready=0; assign done_valid=0; assign done_error=0;
  assign a_valid=0; assign a_bank=0; assign a_row=0; assign a_tile=0;
  assign a_wide=0; assign a_data=0;
  assign b_valid=0; assign b_bank=0; assign b_tile=0;
  assign b_wide=0; assign b_half=0; assign b_data=0;
 end endgenerate
 assign busy=arb_busy || feed_busy;
endmodule
