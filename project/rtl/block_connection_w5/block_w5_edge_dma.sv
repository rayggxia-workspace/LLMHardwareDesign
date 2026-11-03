// H2 bounded ordinary-S DMA. One real S16KiB and one request/ACK helper.
// Write input ready means destination native write ACK already consumed.
// A held input is captured once before ready; its source must retain the offer.
// word_valid is metadata only (1024 bits), not a private payload array.
`default_nettype none
module block_w5_edge_dma (
 input wire clk,reset,abort,
 input wire cmd_valid,output wire cmd_ready,input wire cmd_write,
 input wire [9:0] cmd_base,cmd_words,
 input wire in_valid,output wire in_ready,input wire [127:0] in_data,
 input wire [9:0] in_index,input wire in_last,
 output wire out_valid,input wire out_ready,output wire [127:0] out_data,
 output wire [9:0] out_index,output wire out_last,
 output wire done_valid,input wire done_ready,output wire done_error,
 output wire [9:0] done_words,output wire busy
);
 localparam [3:0] IDLE=0,W_CAPTURE=1,W_REQ=2,W_RSP=3,W_RETIRE=4,
                  R_CHECK=5,R_REQ=6,R_RSP=7,R_HOLD=8,DONE=9;
 reg [3:0] state;
 reg write_hold,error_hold,internal_reset;
 reg [9:0] base_hold,count_hold,index_hold,words_hold;
 reg [127:0] data_hold;
 reg [1023:0] word_valid;
 wire leaf_reset;
 wire permit_req=1'b1,permit_rsp=1'b1;
 wire [10:0] command_end,address_wide;
 wire descriptor_ok,input_meta_ok,source_bad;
 wire h_req_valid,h_req_ready,h_rsp_valid,h_rsp_ready,h_rsp_error;
 wire [127:0] h_rsp_data;
 wire s_req,s_we,s_ready,s_valid,s_take,helper_s_take;
 wire [9:0] s_addr;
 wire [127:0] s_din,s_dout;
 wire native_write_accept,native_write_ack;

 assign leaf_reset=reset||abort||internal_reset;
 assign command_end={1'b0,cmd_base}+{1'b0,cmd_words};
 assign descriptor_ok=cmd_words>=10'd1&&cmd_words<=10'd256&&command_end<=11'd1024;
 assign address_wide={1'b0,base_hold}+{1'b0,index_hold};
 assign input_meta_ok=in_index==index_hold&&in_last==({1'b0,index_hold}+11'd1=={1'b0,count_hold});
 // Under the input contract valid/payload/meta are held until retirement.
 assign source_bad=(state==W_REQ||state==W_RSP||state==W_RETIRE)&&
                   (!in_valid||in_data!=data_hold||!input_meta_ok);
 assign cmd_ready=!leaf_reset&&state==IDLE;
 assign in_ready=!leaf_reset&&state==W_RETIRE&&!source_bad;
 assign out_valid=!leaf_reset&&state==R_HOLD;
 assign out_data=data_hold;
 assign out_index=index_hold;
 assign out_last={1'b0,index_hold}+11'd1=={1'b0,count_hold};
 // Existing completion survives abort, including abort+done_ready on one edge.
 assign done_valid=!reset&&state==DONE;
 assign done_error=error_hold;
 assign done_words=words_hold;
 assign busy=!reset&&state!=IDLE;

 assign h_req_valid=!leaf_reset&&permit_req&&
                   ((state==W_REQ&&!source_bad)||state==R_REQ);
 assign h_rsp_ready=!leaf_reset&&(state==W_RSP||state==R_RSP);
 assign s_take=helper_s_take&&permit_rsp;
 assign native_write_accept=s_req&&s_ready&&s_we;
 assign native_write_ack=s_valid&&s_take&&s_we;

 block_p2_s_ctrl u_s_ctrl (
  .clk(clk),.resetn(!leaf_reset),
  .req_valid(h_req_valid),.req_ready(h_req_ready),.req_write(write_hold),
  .req_addr(address_wide[9:0]),.req_data(data_hold),
  .rsp_valid(h_rsp_valid),.rsp_ready(h_rsp_ready),.rsp_data(h_rsp_data),.rsp_error(h_rsp_error),
  .s_req(s_req),.s_we(s_we),.s_addr(s_addr),.s_din(s_din),.s_rsp_ready(helper_s_take),
  .s_ready(s_ready),.s_rsp_valid(s_valid&&permit_rsp),.s_dout(s_dout)
 );
 block_feed_s_macro u_s (
  .clk(clk),.reset(leaf_reset),.req(s_req),.wr(s_we),.addr(s_addr),.din(s_din),
  .ready(s_ready),.valid(s_valid),.take(s_take),.dout(s_dout),
  .load_valid(1'b0),.load_ready(),.load_bank(1'b0),.load_rows(4'd0),.load_tiles(3'd0),
  .load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),
  .load_a_base(10'd0),.load_b_base(10'd0),.done_valid(),.done_take(1'b0),.done_error(),.busy(),
  .a_valid(),.a_ready(1'b0),.a_bank(),.a_row(),.a_tile(),.a_wide(),.a_data(),
  .b_valid(),.b_ready(1'b0),.b_bank(),.b_tile(),.b_wide(),.b_half(),.b_data()
 );

 always @(posedge clk) begin
  if(reset) begin
   state<=IDLE;write_hold<=0;error_hold<=0;internal_reset<=0;
   base_hold<=0;count_hold<=0;index_hold<=0;words_hold<=0;data_hold<=0;word_valid<=0;
  end else begin
   internal_reset<=0;
   // A new unacknowledged overwrite invalidates its old version immediately.
   // Abort/reset of the S protocol cannot undo a real RAM write.
   if(native_write_accept) word_valid[s_addr]<=1'b0;
   if(native_write_ack) begin
    word_valid[s_addr]<=1'b1;
    words_hold<=words_hold+10'd1;
   end
   if(state==DONE) begin
    if(done_valid&&done_ready) state<=IDLE;
   end else if(abort&&state!=IDLE) begin
    state<=DONE;error_hold<=1'b1;
   end else if(source_bad) begin
    state<=DONE;error_hold<=1'b1;internal_reset<=1'b1;
   end else begin
    case(state)
     IDLE:if(cmd_valid&&cmd_ready) begin
      base_hold<=cmd_base;count_hold<=cmd_words;write_hold<=cmd_write;
      index_hold<=0;words_hold<=0;error_hold<=0;
      if(!descriptor_ok) begin state<=DONE;error_hold<=1'b1;end
      else if(cmd_write) state<=W_CAPTURE;
      else state<=R_CHECK;
     end
     W_CAPTURE:if(in_valid) begin
      if(!input_meta_ok) begin state<=DONE;error_hold<=1'b1;end
      else begin data_hold<=in_data;state<=W_REQ;end
     end
     W_REQ:if(h_req_valid&&h_req_ready) state<=W_RSP;
     W_RSP:if(h_rsp_valid&&h_rsp_ready) begin
      if(h_rsp_error) begin state<=DONE;error_hold<=1'b1;internal_reset<=1'b1;end
      else state<=W_RETIRE;
     end
     W_RETIRE:if(in_valid&&in_ready) begin
      if({1'b0,index_hold}+11'd1=={1'b0,count_hold}) state<=DONE;
      else begin index_hold<=index_hold+10'd1;state<=W_CAPTURE;end
     end
     R_CHECK:begin
      if(!word_valid[address_wide[9:0]]) begin state<=DONE;error_hold<=1'b1;end
      else state<=R_REQ;
     end
     R_REQ:if(h_req_valid&&h_req_ready) state<=R_RSP;
     R_RSP:if(h_rsp_valid&&h_rsp_ready) begin
      if(h_rsp_error) begin state<=DONE;error_hold<=1'b1;internal_reset<=1'b1;end
      else begin data_hold<=h_rsp_data;state<=R_HOLD;end
     end
     R_HOLD:if(out_valid&&out_ready) begin
      words_hold<=words_hold+10'd1;
      if({1'b0,index_hold}+11'd1=={1'b0,count_hold}) state<=DONE;
      else begin index_hold<=index_hold+10'd1;state<=R_CHECK;end
     end
     default:begin state<=DONE;error_hold<=1'b1;internal_reset<=1'b1;end
    endcase
   end
  end
 end
endmodule
`default_nettype wire
