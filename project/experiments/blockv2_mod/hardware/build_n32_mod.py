"""Extend N32 with RMS factor using the existing divider and scale multipliers."""
from pathlib import Path
from hashlib import sha256
import json
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'rtl/p_services/n_s32_softmax_s128.sv'
original=source.read_text()
s=original.replace('module n_s32_softmax_s128 (','module n_s32_mod (',1)
s=s.replace(' input wire clk,reset,',""" input wire clk,reset,
 input wire cmd_rms,
 input wire [31:0] cmd_epsilon_mantissa,
 input wire signed [7:0] cmd_epsilon_shift,
 input wire signed [5:0] cmd_baseline_shift,
 output reg [31:0] rsp_factor,
 output reg signed [5:0] rsp_shift,
 output reg [5:0] rsp_extra_shift,""",1)
s=s.replace('WRITE_REQ=14,WRITE_ACK=15,EXP_ROUND_HIGH=16,SCALE_ROUND_HIGH=17;',
"""WRITE_REQ=14,WRITE_ACK=15,EXP_ROUND_HIGH=16,SCALE_ROUND_HIGH=17,
     RMS_RANGE=18,RMS_SELECT=19,RMS_SQUARE=20,RMS_ACCUM=21,
     RMS_MEAN_START=22,RMS_MEAN_WAIT=23,RMS_ROOT_START=24,RMS_ROOT_WAIT=25,
     RMS_FACTOR_START=26,RMS_FACTOR_WAIT=27,RMS_EPSILON=28;""")
s=s.replace(' reg [4:0] state;',""" reg [4:0] state;
 reg rms_mode,rms_replay,rms_high;
 reg [12:0] rms_count;
 reg signed [31:0] minimum;
 reg [31:0] rms_epsilon_mantissa,rms_epsilon_word;
 reg signed [7:0] rms_epsilon_shift;
 reg [47:0] rms_sum;
 reg [63:0] rms_radicand,rms_root;""")
s=s.replace("({3'd0,cmd_base}+cmd_words<=13'd1024);","({3'd0,cmd_base}+cmd_words<=13'd1024)&&(!cmd_rms||cmd_epsilon_mantissa!=0);")
old=""" block_v2_n_group divider(clk,reset,state==DIV_START&&!stop,div_ready,1'b0,
     64'd1<<48,{32'd0,total},div_valid,state==DIV_WAIT,div_q,div_r,div_error);"""
new=""" wire rms_div_start=state==RMS_MEAN_START||state==RMS_ROOT_START||state==RMS_FACTOR_START;
 wire rms_div_wait=state==RMS_MEAN_WAIT||state==RMS_ROOT_WAIT||state==RMS_FACTOR_WAIT;
 wire [63:0] div_numerator=!rms_mode ? 64'd1<<48 :
     state==RMS_MEAN_START ? {rms_sum,16'd0} :
     state==RMS_ROOT_START ? rms_radicand : 64'd1<<38;
 wire [63:0] div_input_denominator=!rms_mode ? {32'd0,total} :
     state==RMS_MEAN_START ? {51'd0,rms_count} : rms_root;
 block_v2_n_group divider(clk,reset,(state==DIV_START||rms_div_start)&&!stop,
     div_ready,state==RMS_ROOT_START,div_numerator,div_input_denominator,
     div_valid,state==DIV_WAIT||rms_div_wait,div_q,div_r,div_error);"""
assert old in s;s=s.replace(old,new)
needle=" wire [18:0] packet_sum="
start=s.index(needle)
insert=""" function automatic signed [63:0] round_scaled(
     input signed [63:0] value,input signed [9:0] shift);
   reg signed [63:0] floor_q;
   reg [63:0] denominator,remainder;
   begin
     if(shift<=0) round_scaled=value<<<$unsigned(-shift);
     else if(shift>63) round_scaled=0;
     else begin
       denominator=64'd1<<$unsigned(shift);
       floor_q=value>>>$unsigned(shift);
       remainder=$unsigned(value)&(denominator-64'd1);
       round_scaled=floor_q+$signed({63'd0,remainder>(denominator>>1)||
           (remainder==(denominator>>1)&&floor_q[0])});
     end
   end
 endfunction
 reg signed [31:0] packet_min;
 always @* begin
   packet_min=32'sh7fffffff;
   for(integer i=0;i<4;i=i+1)
     if(int'(valid_lanes)>i&&$signed(input_word[32*i+:32])<packet_min)
       packet_min=$signed(input_word[32*i+:32]);
 end
 wire rms_fits=round_scaled({{32{minimum[31]}},minimum},10'(rsp_shift))>=-64'sd32768&&
               round_scaled({{32{maximum[31]}},maximum},10'(rsp_shift))<=64'sd32767;
 wire signed [9:0] epsilon_div_shift=-10'(rms_epsilon_shift)+10'({3'd0,rsp_extra_shift,1'b0});
 wire [63:0] epsilon_scaled=$unsigned(round_scaled($signed({32'd0,rms_epsilon_mantissa}),epsilon_div_shift));
 wire [47:0] square_sum=
     (int'(valid_lanes)>2*int'(rms_high) ? norm_product[0][47:0] : 48'd0)+
     (int'(valid_lanes)>2*int'(rms_high)+1 ? norm_product[1][47:0] : 48'd0);
"""
s=s[:start]+insert+s[start:]
old='  assign next_norm_product[lane]=scale_operand*factor;'
new="""  wire signed [31:0] rms_operand=$signed(input_word[32*(2*int'(rms_high)+lane)+:32]);
  wire signed [63:0] rms_narrow=round_scaled({{32{rms_operand[31]}},rms_operand},10'(rsp_shift));
  wire [16:0] rms_magnitude=17'(rms_narrow<0 ? -rms_narrow : rms_narrow);
  wire [16:0] multiply_left=state==RMS_SQUARE ? rms_magnitude : scale_operand;
  wire [32:0] multiply_right=state==RMS_SQUARE ? {16'd0,rms_magnitude} : factor;
  assign next_norm_product[lane]=multiply_left*multiply_right;"""
assert old in s;s=s.replace(old,new)
s=s.replace('   cancelled<=0;',"""   cancelled<=0;rms_mode<=0;rms_replay<=0;rms_high<=0;rms_count<=0;
   rsp_factor<=0;rsp_shift<=0;rsp_extra_shift<=0;rms_sum<=0;
   rms_epsilon_mantissa<=0;rms_epsilon_shift<=0;rms_epsilon_word<=0;
   rms_radicand<=0;rms_root<=0;minimum<=0;""",1)
s=s.replace('state!=WRITE_REQ&&state!=WRITE_ACK&&state!=DIV_WAIT)', 'state!=WRITE_REQ&&state!=WRITE_ACK&&state!=DIV_WAIT&&!rms_div_wait)')
s=s.replace('    IDLE:if(cmd_valid&&cmd_ready)begin',"""    IDLE:if(cmd_valid&&cmd_ready)begin
     rsp_factor<=0;rsp_shift<=cmd_baseline_shift;rsp_extra_shift<=0;
     rms_mode<=cmd_rms;rms_replay<=0;rms_high<=0;rms_count<=cmd_count;
     rms_epsilon_mantissa<=cmd_epsilon_mantissa;rms_epsilon_shift<=cmd_epsilon_shift;
     rms_sum<=0;minimum<=32'sh7fffffff;""")
s=s.replace('state<=pass_kind==FIND_MAX?WORD_MAX:pass_kind==WRITE_EXP?DIFF:SCALE;',
'state<=rms_mode ? (rms_replay ? RMS_SQUARE : RMS_RANGE) : pass_kind==FIND_MAX?WORD_MAX:pass_kind==WRITE_EXP?DIFF:SCALE;')
needle='    WORD_MAX:begin'
extra="""    RMS_RANGE:begin
     minimum<=minimum<packet_min ? minimum : packet_min;
     maximum<=larger(maximum,packet_max);
     word_index<=last_word ? 11'd0 : word_index+11'd1;
     state<=last_word ? RMS_SELECT : READ_REQ;
    end
    RMS_SELECT:if(rms_fits)state<=RMS_EPSILON;
     else if(rsp_shift==6'sd31)finish(1,0,0);
     else begin rsp_shift<=rsp_shift+6'sd1;rsp_extra_shift<=rsp_extra_shift+6'd1;end
    RMS_EPSILON:begin
     if(epsilon_div_shift< -10'sd31||epsilon_scaled>64'hffffffff)finish(1,0,0);
     else begin
      rms_epsilon_word<=epsilon_scaled==0 ? 32'd1 : epsilon_scaled[31:0];
      rms_replay<=1;rms_high<=0;rms_sum<=0;word_index<=0;state<=READ_REQ;
     end
    end
    RMS_SQUARE:begin
     for(integer i=0;i<2;i=i+1)norm_product[i]<=next_norm_product[i];
     state<=RMS_ACCUM;
    end
    RMS_ACCUM:begin
     rms_sum<=rms_sum+square_sum;
     if(!rms_high&&valid_lanes>2)begin rms_high<=1;state<=RMS_SQUARE;end
     else begin
      rms_high<=0;word_index<=last_word ? 11'd0 : word_index+11'd1;
      state<=last_word ? RMS_MEAN_START : READ_REQ;
     end
    end
    RMS_MEAN_START:if(div_ready)state<=RMS_MEAN_WAIT;
    RMS_MEAN_WAIT:if(div_valid)begin
     if(div_error||stop)finish(div_error,stop,0);
     else begin rms_radicand<=div_q+{16'd0,rms_epsilon_word,16'd0};state<=RMS_ROOT_START;end
    end
    RMS_ROOT_START:if(div_ready)state<=RMS_ROOT_WAIT;
    RMS_ROOT_WAIT:if(div_valid)begin
     if(div_error||div_q==0||stop)finish(div_error||div_q==0,stop,0);
     else begin rms_root<=div_q;state<=RMS_FACTOR_START;end
    end
    RMS_FACTOR_START:if(div_ready)state<=RMS_FACTOR_WAIT;
    RMS_FACTOR_WAIT:if(div_valid)begin
     if(div_error||(|div_q[63:32])||stop)finish(div_error||(|div_q[63:32]),stop,0);
     else begin
      rsp_factor<=32'(round_scaled($signed(div_q),10'({4'd0,rsp_extra_shift})));
      finish(0,0,0);
     end
    end
"""
assert needle in s;s=s.replace(needle,extra+needle)
# Argmax uses the same maximum datapath and explicit first-index tracking.
s=s.replace('input wire cmd_rms,','input wire [1:0] cmd_mode, // 0 Softmax, 1 RMS factor, 2 Argmax')
s=s.replace('output reg [31:0] rsp_factor,','output reg [31:0] rsp_scalar,rsp_index,')
s=s.replace('rsp_factor','rsp_scalar')
s=s.replace('reg rms_mode,rms_replay,rms_high;','reg rms_mode,rms_replay,rms_high,argmax_mode;')
s=s.replace('RMS_FACTOR_START=26,RMS_FACTOR_WAIT=27,RMS_EPSILON=28;',
            'RMS_FACTOR_START=26,RMS_FACTOR_WAIT=27,RMS_EPSILON=28,ARGMAX_SCAN=29;')
s=s.replace('(!cmd_rms||cmd_epsilon_mantissa!=0);',
            '(cmd_mode!=1||cmd_epsilon_mantissa!=0)&&cmd_mode<=2;')
s=s.replace('rms_mode<=0;rms_replay<=0;', 'rms_mode<=0;argmax_mode<=0;rsp_index<=0;rms_replay<=0;')
s=s.replace('rms_mode<=cmd_rms;rms_replay<=0;', 'rms_mode<=cmd_mode==1;argmax_mode<=cmd_mode==2;rsp_index<=0;rms_replay<=0;')
s=s.replace('state<=rms_mode ? (rms_replay ? RMS_SQUARE : RMS_RANGE) :',
            'state<=argmax_mode ? ARGMAX_SCAN : rms_mode ? (rms_replay ? RMS_SQUARE : RMS_RANGE) :')
s=s.replace(' wire [18:0] packet_sum=', """
 reg [1:0] packet_first;
 always @* begin
   packet_first=0;
   for(integer i=3;i>=0;i=i-1)
     if(int'(valid_lanes)>i&&score[i]==packet_max)packet_first=2'(i);
 end
 wire [18:0] packet_sum=""")
s=s.replace('    RMS_RANGE:begin', """
    ARGMAX_SCAN:begin
     if(word_index==0||packet_max>maximum)begin
      maximum<=packet_max;rsp_scalar<=$unsigned(packet_max);
      rsp_index<={19'd0,word_index,2'd0}+{30'd0,packet_first};
     end
     word_index<=last_word ? 11'd0 : word_index+11'd1;
     if(last_word)finish(0,0,0);
     else state<=READ_REQ;
    end
    RMS_RANGE:begin""")

header="""// N32 mod: one macro, one divider/root unit and two shared scale/square lanes.
// Softmax keeps the original protocol; modes 1/2 return RMS factor or Argmax.
// This is an explicit macro revision, not parent controller arithmetic.
"""
s=s.replace('module n_s32_mod (','module n_s32_reduction_engine (',1)
target=ROOT/'rtl/macros/n_s32_reduction_engine.sv'
target.write_text(header+s)
manifest={'schema':'macro-mod-revision/1','profile':'N32-reduction-mod-v1','master':'n_s32_mod',
 'source_profile':'N32','source':str(source.relative_to(ROOT)),
 'source_sha256':sha256(original.encode()).hexdigest(),
 'rtl':'rtl/macros/n_s32_mod.sv','rtl_sha256':sha256((ROOT/'rtl/macros/n_s32_mod.sv').read_bytes()).hexdigest(),
 'internal_engine_rtl':str(target.relative_to(ROOT)),
 'internal_engine_sha256':sha256(target.read_bytes()).hexdigest(),
 'resource_changes':{'divider_root_instances':'1 -> 1','scale_square_multiplier_lanes':'2 -> 2',
                    'added_state':'RMS range, sum-of-squares, count, epsilon and factor response',
                    'additional_arithmetic_macro_instances':0},
 'interface_changes':{'additional_input_bits':2,'additional_output_bits':0,
                      'sram_data_bits':'128 -> 128','softmax_abi':'preserved when cmd_mode=0','scalar_response':'16-byte result committed through existing SRAM port','configuration':'mode 3 counted command/response using existing tag/base/count pins'},
 'status':'RTL candidate; functional equivalence and numerical validation pending',
 'physical_views':'not generated; no inherited physical acceptance'}
(ROOT/'hardware/n32-mod-revision.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Wrote explicit N32 mod; added 2 input and 0 output bits, no extra divider or multiplier lanes')
