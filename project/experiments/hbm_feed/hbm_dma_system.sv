// Real RTL DMA/arbiter + independent channel CDC + original private S/M.
// HBM protocol and physical timing remain outside this verification system.
module hbm_dma_system #(parameter integer GROUPS=4,S_PER_GROUP=4,SLOTS=8,
 NS=GROUPS*S_PER_GROUP,CHANNELS=4,LGDEPTH=4)(
 input wire core_clk,mem_clk,reset,input wire [2:0] channel_count,input wire [3:0] credit_limit,
 input wire [NS-1:0] desc_valid,desc_write,complete_ready,hold_s,
 output wire [NS-1:0] desc_ready,complete_valid,busy,
 input wire [39:0] desc_address[NS],input wire [9:0] desc_local[NS],
 input wire [10:0] desc_words[NS],input wire [15:0] desc_tag[NS],
 output wire [1:0] complete_status[NS],output wire [15:0] complete_tag[NS],
 output wire [10:0] completed_words[NS],output wire protocol_error,
 output wire [3:0] live_count[NS],
 output wire [CHANNELS-1:0] mem_valid,input wire [CHANNELS-1:0] mem_ready,
 output wire [184:0] mem_data[CHANNELS],
 input wire [CHANNELS-1:0] response_valid,output wire [CHANNELS-1:0] response_ready,
 input wire [145:0] response_data[CHANNELS],
 output wire [CHANNELS-1:0] grant_valid,output wire [3:0] grant_s[CHANNELS],
 input wire [3:0] select_s,input wire load_valid,output wire load_ready,
 input wire done_take,output wire done_valid,done_error,input wire a_allow,b_allow,
 input wire cmd_valid,output wire cmd_ready,input wire [3:0] cmd_op,
 input wire [5:0] cmd_index,input wire [63:0] cmd_data,
 output wire rsp_valid,input wire rsp_ready,output wire [127:0] rsp_data,
 output wire rsp_error,rsp_saturated,output wire [NS-1:0] a_fire,b_fire,
 output wire [NS-1:0] s_accept,s_ack,output wire [9:0] observed_address[NS],
 output wire [127:0] observed_data[NS],output wire [NS-1:0] observed_request,observed_write,observed_ready,eligible_debug
);
 wire [NS*40-1:0] da;wire [NS*10-1:0] dl,sa;wire [NS*11-1:0] dw,cw;
 wire [NS*16-1:0] dt,ct;wire [NS*2-1:0] cs;wire [NS*4-1:0] lc;
 wire [NS*128-1:0] sd,sr;
 wire [NS-1:0] req,wr,take,ready,valid,native_ready;
 wire [CHANNELS-1:0] qvalid,qready,rvalid,rready;
 wire [CHANNELS*185-1:0] qdata;wire [CHANNELS*146-1:0] rdata;wire [CHANNELS*4-1:0] gs;
 hbm_group_dma #(.GROUPS(GROUPS),.S_PER_GROUP(S_PER_GROUP),.SLOTS(SLOTS)) dma(
  .clk(core_clk),.reset(reset),.channel_count(channel_count),.credit_limit(credit_limit),
  .desc_valid(desc_valid),.desc_write(desc_write),.complete_ready(complete_ready),.desc_ready(desc_ready),
  .desc_address_flat(da),.desc_local_flat(dl),.desc_words_flat(dw),.desc_tag_flat(dt),
  .complete_valid(complete_valid),.complete_status_flat(cs),.complete_tag_flat(ct),.completed_words_flat(cw),
  .busy(busy),.protocol_error(protocol_error),.live_count_flat(lc),
  .mem_valid(qvalid),.mem_ready(qready),.mem_data_flat(qdata),
  .response_valid(rvalid),.response_ready(rready),.response_data_flat(rdata),
  .s_req(req),.s_wr(wr),.s_take(take),.s_address_flat(sa),.s_data_flat(sd),
  .s_ready(ready),.s_valid(valid),.s_result_flat(sr),.grant_valid(grant_valid),.grant_s_flat(gs),.eligible_debug(eligible_debug));
 assign observed_request=req;assign observed_write=wr;assign observed_ready=ready;
 for(genvar ch=0;ch<CHANNELS;ch=ch+1)begin: cdc
  hbm_async_fifo #(.WIDTH(185),.LGDEPTH(LGDEPTH)) requests(
   .wclk(core_clk),.rclk(mem_clk),.reset(reset),.wvalid(qvalid[ch]),.wready(qready[ch]),.wdata(qdata[ch*185+:185]),
   .rvalid(mem_valid[ch]),.rready(mem_ready[ch]),.rdata(mem_data[ch]));
  hbm_async_fifo #(.WIDTH(146),.LGDEPTH(LGDEPTH)) responses(
   .wclk(mem_clk),.rclk(core_clk),.reset(reset),.wvalid(response_valid[ch]),.wready(response_ready[ch]),.wdata(response_data[ch]),
   .rvalid(rvalid[ch]),.rready(rready[ch]),.rdata(rdata[ch*146+:146]));
  assign grant_s[ch]=gs[ch*4+:4];
 end
 wire [NS-1:0] lr,dv,de,av,ar,ab,aw,bv,br,bb,bw,bh;
 wire [2:0] row[NS];wire [1:0] atile[NS],btile[NS];
 wire [127:0] adata[NS];wire [511:0] bdata[NS];wire ma_ready,mb_ready,unused_busy;
 assign load_ready=lr[select_s];assign done_valid=dv[select_s];assign done_error=de[select_s];
 for(genvar s=0;s<NS;s=s+1)begin: stores
  assign da[s*40+:40]=desc_address[s];assign dl[s*10+:10]=desc_local[s];
  assign dw[s*11+:11]=desc_words[s];assign dt[s*16+:16]=desc_tag[s];
  assign complete_status[s]=cs[s*2+:2];assign complete_tag[s]=ct[s*16+:16];
  assign completed_words[s]=cw[s*11+:11];assign live_count[s]=lc[s*4+:4];
  assign ready[s]=native_ready[s]&&!hold_s[s];
  assign s_accept[s]=req[s]&&ready[s];assign s_ack[s]=valid[s]&&take[s];
  assign observed_address[s]=sa[s*10+:10];assign observed_data[s]=sd[s*128+:128];
  assign ar[s]=(select_s==4'(s))&&ma_ready&&a_allow;
  assign br[s]=(select_s==4'(s))&&mb_ready&&b_allow;
  assign a_fire[s]=av[s]&&ar[s];assign b_fire[s]=bv[s]&&br[s];
  block_feed_s_macro storage(
   .clk(core_clk),.reset(reset),.req(req[s]&&!hold_s[s]),.wr(wr[s]),.addr(sa[s*10+:10]),.din(sd[s*128+:128]),
   .ready(native_ready[s]),.valid(valid[s]),.take(take[s]),.dout(sr[s*128+:128]),
   .load_valid(load_valid&&(select_s==4'(s))),.load_ready(lr[s]),
   .load_bank(1'b0),.load_rows(4'd8),.load_tiles(3'd4),.load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),
   .load_a_base(10'd0),.load_b_base(10'd64),.done_valid(dv[s]),.done_take(done_take&&(select_s==4'(s))),
   .done_error(de[s]),.busy(),.a_valid(av[s]),.a_ready(ar[s]),.a_bank(ab[s]),.a_row(row[s]),.a_tile(atile[s]),
   .a_wide(aw[s]),.a_data(adata[s]),.b_valid(bv[s]),.b_ready(br[s]),.b_bank(bb[s]),.b_tile(btile[s]),
   .b_wide(bw[s]),.b_half(bh[s]),.b_data(bdata[s]));
 end
 block_v2_m matrix(
  .clk(core_clk),.reset(reset),.a_valid(av[select_s]&&a_allow),.a_ready(ma_ready),.a_bank(ab[select_s]),
  .a_row(row[select_s]),.a_tile(atile[select_s]),.a_wide(aw[select_s]),.a_data(adata[select_s]),
  .b_valid(bv[select_s]&&b_allow),.b_ready(mb_ready),.b_bank(bb[select_s]),.b_tile(btile[select_s]),
  .b_wide(bw[select_s]),.b_half(bh[select_s]),.b_data(bdata[select_s]),
  .cmd_valid(cmd_valid),.cmd_ready(cmd_ready),.cmd_op(cmd_op),.cmd_index(cmd_index),.cmd_data(cmd_data),
  .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_data(rsp_data),.rsp_error(rsp_error),.rsp_saturated(rsp_saturated),.busy(unused_busy));
endmodule
