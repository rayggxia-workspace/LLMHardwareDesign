// Stable S32 Q16.16 Softmax in one exclusive existing S128 window.
// One ordinary S owner, one word of compute input and one word of result.
module n_s32_softmax_s128 (
 input wire clk,reset,
 input wire cmd_valid,output wire cmd_ready,input wire [31:0] cmd_tag,
 input wire [9:0] cmd_base,input wire [12:0] cmd_count,input wire cmd_committed,
 input wire abort_valid,output wire abort_ready,input wire [31:0] abort_tag,
 output reg rsp_valid,input wire rsp_ready,output reg [31:0] rsp_tag,
 output reg rsp_error,rsp_aborted,output reg [11:0] rsp_writes,
 output wire s_req_valid,input wire s_req_ready,output wire s_req_write,
 output wire [9:0] s_req_address,output wire [127:0] s_req_data,
 input wire s_rsp_valid,output wire s_rsp_ready,input wire [127:0] s_rsp_data,input wire s_rsp_error
);
 `include "exp_q16_lut.svh"
 localparam [4:0] IDLE=0,READ_REQ=1,READ_ACK=2,WORD_MAX=3,
     DIFF=4,LOOKUP=5,INTERPOLATE=6,EXP_ROUND=7,WORD_SUM=8,
     DIV_START=9,DIV_WAIT=10,DIV_ROUND=11,SCALE=12,SCALE_ROUND=13,
     WRITE_REQ=14,WRITE_ACK=15,EXP_ROUND_HIGH=16,SCALE_ROUND_HIGH=17;
 localparam [1:0] FIND_MAX=0,WRITE_EXP=1,WRITE_PROBABILITY=2;
 reg [4:0] state;
 reg [1:0] pass_kind;
 reg [31:0] tag;
 reg cancelled;
 reg [9:0] base;
 reg [10:0] word_count,word_index;
 reg [2:0] tail_lanes;
 reg [11:0] write_count;
 reg [127:0] input_word,output_word;
 reg signed [31:0] maximum;
 reg [31:0] total;
 reg [32:0] factor;
 reg [32:0] div_quotient,div_remainder;
 reg signed [32:0] difference[0:1];
 reg [16:0] exp_lo[0:1],exp_delta[0:1],product_base[0:1];
 reg [8:0] exp_fraction[0:1];
 reg [25:0] exp_product[0:1];
 reg [49:0] norm_product[0:1];

 wire last_word=word_index+11'd1==word_count;
 wire [2:0] valid_lanes=last_word?tail_lanes:3'd4;
 wire [12:0] cmd_words=(cmd_count+13'd3)>>2;
 wire cmd_legal=cmd_committed&&cmd_count!=0&&cmd_count<=4096&&
      ({3'd0,cmd_base}+cmd_words<=13'd1024);
 assign cmd_ready=!reset&&state==IDLE&&!rsp_valid;
 assign abort_ready=!reset&&state!=IDLE&&!cancelled&&abort_tag==tag;
 wire stop=cancelled||(abort_valid&&abort_ready);
 assign s_req_valid=!reset&&(state==READ_REQ||state==WRITE_REQ);
 assign s_req_write=state==WRITE_REQ;
 assign s_req_address=base+word_index[9:0];
 assign s_req_data=s_req_write?output_word:128'd0;
 assign s_rsp_ready=!reset&&(state==READ_ACK||state==WRITE_ACK);

 wire div_ready,div_valid,div_error;
 wire [63:0] div_q,div_r;
 block_v2_n_group divider(clk,reset,state==DIV_START&&!stop,div_ready,1'b0,
     64'd1<<48,{32'd0,total},div_valid,state==DIV_WAIT,div_q,div_r,div_error);
 wire [33:0] doubled_remainder={div_remainder,1'b0};
 wire [33:0] div_denominator={2'b0,total};
 wire div_increment=doubled_remainder>div_denominator||
       (doubled_remainder==div_denominator&&div_quotient[0]);

 function automatic signed [31:0] larger(input signed [31:0] a,b);
  larger=a>b?a:b;
 endfunction
 wire signed [31:0] score[0:3];
 for(genvar lane=0;lane<4;lane=lane+1)begin: scores
  assign score[lane]=valid_lanes>3'(lane)?$signed(input_word[32*lane+:32]):32'sh80000000;
 end
 wire signed [31:0] packet_max=larger(larger(score[0],score[1]),larger(score[2],score[3]));
 wire [18:0] packet_sum={2'd0,output_word[16:0]}+{2'd0,output_word[48:32]}+
                       {2'd0,output_word[80:64]}+{2'd0,output_word[112:96]};

 wire [16:0] lut_low[0:1],lut_high[0:1],rounded_exp[0:1];
 wire [8:0] lut_fraction[0:1];
 wire [31:0] rounded_norm[0:1];
 wire signed [32:0] next_difference[0:1];
 wire [49:0] next_norm_product[0:1];
 for(genvar lane=0;lane<2;lane=lane+1)begin: arithmetic
  wire signed [31:0] next_score=state==DIFF?score[lane]:score[2+lane];
  assign next_difference[lane]=$signed({next_score[31],next_score})-$signed({maximum[31],maximum});
  wire [16:0] scale_operand=state==SCALE?input_word[32*lane+:17]:input_word[32*(2+lane)+:17];
  assign next_norm_product[lane]=scale_operand*factor;
  // The LUT is evaluated only over a representable offset. Exponents at
  // both closed-domain endpoints come from the exact constant values.
  wire [19:0] offset=20'(difference[lane]+33'sd1048576);
  wire interior=difference[lane]<0&&difference[lane]>-33'sd1048576;
  wire [11:0] index={1'b0,offset[19:9]};
  assign lut_low[lane]=interior?exp_lut(index):difference[lane]>=0?17'd65536:17'd0;
  assign lut_high[lane]=interior?exp_lut(index+12'd1):lut_low[lane];
  assign lut_fraction[lane]=interior?offset[8:0]:9'd0;
  wire exp_up=exp_product[lane][8:0]>9'd256||
        (exp_product[lane][8:0]==9'd256&&exp_product[lane][9]);
  assign rounded_exp[lane]=product_base[lane]+exp_product[lane][25:9]+{16'd0,exp_up};
  wire norm_up=norm_product[lane][31:0]>32'h80000000||
        (norm_product[lane][31:0]==32'h80000000&&norm_product[lane][32]);
  assign rounded_norm[lane]={14'd0,norm_product[lane][49:32]}+{31'd0,norm_up};
 end

 task automatic finish(input bit failed,input bit aborted,input [11:0] written);
  begin
   state<=IDLE;rsp_valid<=1;rsp_tag<=tag;rsp_error<=failed;rsp_aborted<=aborted;rsp_writes<=written;
  end
 endtask

 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;rsp_valid<=0;rsp_tag<=0;rsp_error<=0;rsp_aborted<=0;rsp_writes<=0;
   cancelled<=0;
  end else begin
   if(rsp_valid&&rsp_ready)rsp_valid<=0;
   if(abort_valid&&abort_ready)cancelled<=1;
   if(stop&&state!=IDLE&&state!=READ_REQ&&state!=READ_ACK&&
      state!=WRITE_REQ&&state!=WRITE_ACK&&state!=DIV_WAIT)finish(0,1,write_count);
   else case(state)
    IDLE:if(cmd_valid&&cmd_ready)begin
     if(!cmd_legal)begin rsp_valid<=1;rsp_tag<=cmd_tag;rsp_error<=1;rsp_aborted<=0;rsp_writes<=0;end
     else begin
      tag<=cmd_tag;cancelled<=0;base<=cmd_base;word_count<=cmd_words[10:0];word_index<=0;
      tail_lanes<=cmd_count[1:0]==0?3'd4:{1'b0,cmd_count[1:0]};write_count<=0;
      maximum<=32'sh80000000;total<=0;pass_kind<=FIND_MAX;state<=READ_REQ;
     end
    end
    READ_REQ:if(s_req_ready)state<=READ_ACK;
    READ_ACK:if(s_rsp_valid)begin
     if(s_rsp_error||stop)finish(s_rsp_error,stop,write_count);
     else begin
      input_word<=s_rsp_data;output_word<=0;
      state<=pass_kind==FIND_MAX?WORD_MAX:pass_kind==WRITE_EXP?DIFF:SCALE;
     end
    end
    WORD_MAX:begin
     maximum<=larger(maximum,packet_max);
     word_index<=last_word?11'd0:word_index+11'd1;
     if(last_word)pass_kind<=WRITE_EXP;
     state<=READ_REQ;
    end
    DIFF:begin
     for(integer i=0;i<2;i=i+1)begin
      difference[i]<=next_difference[i];
     end
     state<=LOOKUP;
    end
    LOOKUP:begin
     for(integer i=0;i<2;i=i+1)begin
      exp_lo[i]<=lut_low[i];exp_delta[i]<=lut_high[i]-lut_low[i];exp_fraction[i]<=lut_fraction[i];
      difference[i]<=next_difference[i];
     end
     state<=INTERPOLATE;
    end
    INTERPOLATE:begin
     // Interleave the two pairs through the same EXP lanes. The base
     // follows its own product to the rounding stage.
     for(integer i=0;i<2;i=i+1)begin
      exp_product[i]<=exp_delta[i]*exp_fraction[i];product_base[i]<=exp_lo[i];
      exp_lo[i]<=lut_low[i];exp_delta[i]<=lut_high[i]-lut_low[i];exp_fraction[i]<=lut_fraction[i];
     end
     state<=EXP_ROUND;
    end
    EXP_ROUND:begin
     for(integer i=0;i<2;i=i+1)begin
      if(int'(valid_lanes)>i)output_word[32*i+:32]<={15'd0,rounded_exp[i]};
      exp_product[i]<=exp_delta[i]*exp_fraction[i];product_base[i]<=exp_lo[i];
     end
     state<=valid_lanes<=2?WORD_SUM:EXP_ROUND_HIGH;
    end
    EXP_ROUND_HIGH:begin
     for(integer i=0;i<2;i=i+1)begin
      if(int'(valid_lanes)>2+i)output_word[32*(2+i)+:32]<={15'd0,rounded_exp[i]};
     end
     state<=WORD_SUM;
    end
    WORD_SUM:begin total<=total+{13'd0,packet_sum};state<=WRITE_REQ;end
    DIV_START:if(div_ready)state<=DIV_WAIT;
    DIV_WAIT:if(div_valid)begin
     if(div_error||(|div_q[63:33])||(|div_r[63:33])||stop)finish(div_error||(|div_q[63:33])||(|div_r[63:33]),stop,write_count);
     else begin div_quotient<=div_q[32:0];div_remainder<=div_r[32:0];state<=DIV_ROUND;end
    end
    DIV_ROUND:begin factor<=div_quotient+{32'd0,div_increment};pass_kind<=WRITE_PROBABILITY;state<=READ_REQ;end
    SCALE:begin
     for(integer i=0;i<2;i=i+1)norm_product[i]<=next_norm_product[i];
     state<=SCALE_ROUND;
    end
    SCALE_ROUND:begin
     for(integer i=0;i<2;i=i+1)begin
      if(int'(valid_lanes)>i)output_word[32*i+:32]<=rounded_norm[i];
      norm_product[i]<=next_norm_product[i];
     end
     state<=valid_lanes<=2?WRITE_REQ:SCALE_ROUND_HIGH;
    end
    SCALE_ROUND_HIGH:begin
     for(integer i=0;i<2;i=i+1)begin
      if(int'(valid_lanes)>2+i)output_word[32*(2+i)+:32]<=rounded_norm[i];
     end
     state<=WRITE_REQ;
    end
    WRITE_REQ:if(s_req_ready)state<=WRITE_ACK;
    WRITE_ACK:if(s_rsp_valid)begin
     if(!s_rsp_error)write_count<=write_count+12'd1;
     if(s_rsp_error||stop)finish(s_rsp_error,stop,write_count+{11'd0,!s_rsp_error});
     else if(last_word&&pass_kind==WRITE_PROBABILITY)finish(0,0,write_count+12'd1);
     else begin
      word_index<=last_word?11'd0:word_index+11'd1;
      state<=last_word?DIV_START:READ_REQ;
     end
    end
    default:state<=IDLE;
   endcase
  end
 end
endmodule
