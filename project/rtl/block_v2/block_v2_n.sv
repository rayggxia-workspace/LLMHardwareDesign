// Stateful operations retain two lanes; stateless op12 optionally uses four EXP lanes.
// No calls to E/G; local square, EXP, divide/root and scaling resources.
module block_v2_n #(parameter integer NEXP_DIRECT=0, NEXP_DIRECT_LANES=2) (
 input wire clk,reset,cmd_valid,output wire cmd_ready,
 input wire [3:0] cmd_op,cmd_count,input wire [31:0] cmd_param,
 input wire [127:0] cmd_data,cmd_aux,
 output reg rsp_valid,input wire rsp_ready,output reg [127:0] rsp_data,
 output reg rsp_error,rsp_saturated,output wire busy
);
 `include "block_v2_n_exp.svh"
 localparam IDLE=0,CALC=1,ACCUM=2,MEAN_START=3,MEAN_WAIT=4,
 ROOT_START=5,ROOT_WAIT=6,FACTOR_START=7,FACTOR_WAIT=8,
 NORM_MUL=9,NORM_GATE=10,EMIT=11,TOP_SCAN=12,TOP_SAVE=13;
 reg [3:0] phase,operation,n;
 reg [3:0] position;
 reg [127:0] data,aux,result;
 reg [1:0] mode;
 reg context_valid,statistics_final,factor_valid;
 reg [31:0] epsilon,factor,exp_sum;
 reg [15:0] count,exp_count,replayed;
 reg signed [31:0] sum;
 reg [47:0] sumsq;
 reg signed [15:0] maximum,minimum;
 reg signed [15:0] raw[0:1],gamma[0:1];
 wire signed [16:0] norm_operand[0:1];
 for(genvar l=0;l<2;l=l+1)begin: norm_sign
  assign norm_operand[l]=operation==6?$signed({1'b0,raw[l]}):$signed({raw[l][15],raw[l]});
 end
 reg [1:0] enabled;
 reg [31:0] square[0:1];reg [15:0] ex[0:1];
 // Only op12 may select a four-element step. Legacy pair arithmetic is intact.
 localparam integer DIRECT_LANES=NEXP_DIRECT!=0?NEXP_DIRECT_LANES:2;
 wire [3:0] accum_step=operation==12&&DIRECT_LANES==4?4'd4:4'd2;
 wire [15:0] direct_extra_exp[0:1];wire [1:0] direct_extra_enabled;
 reg signed [47:0] norm_product[0:1];
 reg signed [63:0] gate_product[0:1];
 wire signed [63:0] normalized_gate[0:1];
 for(genvar k=0;k<2;k=k+1)begin: gamma_multiplier
  assign normalized_gate[k]=norm_product[k]*gamma[k];
 end
 reg saturated;
 reg [63:0] group_n,group_d;
 wire group_valid,group_ready,group_error;
 wire [63:0] group_q,group_r;
 wire start_group=phase==MEAN_START||phase==ROOT_START||phase==FACTOR_START;
 wire take_group=phase==MEAN_WAIT||phase==ROOT_WAIT||phase==FACTOR_WAIT;
 block_v2_n_group group_unit(clk,reset,start_group,group_ready,phase==ROOT_START,
  group_n,group_d,group_valid,take_group,group_q,group_r,group_error);

 reg [15:0] top_id[0:39];reg signed [15:0] top_score[0:39];
 reg [39:0] selected;
 reg [5:0] top_count,scan_index,best_index;
 reg [3:0] top_k,top_round;
 reg top_loading,best_valid;
 reg signed [15:0] best_value;reg [15:0] best_id;
 reg [127:0] chosen;

 assign cmd_ready=!reset&&phase==IDLE&&(!rsp_valid||rsp_ready);
 assign busy=!cmd_ready;

 function automatic [15:0] exponential;
  input signed [16:0] difference;
  reg [16:0] offset;reg [10:0] index;
  reg [15:0] lo,hi;reg [20:0] interpolation;
  begin
   if(difference< -16384)exponential=0;
   else if(difference>=0)exponential=32768;
   else begin
    offset=$unsigned(difference+17'sd16384);index=11'(offset>>4);
    lo=exp_lut(index);hi=exp_lut(index+1'b1);
    interpolation={5'd0,hi-lo}*{17'd0,offset[3:0]};
    exponential=lo+16'(interpolation>>4)+{15'd0,(interpolation[3:0]>8)||((interpolation[3:0]==8)&&interpolation[4])};
   end
  end
 endfunction
 function automatic signed [63:0] rne30;
  input signed [63:0] value;
  begin rne30=(value>>>30)+$signed({63'd0,(value[29:0]>30'h20000000)||((value[29:0]==30'h20000000)&&value[30])});end
 endfunction

 // Extra arithmetic exists only in the selected direct configuration. It
 // neither reads nor writes any statistics, factor, replay or top state.
 generate if(DIRECT_LANES==4)begin: direct_exp4
  reg [15:0] extra_exp[0:1];reg [1:0] extra_enabled;
  wire signed [15:0] extra_fetch[0:1];
  for(genvar lane=0;lane<2;lane=lane+1)begin: extra_lane
   assign extra_fetch[lane]=operation==12?$signed(16'(data>>(16*(position+4'd2+4'(lane))))):16'sd0;
   assign direct_extra_exp[lane]=extra_exp[lane];
  end
  assign direct_extra_enabled=extra_enabled;
  always @(posedge clk)begin
   if(reset)begin extra_exp[0]<=0;extra_exp[1]<=0;extra_enabled<=0;end
   else if(phase==CALC&&operation==12)begin
    for(integer lane=0;lane<2;lane=lane+1)begin
     extra_enabled[lane]<=position+4'd2+4'(lane)<n;
     extra_exp[lane]<=exponential($signed({extra_fetch[lane][15],extra_fetch[lane]}));
    end
   end
  end
 end else begin: direct_exp2
  assign direct_extra_exp[0]=16'd0;assign direct_extra_exp[1]=16'd0;
  assign direct_extra_enabled=2'd0;
 end endgenerate

 reg command_ok;
 reg signed [31:0] pair_sum;
 reg [32:0] pair_square;reg [16:0] pair_exp;
 reg signed [15:0] pair_max,pair_min;
 reg signed [63:0] rounded[0:1];
 reg [31:0] formatted;reg pair_saturated;
 reg signed [15:0] fetch[0:1];
 always @* begin
  command_ok=1;
  if(cmd_op==0)command_ok=cmd_param<=2&&(cmd_param[1:0]==0||cmd_data[31:0]!=0);
  else if(cmd_op==1)command_ok=context_valid&&!statistics_final&&cmd_count>0&&cmd_count<=8&&({1'b0,count}+{13'd0,cmd_count}<=17'd65535);
  else if(cmd_op==2)command_ok=context_valid&&!statistics_final&&count!=0;
  else if(cmd_op==3)command_ok=context_valid&&mode==0&&statistics_final&&!factor_valid&&cmd_count>0&&cmd_count<=8&&({1'b0,exp_count}+{13'd0,cmd_count}<={1'b0,count});
  else if(cmd_op==4)command_ok=context_valid&&mode==0&&statistics_final&&!factor_valid&&exp_count==count&&exp_sum!=0;
  else if(cmd_op==5||cmd_op==6)begin
   command_ok=context_valid&&factor_valid&&cmd_count>0&&cmd_count<=8&&({1'b0,replayed}+{13'd0,cmd_count}<={1'b0,count})&&((cmd_op==5&&mode!=0)||(cmd_op==6&&mode==0));
   if(cmd_op==6)for(integer i=0;i<8;i=i+1)if(i<cmd_count&&cmd_data[16*i+:16]>32768)command_ok=0;
  end
  else if(cmd_op==7)command_ok=context_valid;
  else if(cmd_op==8)command_ok=cmd_param>=1&&cmd_param<=8;
  else if(cmd_op==9)command_ok=top_loading&&cmd_count>0&&cmd_count<=4&&({1'b0,top_count}+{3'd0,cmd_count}<=40);
  else if(cmd_op==10)command_ok=top_loading&&top_count>0&&{2'd0,top_k}<=top_count;
  else if(cmd_op==11)command_ok=factor_valid;
  // Optional stateless relative EXP. No context is required or modified.
  // Used operands are signed S16; unused complete lanes and aux must be zero.
  else if(cmd_op==12)begin
   command_ok=NEXP_DIRECT!=0&&cmd_param==0&&cmd_aux==0&&cmd_count>0&&cmd_count<=8;
   for(integer i=0;i<8;i=i+1)
    if(i>=cmd_count&&cmd_data[16*i+:16]!=0)command_ok=0;
  end
  else command_ok=0;
  pair_sum=0;pair_square=0;pair_exp=0;pair_max=raw[0];pair_min=raw[0];
  for(integer l=0;l<2;l=l+1)begin
   fetch[l]=$signed(16'(data>>(16*(position+4'(l)))));
   if(enabled[l])begin
    pair_sum=pair_sum+$signed({{16{raw[l][15]}},raw[l]});
    pair_square=pair_square+{1'd0,square[l]};pair_exp=pair_exp+{1'd0,ex[l]};
    if(raw[l]>pair_max)pair_max=raw[l];if(raw[l]<pair_min)pair_min=raw[l];
   end
   rounded[l]=rne30(gate_product[l]);
  end
  formatted=0;pair_saturated=0;
  for(integer l=0;l<2;l=l+1)begin
   if(!enabled[l])formatted[16*l+:16]=0;
   else if(operation==6)begin
    if(rounded[l]>16384)begin formatted[16*l+:16]=16384;pair_saturated=1;end
    else if(rounded[l]<0)begin formatted[16*l+:16]=0;pair_saturated=1;end
    else formatted[16*l+:16]=rounded[l][15:0];
   end else begin
    if(rounded[l]>32767)begin formatted[16*l+:16]=32767;pair_saturated=1;end
    else if(rounded[l]< -32768)begin formatted[16*l+:16]=16'h8000;pair_saturated=1;end
    else formatted[16*l+:16]=rounded[l][15:0];
   end
  end
 end

 always @(posedge clk)begin
  if(reset)begin
   phase<=IDLE;rsp_valid<=0;rsp_data<=0;rsp_error<=0;rsp_saturated<=0;
   context_valid<=0;statistics_final<=0;factor_valid<=0;top_loading<=0;
   operation<=0;n<=0;position<=0;enabled<=0;mode<=0;count<=0;
  end else begin
   if(rsp_valid&&rsp_ready)rsp_valid<=0;
   case(phase)
    IDLE:if(cmd_valid&&cmd_ready)begin
     rsp_error<=!command_ok;rsp_saturated<=0;rsp_data<=0;
     if(!command_ok)rsp_valid<=1;
     else case(cmd_op)
      0:begin
       mode<=cmd_param[1:0];epsilon<=cmd_data[31:0];context_valid<=1;statistics_final<=0;factor_valid<=0;
       count<=0;sum<=0;sumsq<=0;maximum<=-32768;minimum<=32767;exp_sum<=0;exp_count<=0;replayed<=0;rsp_valid<=1;
      end
      1,3,5,6,12:begin
       operation<=cmd_op;data<=cmd_data;aux<=cmd_aux;n<=cmd_count;position<=0;result<=0;saturated<=0;phase<=CALC;
      end
      2:begin
       statistics_final<=1;
       if(mode==0)rsp_valid<=1;
       else if(mode==1)begin group_n<={sumsq,16'd0};group_d<={48'd0,count};phase<=MEAN_START;end
       else begin group_n<={sumsq,16'd0}+{16'd0,epsilon,16'd0};phase<=ROOT_START;end
      end
      // Q1.14 probabilities are nonnegative S16 operands accepted directly by
      // M; Q0.16 would reinterpret probabilities above0.5 as negative S16.
      4:begin group_n<=64'd1<<44;group_d<={32'd0,exp_sum};phase<=FACTOR_START;end
      7:begin rsp_data<={sumsq,sum,minimum,maximum,count};rsp_valid<=1;end
      8:begin top_count<=0;top_k<=cmd_param[3:0];top_loading<=1;rsp_valid<=1;end
      9:begin
       for(integer i=0;i<4;i=i+1)if(i<cmd_count)begin
        top_score[32'(top_count)+i]<=cmd_data[32*i+:16];top_id[32'(top_count)+i]<=cmd_data[32*i+16+:16];
       end
       top_count<=top_count+{2'd0,cmd_count};rsp_valid<=1;
      end
      10:begin selected<=0;scan_index<=0;top_round<=0;best_valid<=0;chosen<=0;phase<=TOP_SCAN;end
      11:begin rsp_data<={64'd0,32'd0,factor};rsp_valid<=1;end
      default:begin rsp_valid<=1;rsp_error<=1;end
     endcase
    end
    CALC:begin
     for(integer l=0;l<2;l=l+1)begin
      enabled[l]<=position+4'(l)<n;
      raw[l]<=fetch[l];gamma[l]<=16'(aux>>(16*(position+4'(l))));
      square[l]<=fetch[l]*fetch[l];
      // The existing exponential returns32768 for every nonnegative
      // difference, exactly exp(min(x,0)); op12 never reads maximum.
      ex[l]<=exponential(operation==12?$signed({fetch[l][15],fetch[l]}):
       $signed({fetch[l][15],fetch[l]})-$signed({maximum[15],maximum}));
     end
     phase<=operation==5||operation==6?NORM_MUL:ACCUM;
    end
    ACCUM:begin
     if(operation==1)begin
      sum<=sum+pair_sum;sumsq<=sumsq+{15'd0,pair_square};count<=count+{15'd0,enabled[0]}+{15'd0,enabled[1]};
      if(pair_max>maximum)maximum<=pair_max;if(pair_min<minimum)minimum<=pair_min;
     end else begin
      // Only the legacy exp-accumulate command owns persistent statistics.
      // op12 shares the result lanes without changing exp_count or exp_sum.
      if(operation==3)begin
       exp_sum<=exp_sum+{15'd0,pair_exp};exp_count<=exp_count+{15'd0,enabled[0]}+{15'd0,enabled[1]};
      end
      for(integer l=0;l<2;l=l+1)if(enabled[l])result[16*(position+4'(l))+:16]<=ex[l];
      if(operation==12&&DIRECT_LANES==4)
       for(integer l=0;l<2;l=l+1)if(direct_extra_enabled[l])
        result[16*(position+4'd2+4'(l))+:16]<=direct_extra_exp[l];
     end
     if({1'b0,position}+{1'b0,accum_step}>={1'b0,n})begin phase<=IDLE;rsp_valid<=1;
      if(operation==3||operation==12)begin
       rsp_data<=result;
       for(integer l=0;l<2;l=l+1)if(enabled[l])rsp_data[16*(position+4'(l))+:16]<=ex[l];
       // The current result registers update on this same edge, so also
       // override the final two lanes in rsp_data directly.
       if(operation==12&&DIRECT_LANES==4)
        for(integer l=0;l<2;l=l+1)if(direct_extra_enabled[l])
         rsp_data[16*(position+4'd2+4'(l))+:16]<=direct_extra_exp[l];
      end
     end else begin position<=position+accum_step;phase<=CALC;end
    end
    MEAN_START:if(group_ready)phase<=MEAN_WAIT;
    MEAN_WAIT:if(group_valid)begin group_n<=group_q+{16'd0,epsilon,16'd0};phase<=ROOT_START;end
    ROOT_START:if(group_ready)phase<=ROOT_WAIT;
    ROOT_WAIT:if(group_valid)begin
     if(group_error||group_q==0)begin phase<=IDLE;rsp_valid<=1;rsp_error<=1;factor_valid<=0;end
     else begin group_n<=64'd1<<38;group_d<=group_q;phase<=FACTOR_START;end
    end
    FACTOR_START:if(group_ready)phase<=FACTOR_WAIT;
    FACTOR_WAIT:if(group_valid)begin
     phase<=IDLE;rsp_valid<=1;rsp_error<=group_error||(|group_q[63:32]);
     factor_valid<=!group_error&&!(|group_q[63:32]);factor<=group_q[31:0];
    end
    NORM_MUL:begin
     for(integer l=0;l<2;l=l+1)
      norm_product[l]<=norm_operand[l]*$signed({1'b0,factor});
     phase<=NORM_GATE;
    end
    NORM_GATE:begin
     for(integer l=0;l<2;l=l+1)gate_product[l]<=operation==6?$signed({{16{norm_product[l][47]}},norm_product[l]}):normalized_gate[l];
     phase<=EMIT;
    end
    EMIT:begin
     for(integer l=0;l<2;l=l+1)if(enabled[l])result[16*(position+4'(l))+:16]<=formatted[16*l+:16];
     saturated<=saturated||pair_saturated;
     replayed<=replayed+{15'd0,enabled[0]}+{15'd0,enabled[1]};
     if(position+2>=n)begin
      rsp_data<=result;
      for(integer l=0;l<2;l=l+1)if(enabled[l])rsp_data[16*(position+4'(l))+:16]<=formatted[16*l+:16];
      rsp_saturated<=saturated||pair_saturated;rsp_valid<=1;phase<=IDLE;
     end else begin position<=position+2;phase<=CALC;end
    end
    TOP_SCAN:begin
     if(!selected[scan_index]&&(!best_valid||top_score[scan_index]>best_value||(top_score[scan_index]==best_value&&top_id[scan_index]<best_id)))begin
      best_valid<=1;best_value<=top_score[scan_index];best_id<=top_id[scan_index];best_index<=scan_index;
     end
     if(scan_index+1>=top_count)phase<=TOP_SAVE;else scan_index<=scan_index+1'b1;
    end
    TOP_SAVE:begin
     selected[best_index]<=1;chosen[16*top_round+:16]<=best_id;
     if(top_round+1>=top_k)begin
      rsp_data<=chosen;rsp_data[16*top_round+:16]<=best_id;rsp_valid<=1;phase<=IDLE;top_loading<=0;
     end else begin top_round<=top_round+1'b1;scan_index<=0;best_valid<=0;phase<=TOP_SCAN;end
    end
    default:begin phase<=IDLE;rsp_valid<=1;rsp_error<=1;end
   endcase
  end
 end
 // A static configuration error must fail before any command is accepted.
 initial begin
  if(NEXP_DIRECT_LANES!=2&&NEXP_DIRECT_LANES!=4)
   $fatal(1,"NEXP_DIRECT_LANES must be exactly 2 or 4");
 end
 // Remainder is an internal diagnostic of the shared exact arithmetic unit.
 wire unused_remainder=^group_r;
endmodule
