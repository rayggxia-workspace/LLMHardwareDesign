// Shared transport construction, specialized once for N/E/G at elaboration.
// No arithmetic multiplier and no full-vector buffer. Three 128-bit operand
// holds and one result hold are explicit; long N contexts stay in native N.
module control_vector_adapter #(
 parameter integer KIND=3,
 parameter integer DATA_WIDTH=KIND==4?32:128
)(
 input wire clk,reset,input wire task_valid,output wire task_ready,input wire [255:0] task_data,
 output reg complete_valid,input wire complete_ready,output reg [63:0] complete_data,
 output reg s_req,output reg s_wr,output reg [9:0] s_addr,output reg [127:0] s_din,
 input wire s_ready,input wire s_valid,output wire s_take,input wire [127:0] s_dout,
 output reg core_valid,input wire core_ready,output reg [3:0] core_op,output reg [3:0] core_count,
 output reg [31:0] core_param,output reg [DATA_WIDTH-1:0] core_a,core_b,core_c,
 input wire core_rsp_valid,output wire core_rsp_ready,input wire [DATA_WIDTH-1:0] core_rsp_data,
 input wire core_error,core_saturated
);
 localparam IDLE=0,READ_A=1,READ_B=2,READ_C=3,READ_WAIT=4,ISSUE=5,REPLY=6,STORE=7,ADVANCE=8,WRITE_WAIT=9;
 reg [3:0] state,after_read;
 reg [15:0] tag,total,position;
 reg [3:0] op,packet_count;reg [1:0] subword;
 reg use_b,use_c,write_result,control_only;
 reg [31:0] b_ref,c_ref,param,epsilon;
 reg [9:0] a_base,d_base;
 reg [127:0] a_hold,b_hold,c_hold,result_hold;
 reg [9:0] packet_index;
 reg saturated,failed;
 wire [7:0] requested_op=task_data[7:0];
 wire requested_control=KIND==2 && requested_op!=1 && requested_op!=3 && requested_op!=5 && requested_op!=6 && requested_op!=9;
 wire requested_four=(KIND==3 && requested_op==13)||(KIND==2 && requested_op==9);
 wire [31:0] words_needed=requested_control?32'd1:((task_data[63:32]+(requested_four?32'd3:32'd7))>>(requested_four?2:3));
 wire [31:0] footprint=words_needed<<4;
 function automatic bad_ref;
  input [31:0] ref_value,bytes;input allow_constant;
  begin
   if(allow_constant && ref_value[31:30]==1) bad_ref=ref_value[29:16]!=0;
   else bad_ref=ref_value[31:14]!=0 || ref_value[3:0]!=0 || ref_value+bytes>16384;
  end
 endfunction
 function automatic overlap;
  input [31:0] src,dst,bytes;
  begin overlap=src[31:30]==0 && src!=dst && src<dst+bytes && dst<src+bytes;end
 endfunction
 wire invalid=task_data[11:8]!=4'(KIND) || task_data[15] || task_data[63:48]!=0 ||
  (KIND==2?requested_op>11:KIND==3?requested_op>13:requested_op>3) ||
  (requested_control && task_data[63:32]!=0) ||
  (!requested_control && (task_data[63:32]==0 || bad_ref(task_data[95:64],footprint,0))) ||
  (task_data[12] && bad_ref(task_data[127:96],footprint,1)) ||
  (task_data[13] && (KIND!=3 || bad_ref(task_data[159:128],footprint,1))) ||
  (task_data[14] && (bad_ref(task_data[191:160],footprint,0) ||
    (!requested_control && overlap(task_data[95:64],task_data[191:160],footprint)) ||
    (task_data[12] && overlap(task_data[127:96],task_data[191:160],footprint)) ||
    (task_data[13] && overlap(task_data[159:128],task_data[191:160],footprint))));
 wire four=(KIND==3 && op==13)||(KIND==2 && op==9);
 wire [15:0] remaining=total-position;
 wire [3:0] lanes=four?4'd4:4'd8;
 wire [3:0] this_count=remaining>{12'b0,lanes}?lanes:remaining[3:0];
 wire [3:0] g_count=(packet_count>{1'b0,subword,1'b0}+4'd1)?4'd2:4'd1;
 assign task_ready=state==IDLE && !complete_valid;
 assign s_take=state==READ_WAIT || state==WRITE_WAIT;
 assign core_rsp_ready=state==REPLY;
 task respond;
  input [3:0] status;
  begin complete_valid<=1;complete_data<={16'b0,total,7'b0,saturated,status,4'(KIND),tag};state<=IDLE;end
 endtask
 reg [127:0] masked_result,masked_a,masked_b,masked_c;
 always @* begin
  masked_result=128'(core_rsp_data);
  masked_a=a_hold;masked_b=b_hold;masked_c=c_hold;
  for(integer lane=0;lane<8;lane=lane+1) if(lane>=32'(packet_count)) begin
   masked_a[lane*16+:16]=0;masked_b[lane*16+:16]=0;masked_c[lane*16+:16]=0;
  end
  if(four) begin
   masked_a=a_hold;masked_b=b_hold;masked_c=c_hold;
   for(integer lane=0;lane<4;lane=lane+1) if(lane>=32'(packet_count)) begin
    masked_a[lane*32+:32]=0;masked_b[lane*32+:32]=0;masked_c[lane*32+:32]=0;
   end
  end
  if(KIND!=4 && !control_only) begin
   for(integer lane=0;lane<8;lane=lane+1) if(lane>=32'(packet_count)) masked_result[lane*16+:16]=0;
  end
  if(KIND==3 && op==12) for(integer byte_index=0;byte_index<16;byte_index=byte_index+1)
   if(byte_index>=32'(packet_count)) masked_result[byte_index*8+:8]=0;
 end
 always @(posedge clk) begin
  if(reset) begin
   state<=IDLE;after_read<=0;tag<=0;total<=0;position<=0;op<=0;packet_count<=0;subword<=0;
   use_b<=0;use_c<=0;write_result<=0;control_only<=0;b_ref<=0;c_ref<=0;param<=0;epsilon<=0;
   a_base<=0;d_base<=0;a_hold<=0;b_hold<=0;c_hold<=0;result_hold<=0;packet_index<=0;saturated<=0;failed<=0;
   complete_valid<=0;complete_data<=0;s_req<=0;s_wr<=0;s_addr<=0;s_din<=0;
   core_valid<=0;core_op<=0;core_count<=0;core_param<=0;core_a<=0;core_b<=0;core_c<=0;
  end else begin
   if(complete_valid && complete_ready) complete_valid<=0;
   case(state)
    IDLE:if(task_valid && task_ready) begin
     tag<=task_data[31:16];total<=task_data[47:32];position<=0;packet_index<=0;op<=requested_op[3:0];
     use_b<=task_data[12];use_c<=task_data[13];write_result<=task_data[14];control_only<=requested_control;
     b_ref<=task_data[127:96];c_ref<=task_data[159:128];param<=task_data[223:192];epsilon<=task_data[255:224];
     a_base<=task_data[77:68];d_base<=task_data[173:164];saturated<=0;failed<=0;
     a_hold<=0;b_hold<=0;c_hold<=0;result_hold<=0;subword<=0;
     if(invalid) begin complete_valid<=1;complete_data<={32'b0,8'b0,4'd2,4'(KIND),task_data[31:16]};end
     else if(requested_control) begin packet_count<=0;state<=ISSUE;end
     else state<=READ_A;
    end
    READ_A:if(!s_req) begin
     s_req<=1;s_wr<=0;s_addr<=a_base+packet_index[9:0];packet_count<=this_count;after_read<=READ_B;
    end else if(s_ready) begin s_req<=0;state<=READ_WAIT;end
    READ_B:if(!use_b) begin b_hold<=0;state<=READ_C;end
     else if(b_ref[31:30]==1) begin b_hold<={8{b_ref[15:0]}};state<=READ_C;end
     else if(!s_req) begin s_req<=1;s_wr<=0;s_addr<=b_ref[13:4]+packet_index[9:0];after_read<=READ_C;end
     else if(s_ready) begin s_req<=0;state<=READ_WAIT;end
    READ_C:if(!use_c) begin c_hold<=0;state<=ISSUE;end
     else if(c_ref[31:30]==1) begin c_hold<={8{c_ref[15:0]}};state<=ISSUE;end
     else if(!s_req) begin s_req<=1;s_wr<=0;s_addr<=c_ref[13:4]+packet_index[9:0];after_read<=ISSUE;end
     else if(s_ready) begin s_req<=0;state<=READ_WAIT;end
    READ_WAIT:if(s_valid) begin
     if(after_read==READ_B) a_hold<=s_dout;else if(after_read==READ_C) b_hold<=s_dout;else c_hold<=s_dout;
     state<=after_read;
    end
    ISSUE:if(!core_valid) begin
     core_valid<=1;core_op<=op;core_count<=KIND==4?g_count:packet_count;core_param<=param;
     core_a<=control_only?(op==0?DATA_WIDTH'({96'b0,epsilon}):DATA_WIDTH'(0)):DATA_WIDTH'(masked_a>>(KIND==4?subword*32:0));
     core_b<=DATA_WIDTH'(masked_b>>(KIND==4?subword*32:0));core_c<=DATA_WIDTH'(masked_c);
    end else if(core_ready) begin core_valid<=0;state<=REPLY;end
    REPLY:if(core_rsp_valid) begin
     saturated<=saturated||core_saturated;
     if(core_error) begin failed<=1;state<=ADVANCE;end
     else if(KIND==4) begin
      result_hold[subword*32+:32]<=core_rsp_data[31:0];
      if(subword*2+2>=32'(packet_count)) begin
       if(packet_count[0]) result_hold[subword*32+16+:16]<=0;
       subword<=0;state<=write_result?STORE:ADVANCE;
      end else begin subword<=subword+1;state<=ISSUE;end
     end else begin result_hold<=masked_result;state<=write_result?STORE:ADVANCE;end
    end
    STORE:if(!s_req) begin s_req<=1;s_wr<=1;s_addr<=d_base+packet_index[9:0];s_din<=result_hold;end
     else if(s_ready) begin s_req<=0;state<=WRITE_WAIT;end
    WRITE_WAIT:if(s_valid) state<=ADVANCE;
    ADVANCE:if(failed) respond(4);
     else if(control_only || position+{12'b0,packet_count}==total) respond(0);
     else begin position<=position+{12'b0,packet_count};packet_index<=packet_index+1;result_hold<=0;state<=READ_A;end
    default:begin failed<=1;respond(3);end
   endcase
  end
 end
endmodule
