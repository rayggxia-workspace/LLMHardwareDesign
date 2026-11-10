// One MC response aperture and one ordinary local S128 port.
// The existing MC landing slot keeps the entire 64 B payload valid until
// raw_ready. This adapter owns two descriptors and NO payload register/FIFO.
// Accepted descriptor -> exactly one raw response even if canceled, or a
// matching explicit fabric-reject event before any raw offer. Admit must be
// true before the issuer can submit the corresponding DMA.
module dot_s32_stage64(
 input wire clk,reset,
 input wire cmd_valid,output wire cmd_ready,output wire cmd_admit,
 input wire [31:0] cmd_tag,
 input wire [9:0] cmd_dst,
 input wire [1:0] cmd_first,
 input wire [2:0] cmd_words,
 input wire cancel_valid,output wire cancel_ready,input wire [31:0] cancel_tag,
 input wire reject_valid,output wire reject_ready,input wire [31:0] reject_tag,
 input wire raw_valid,output wire raw_ready,input wire [31:0] raw_tag,
 input wire [511:0] raw_data,output wire unexpected_return,
 output wire s_req_valid,input wire s_req_ready,output wire [9:0] s_req_address,
 output wire [127:0] s_req_wdata,
 input wire s_rsp_valid,output wire s_rsp_ready,input wire s_rsp_error,
 output wire done_valid,input wire done_ready,
 output wire [31:0] done_tag,output wire done_cancelled,done_error,
 output wire [3:0] done_written_mask
);
 localparam [1:0] FREE=0, WAIT_RAW=1, ACTIVE=2, DONE=3;
 reg [1:0] state[0:1];
 reg [31:0] tag[0:1];
 reg [9:0] base[0:1];
 reg [1:0] first[0:1];
 reg [2:0] words[0:1];
 reg cancelled[0:1],failed[0:1],owns_window[0:1];
 reg [3:0] written[0:1];
 reg active,which,offer_held;
 reg [2:0] issued,acked;
 reg done_locked,done_which;

 wire slot = state[0]!=FREE;
 wire duplicate = (state[0]!=FREE&&cmd_tag==tag[0]) || (state[1]!=FREE&&cmd_tag==tag[1]);
 wire [10:0] cmd_end={1'b0,cmd_dst}+{8'd0,cmd_words};
 wire [10:0] end0={1'b0,base[0]}+{8'd0,words[0]};
 wire [10:0] end1={1'b0,base[1]}+{8'd0,words[1]};
 wire overlap0=state[0]!=FREE&&owns_window[0]&&{1'b0,cmd_dst}<end0&&{1'b0,base[0]}<cmd_end;
 wire overlap1=state[1]!=FREE&&owns_window[1]&&{1'b0,cmd_dst}<end1&&{1'b0,base[1]}<cmd_end;
 wire legal=cmd_words!=0&&{2'b0,cmd_first}+{1'b0,cmd_words}<=4&&cmd_end<=1024&&!overlap0&&!overlap1;
 assign cmd_ready=!reset&&(state[0]==FREE||state[1]==FREE)&&!duplicate;
 assign cmd_admit=cmd_valid&&cmd_ready&&legal;

 wire cancel0=(state[0]==WAIT_RAW||state[0]==ACTIVE)&&tag[0]==cancel_tag&&!cancelled[0]&&!failed[0];
 wire cancel1=(state[1]==WAIT_RAW||state[1]==ACTIVE)&&tag[1]==cancel_tag&&!cancelled[1]&&!failed[1];
 wire match0=state[0]==WAIT_RAW&&tag[0]==raw_tag;
 wire match1=state[1]==WAIT_RAW&&tag[1]==raw_tag;
 wire reject0=state[0]==WAIT_RAW&&tag[0]==reject_tag&&!(raw_valid&&match0);
 wire reject1=state[1]==WAIT_RAW&&tag[1]==reject_tag&&!(raw_valid&&match1);
 wire matching_active=active&&tag[which]==raw_tag;
 wire stopped=cancelled[which]||failed[which];
 wire exhausted=issued==words[which];
 wire outstanding=issued!=acked;
 wire [2:0] pending=issued-acked;
 assign cancel_ready=!reset&&(cancel0||cancel1)&&!(matching_active&&raw_ready&&cancel_tag==raw_tag);
 assign reject_ready=!reset&&(reject0||reject1);
 assign unexpected_return=!reset&&raw_valid&&!(matching_active||match0||match1);

 assign s_rsp_ready=!reset&&active&&outstanding;
 wire ack=s_rsp_valid&&s_rsp_ready;
 assign s_req_valid=!reset&&matching_active&&raw_valid&&!exhausted&&
   (!stopped||offer_held)&&(pending<2||ack);
 wire request=s_req_valid&&s_req_ready;
 assign s_req_address=base[which]+{7'd0,issued};
 wire [1:0] source_word=first[which]+issued[1:0];
 assign s_req_wdata=raw_data[source_word*128+:128];
 assign raw_ready=!reset&&matching_active&&!outstanding&&!offer_held&&(stopped||exhausted);
 wire retire = raw_valid&&raw_ready;

 wire report=done_locked ? done_which : state[0]!=DONE;
 assign done_valid=!reset&&(state[0]==DONE||state[1]==DONE);
 assign done_tag=tag[report];
 assign done_cancelled=cancelled[report];
 assign done_error=failed[report];
 assign done_written_mask=written[report];

 always @(posedge clk)begin
  if(reset)begin
   active<=0;which<=0;offer_held<=0;issued<=0;acked<=0;done_locked<=0;done_which<=0;
   for(integer i=0;i<2;i=i+1)begin
    state[i]<=FREE;tag[i]<=0;base[i]<=0;first[i]<=0;words[i]<=0;
    cancelled[i]<=0;failed[i]<=0;owns_window[i]<=0;written[i]<=0;
   end
  end else begin
   if(cmd_valid&&cmd_ready)begin
    state[slot]<=legal ? WAIT_RAW : DONE;tag[slot]<=cmd_tag;
    base[slot]<=cmd_dst;first[slot]<=cmd_first;words[slot]<=cmd_words;
    cancelled[slot]<=0;failed[slot]<=!legal;owns_window[slot]<=legal;written[slot]<=0;
   end
   if(cancel_valid&&cancel_ready)begin
    if(cancel0)cancelled[0]<=1;
    if(cancel1)cancelled[1]<=1;
   end
   if(reject_valid&&reject_ready)begin
    state[reject1]<=DONE;failed[reject1]<=1;
   end
   if(!active&&raw_valid&&(match0||match1))begin
    active<=1;which<=match1;state[match1]<=ACTIVE;
    issued<=0;acked<=0;offer_held<=0;
   end
   if(active)begin
    offer_held<=s_req_valid&&!s_req_ready;
    if(request)issued<=issued+1'b1;
    if(ack)begin
     acked<=acked+1'b1;
     if(s_rsp_error)failed[which]<=1;
     else written[which][acked[1:0]]<=1;
    end
    if(retire)begin
     active<=0;state[which]<=DONE;
    end
   end
   if(done_valid)begin
    if(done_ready)begin state[report]<=FREE;done_locked<=0;end
    else begin done_locked<=1;done_which<=report;end
   end
  end
 end
endmodule
