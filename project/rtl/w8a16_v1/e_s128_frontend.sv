`timescale 1ns/1ps
// LC-owned E32 service over one ordinary S128 request/response port.
// One S request outstanding; S response and E result are held by their
// producers, so the adapter adds no operand or result payload buffer.
// Each narrow result retains one S128 word (four i16 lanes + zero padding).
// Exact in-place is legal; a shifted overlapping destination is not.
module e_s128_frontend #(parameter bit AP64=1'b0)(
 input wire clk,reset,
 input wire cmd_valid,output wire cmd_ready,
 input wire [3:0] cmd_op,cmd_tail_mask,
 input wire [7:0] cmd_shift,
 input wire [2:0] cmd_minus,
 input wire [9:0] cmd_a,cmd_b,cmd_c,cmd_out,
 input wire [5:0] cmd_words,
 output reg done_valid,input wire done_ready,
 output reg done_error,output reg [5:0] done_words,
 output reg [7:0] done_clipped_lanes,
 output wire s_req_valid,s_req_write,
 output wire [9:0] s_req_address,output wire [127:0] s_req_data,
 input wire s_req_ready,s_rsp_valid,
 output wire s_rsp_ready,input wire [127:0] s_rsp_data
);
 localparam [2:0] IDLE=0,READ_REQ=1,READ_RSP=2,RESULT=3,WRITE_ACK=4;
 reg [2:0] phase;
 reg [1:0] operand,last_operand;
 reg [3:0] op,tail_mask;
 reg [7:0] shift;
 reg [2:0] minus;
 reg [9:0] a,b,c,dst;
 reg [5:0] index_word,words;
 reg [2:0] pending_clips;
 wire e_in_ready,e_out_valid,e_out_ready,e_out_error;
 wire [127:0] e_out_data;
 wire [3:0] e_out_clipped;

 wire unary=cmd_op==4'd3||cmd_op==4'd4||cmd_op==4'd10||cmd_op==4'd11;
 wire ternary=cmd_op==4'd1||cmd_op==4'd9;
 wire [10:0] a_end={1'b0,cmd_a}+{5'b0,cmd_words};
 wire [10:0] b_end={1'b0,cmd_b}+{5'b0,cmd_words};
 wire [10:0] c_end={1'b0,cmd_c}+{5'b0,cmd_words};
 wire [10:0] d_end={1'b0,cmd_out}+{5'b0,cmd_words};
 function automatic safe_window(input [9:0] src,dest,input [10:0] src_end,dest_end);
   safe_window=src_end<=11'd1024 &&
    (src==dest||src_end<={1'b0,dest}||dest_end<={1'b0,src});
 endfunction
 wire valid_op=cmd_op<=4'd11 &&
  $signed(cmd_shift)>=-8'sd63 && $signed(cmd_shift)<=8'sd63 &&
  ((cmd_op>=4'd2&&cmd_op<=4'd4)||cmd_shift==0) &&
  ((cmd_op==4'd0||cmd_op==4'd1)||cmd_minus==0) && (cmd_op!=4'd0||!cmd_minus[2]);
 wire valid_cmd=valid_op && cmd_words!=0 && cmd_words<=6'd32 && d_end<=11'd1024 &&
  safe_window(cmd_a,cmd_out,a_end,d_end) &&
  (unary||safe_window(cmd_b,cmd_out,b_end,d_end)) &&
  (!ternary||safe_window(cmd_c,cmd_out,c_end,d_end));

 wire last_word=index_word+6'd1==words;
 assign cmd_ready=!reset && phase==IDLE && !done_valid;
 assign s_req_write=!reset && phase==RESULT && e_out_valid && !e_out_error;
 assign s_req_valid=!reset && (phase==READ_REQ || s_req_write);
 assign s_req_address=(s_req_write?dst:operand==0?a:operand==1?b:c)+{4'b0,index_word};
 assign s_req_data=s_req_write?e_out_data:128'd0;
 assign s_rsp_ready=!reset && (phase==WRITE_ACK || (phase==READ_RSP && e_in_ready));
 assign e_out_ready=!reset && phase==RESULT && (e_out_error || s_req_ready);
 if(!AP64)begin: wide_leaf
 e_s32_native arithmetic(.clk,.reset,.in_valid(phase==READ_RSP && s_rsp_valid),.in_ready(e_in_ready),
  .in_op(op),.in_mask(last_word?tail_mask:4'hf),.in_shift(shift),.in_minus(minus),.in_data(s_rsp_data),
  .out_valid(e_out_valid),.out_ready(e_out_ready),.out_data(e_out_data),
  .out_clipped(e_out_clipped),.out_error(e_out_error));
 end else begin: narrow_leaf
   reg send_upper,recv_upper;
   reg [63:0] low_result;
   wire aperture_ready,aperture_valid;
   wire aperture_in_valid=phase==READ_RSP&&s_rsp_valid;
   wire aperture_out_ready=phase==RESULT&&(!recv_upper||e_out_ready);
   wire [63:0] aperture_result;
   assign e_in_ready=send_upper&&aperture_ready;
   assign e_out_valid=recv_upper&&aperture_valid;
   assign e_out_data={aperture_result,low_result};
   e_s32_ap64 arithmetic(.clk,.reset,.in_valid(aperture_in_valid),.in_ready(aperture_ready),
    .in_data(send_upper ? s_rsp_data[127:64] : s_rsp_data[63:0]),
    .in_op(op),.in_mask(last_word ? tail_mask : 4'hf),.in_shift(shift),.in_minus(minus),
    .out_valid(aperture_valid),.out_ready(aperture_out_ready),.out_data(aperture_result),
    .out_clipped(e_out_clipped),.out_error(e_out_error));
   always @(posedge clk)begin
    if(reset)begin send_upper<=0;recv_upper<=0;low_result<=0;end
    else begin
     if(aperture_in_valid&&aperture_ready)send_upper<=!send_upper;
     if(aperture_valid&&aperture_out_ready)begin
      recv_upper<=!recv_upper;
      if(!recv_upper)low_result<=aperture_result;
     end
    end
   end
 end

 always @(posedge clk)begin
   if(reset)begin
     phase<=IDLE;done_valid<=0;done_error<=0;done_words<=0;done_clipped_lanes<=0;
     operand<=0;last_operand<=0;op<=0;tail_mask<=0;shift<=0;minus<=0;
     a<=0;b<=0;c<=0;dst<=0;index_word<=0;words<=0;pending_clips<=0;
   end else begin
     if(done_valid&&done_ready)done_valid<=0;
     case(phase)
       IDLE:if(cmd_valid&&cmd_ready)begin
         done_error<=!valid_cmd;done_words<=0;done_clipped_lanes<=0;
         if(!valid_cmd)done_valid<=1;
         else begin
           phase<=READ_REQ;operand<=0;last_operand<=unary?2'd0:ternary?2'd2:2'd1;
           op<=cmd_op;tail_mask<=cmd_tail_mask;shift<=cmd_shift;minus<=cmd_minus;
           a<=cmd_a;b<=cmd_b;c<=cmd_c;dst<=cmd_out;index_word<=0;words<=cmd_words;
         end
       end
       READ_REQ:if(s_req_valid&&s_req_ready)phase<=READ_RSP;
       READ_RSP:if(s_rsp_valid&&s_rsp_ready)begin
         if(operand==last_operand)phase<=RESULT;
         else begin operand<=operand+2'd1;phase<=READ_REQ;end
       end
       RESULT:if(e_out_valid&&e_out_ready)begin
         if(e_out_error)begin phase<=IDLE;done_valid<=1;done_error<=1;end
         else begin
           phase<=WRITE_ACK;
           pending_clips<={2'd0,e_out_clipped[0]}+{2'd0,e_out_clipped[1]}+
                          {2'd0,e_out_clipped[2]}+{2'd0,e_out_clipped[3]};
         end
       end
       WRITE_ACK:if(s_rsp_valid&&s_rsp_ready)begin
         done_words<=done_words+6'd1;
         done_clipped_lanes<=done_clipped_lanes+{5'd0,pending_clips};
         if(last_word)begin phase<=IDLE;done_valid<=1;end
         else begin index_word<=index_word+6'd1;operand<=0;phase<=READ_REQ;end
       end
       default:phase<=IDLE;
     endcase
   end
 end
endmodule
