// Integration TEST FIXTURE: two physical candidates S and M plus unchanged T.
// Test allow signals deliberately stall real A/B handshakes. The T routing mux
// is explicit active test glue, NOT a zero-cost proposed M11/M12 feature.
module block_feed_pair (
 input wire clk,reset,
 input wire req,wr,input wire [9:0] addr,input wire [127:0] din,
 output wire ready,valid,input wire take,output wire [127:0] dout,
 input wire load_valid,output wire load_ready,
 input wire load_bank,input wire [3:0] load_rows,input wire [2:0] load_tiles,
 input wire load_a_wide,load_b_wide,load_reuse_b,input wire [9:0] load_a_base,load_b_base,
 output wire done_valid,input wire done_take,output wire done_error,load_busy,
 input wire a_allow,b_allow,
 input wire cmd_valid,output wire cmd_ready,input wire [3:0] cmd_op,
 input wire [5:0] cmd_index,input wire [63:0] cmd_data,
 output wire rsp_valid,input wire rsp_ready,output wire [127:0] rsp_data,
 output wire rsp_error,rsp_saturated,busy,
 output wire a_fire,b_fire,mem_fire,
 input wire capture_to_t,output wire capture_fire,
 input wire t_begin_valid,output wire t_begin_ready,input wire [9:0] t_words,
 input wire t_commit,output wire t_commit_ready,
 output wire t_read_valid,input wire t_read_take,output wire [127:0] t_read_data,
 output wire t_read_last,input wire t_release,output wire t_release_ready,
 output wire t_error
);
 wire av,ar,ab,aw,bv,br,bb,bw,bh;wire [2:0] row;wire [1:0] at,bt;
 wire [127:0] ad;wire [511:0] bd;
 block_feed_s_macro store(.clk(clk),.reset(reset),.req(req),.wr(wr),.addr(addr),.din(din),
  .ready(ready),.valid(valid),.take(take),.dout(dout),
  .load_valid(load_valid),.load_ready(load_ready),.load_bank(load_bank),.load_rows(load_rows),
  .load_tiles(load_tiles),.load_a_wide(load_a_wide),.load_b_wide(load_b_wide),.load_reuse_b(load_reuse_b),
  .load_a_base(load_a_base),.load_b_base(load_b_base),.done_valid(done_valid),.done_take(done_take),
  .done_error(done_error),.busy(load_busy),
  .a_valid(av),.a_ready(ar&&a_allow),.a_bank(ab),.a_row(row),.a_tile(at),.a_wide(aw),.a_data(ad),
  .b_valid(bv),.b_ready(br&&b_allow),.b_bank(bb),.b_tile(bt),.b_wide(bw),.b_half(bh),.b_data(bd));
 wire mv,mr,me;wire [127:0] md;
 block_feed_m engine(.clk(clk),.reset(reset),.a_valid(av&&a_allow),.a_ready(ar),.a_bank(ab),
  .a_row(row),.a_tile(at),.a_wide(aw),.a_data(ad),.b_valid(bv&&b_allow),.b_ready(br),
  .b_bank(bb),.b_tile(bt),.b_wide(bw),.b_half(bh),.b_data(bd),
  .cmd_valid(cmd_valid),.cmd_ready(cmd_ready),.cmd_op(cmd_op),.cmd_index(cmd_index),.cmd_data(cmd_data),
  .rsp_valid(mv),.rsp_ready(mr),.rsp_data(md),.rsp_error(me),.rsp_saturated(rsp_saturated),.busy(busy));
 assign a_fire=av&&ar&&a_allow;assign b_fire=bv&&br&&b_allow;
 assign mem_fire=store.mem_req&&store.mem_ready;
 reg route_to_t;reg [9:0] t_index;
 wire t_write_ready;
 assign mr=route_to_t&&!me?t_write_ready:rsp_ready;
 assign rsp_valid=mv&&(!route_to_t||me);assign rsp_data=md;assign rsp_error=me;
 assign capture_fire=route_to_t&&mv&&!me&&t_write_ready;
 always @(posedge clk)begin
  if(reset)begin route_to_t<=0;t_index<=0;end
  else begin
   if(cmd_valid&&cmd_ready)route_to_t<=capture_to_t&&cmd_op==5;
   else if(mv&&mr)route_to_t<=0;
   if(t_begin_valid&&t_begin_ready)t_index<=0;
   else if(capture_fire)t_index<=t_index+1'b1;
  end
 end
 wire t_busy,t_sealed,t_committed;wire [1:0] t_owner;
 wire [31:0] t_generation;wire [9:0] t_count,t_read_index;wire [2:0] t_state;wire t_revoke_ready;
 transaction6k transaction(.clk(clk),.reset(reset),.begin_valid(t_begin_valid),.begin_ready(t_begin_ready),
  .begin_owner(2'b00),.begin_generation(32'd130),.begin_words(t_words),
  .write_valid(route_to_t&&mv&&!me),.write_ready(t_write_ready),.write_index(t_index),.write_data(md),
  .commit_valid(t_commit),.commit_ready(t_commit_ready),.revoke_valid(1'b0),.revoke_ready(t_revoke_ready),
  .read_valid(t_read_valid),.read_take(t_read_take),.read_index(t_read_index),.read_data(t_read_data),
  .read_last(t_read_last),.owner(t_owner),.generation(t_generation),.word_count(t_count),
  .release_valid(t_release),.release_ready(t_release_ready),.busy(t_busy),.sealed(t_sealed),
  .committed(t_committed),.protocol_error(t_error),.debug_state(t_state));
 // These state/lease checks are observable in the fixture, rather than ignored
 // outputs or extra real macro pins. They do not modify the production T RTL.
 wire unused_lease=^{t_busy,t_sealed,t_committed,t_owner,t_generation,t_count,t_read_index,t_state,t_revoke_ready};
endmodule
