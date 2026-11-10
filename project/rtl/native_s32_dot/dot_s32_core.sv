// Refs #252. Explicit new P-owned functional compute resource, not LC glue.
// ROWS query rows share four B values: 4/8/16 real signed32 multipliers.
// Each query has eight80-bit carry-save full-K accumulator pairs.
// A logical N8 step is two groups of four columns; full-K RNE occurs once.
module dot_s32_core #(parameter integer ROWS=1) (
 input wire clk,reset,
 input wire in_valid,output wire in_ready,
 input wire [1:0] in_kind, // BEGIN0 STEP1 CANCEL2; kind3 rejected
 input wire [127:0] in_key,input wire [31:0] in_tag,
 input wire [15:0] in_full_k,in_k,input wire in_group,
 input wire [3:0] in_n,input wire [2:0] in_rows,input wire [5:0] in_shift,
 input wire [ROWS*32-1:0] in_a,input wire [127:0] in_b,
 output reg out_valid,input wire out_ready,
 output reg [1:0] out_kind,output reg [127:0] out_key,
 output reg [31:0] out_tag,output reg out_error,out_done,
 output reg [ROWS*256-1:0] out_data
);
 localparam integer MULTS=ROWS*4,OUTPUTS=ROWS*8;
 reg owned,sequence_done,expected_group;
 reg [127:0] owner;
 reg [15:0] full_k,next_k;
 reg [3:0] lanes;reg [2:0] rows;
 reg [5:0] shift;
 reg [ROWS*32-1:0] shared_a;
 reg [79:0] sum[0:OUTPUTS-1],carry[0:OUTPUTS-1];
 reg [3:0] valid_pipe,error_pipe,last_pipe,group_pipe;
 reg [1:0] kind_pipe[0:3];
 reg [31:0] tag_pipe[0:3];
 reg [127:0] key_pipe[0:3];
 reg [31:0] ll0[0:MULTS-1],hh0[0:MULTS-1];
 reg signed [31:0] hl0[0:MULTS-1],lh0[0:MULTS-1];
 reg [31:0] ll1[0:MULTS-1],hh1[0:MULTS-1];
 reg signed [32:0] cross1[0:MULTS-1];
 reg [63:0] product_sum2[0:MULTS-1],product_carry2[0:MULTS-1],product3[0:MULTS-1];
 reg [2:0] finish_state;
 reg [31:0] finish_tag;
 reg [127:0] finish_key;
 reg [39:0] final_low[0:OUTPUTS-1];reg [OUTPUTS-1:0] final_carry;
 reg signed [79:0] final_value[0:OUTPUTS-1],quotient[0:OUTPUTS-1];
 reg [OUTPUTS-1:0] increment;
 wire empty=valid_pipe==0;
 wire advance=!out_valid || out_ready;
 assign in_ready=!reset && finish_state==0 && advance &&
  (in_kind==1 ? !sequence_done : empty && !out_valid);
 reg command_error;
 reg last_step;
 always @*begin
  command_error=0;last_step=0;
  case(in_kind)
   0:command_error=owned || in_full_k==0 || in_n==0 || in_n>8 || in_rows==0 || int'(in_rows)>ROWS;
   1:begin
    command_error=!owned || sequence_done || in_key!=owner || in_k!=next_k ||
     in_group!=expected_group || (in_group && in_a!=shared_a);
    for(integer j=0;j<4;j=j+1)
     if((in_group ? 4+j : j)>=int'(lanes) && in_b[j*32+:32]!=0)command_error=1;
    for(integer r=0;r<ROWS;r=r+1)
     if(r>=int'(rows) && in_a[r*32+:32]!=0)command_error=1;
    last_step=next_k==full_k-1'b1 && (lanes<=4 || in_group);
   end
   2:command_error=!owned || in_key!=owner;
   default:command_error=1;
  endcase
 end
 // Mixed signed16 * unsigned16 fits signed32. Explicit17-bit operands keep
 // INT_MIN/MAX and unsigned low limbs exact; no unsigned32 shortcut.
 function automatic [31:0] mixed(input [15:0] hi,input [15:0] lo);
  reg signed [33:0] wide;
  begin
   wide=$signed({hi[15],hi})*$signed({1'b0,lo});
   mixed=wide[33:32]=={2{wide[31]}} ? wide[31:0] : 32'd0;
  end
 endfunction
 function automatic round_increment(input signed [79:0] value,input [5:0] amount);
  reg [79:0] mask;
  begin
   mask=amount>1 ? (80'd1<<(amount-1'b1))-1'b1 : 80'd0;
   round_increment=amount!=0 && value[{1'b0,amount}-7'd1] && ((|(value&mask)) || value[{1'b0,amount}]);
  end
 endfunction
 function automatic [31:0] saturate(input signed [79:0] q,input inc);
  begin
   if(q>=80'sd2147483647)saturate=32'h7fffffff;
   else if(q< -80'sd2147483648)saturate=32'h80000000;
   else saturate=q[31:0]+{31'd0,inc};
  end
 endfunction
 reg [63:0] term_l,term_cross,term_h;
 reg [79:0] extended_product;
 reg [40:0] low_add;
 reg [39:0] high_add;
 reg [$clog2(OUTPUTS)-1:0] destination;
 always @(posedge clk)begin
  if(reset)begin
   owned<=0;sequence_done<=0;expected_group<=0;owner<=0;full_k<=0;next_k<=0;lanes<=0;rows<=0;shift<=0;shared_a<=0;
   valid_pipe<=0;error_pipe<=0;last_pipe<=0;group_pipe<=0;
   finish_state<=0;finish_tag<=0;finish_key<=0;final_carry<=0;increment<=0;
   out_valid<=0;out_kind<=0;out_key<=0;out_tag<=0;out_error<=0;out_done<=0;out_data<=0;
   for(integer p=0;p<4;p=p+1)begin
    kind_pipe[p]<=0;tag_pipe[p]<=0;key_pipe[p]<=0;
   end
   for(integer p=0;p<MULTS;p=p+1)begin
    ll0[p]<=0;hh0[p]<=0;hl0[p]<=0;lh0[p]<=0;
    ll1[p]<=0;hh1[p]<=0;cross1[p]<=0;product_sum2[p]<=0;product_carry2[p]<=0;product3[p]<=0;
   end
   for(integer j=0;j<OUTPUTS;j=j+1)begin sum[j]<=0;carry[j]<=0;final_low[j]<=0;final_value[j]<=0;quotient[j]<=0;end
  end else begin
   if(out_valid && out_ready)begin
    out_valid<=0;
    if(out_done && !out_error)begin owned<=0;sequence_done<=0;end
   end
   if(finish_state==0 && advance)begin
    valid_pipe<={valid_pipe[2:0],in_valid && in_ready};
    error_pipe<={error_pipe[2:0],command_error};last_pipe<={last_pipe[2:0],last_step};
    group_pipe<={group_pipe[2:0],in_group};
    for(integer p=1;p<4;p=p+1)begin
     kind_pipe[p]<=kind_pipe[p-1];tag_pipe[p]<=tag_pipe[p-1];key_pipe[p]<=key_pipe[p-1];
    end
    kind_pipe[0]<=in_kind;tag_pipe[0]<=in_tag;key_pipe[0]<=in_key;
    for(integer j=0;j<MULTS;j=j+1)begin
     ll0[j]<=in_a[(j/4)*32+:16]*in_b[(j%4)*32+:16];
     hl0[j]<=$signed(mixed(in_a[(j/4)*32+16+:16],in_b[(j%4)*32+:16]));
     lh0[j]<=$signed(mixed(in_b[(j%4)*32+16+:16],in_a[(j/4)*32+:16]));
     hh0[j]<=$signed(in_a[(j/4)*32+16+:16])*$signed(in_b[(j%4)*32+16+:16]);
     ll1[j]<=ll0[j];hh1[j]<=hh0[j];cross1[j]<={hl0[j][31],hl0[j]}+{lh0[j][31],lh0[j]};
     term_l={32'd0,ll1[j]};term_cross={{15{cross1[j][32]}},cross1[j],16'd0};term_h={hh1[j],32'd0};
     product_sum2[j]<=term_l^term_cross^term_h;
     product_carry2[j]<=((term_l&term_cross)|(term_l&term_h)|(term_cross&term_h))<<1;
     product3[j]<=product_sum2[j]+product_carry2[j];
    end
    if(in_valid && in_ready && !command_error)begin
     if(in_kind==0)begin
      owned<=1;owner<=in_key;full_k<=in_full_k;lanes<=in_n;rows<=in_rows;shift<=in_shift;
      next_k<=0;expected_group<=0;sequence_done<=0;
      for(integer j=0;j<OUTPUTS;j=j+1)begin sum[j]<=0;carry[j]<=0;end
     end else if(in_kind==1)begin
      if(lanes>4 && !in_group)begin expected_group<=1;shared_a<=in_a;end
      else begin expected_group<=0;next_k<=next_k+1'b1;if(last_step)sequence_done<=1;end
     end else if(in_kind==2)sequence_done<=1;
    end
    if(valid_pipe[3])begin
     if(kind_pipe[3]==1 && !error_pipe[3])begin
      for(integer j=0;j<MULTS;j=j+1)begin
       destination=$clog2(OUTPUTS)'((j/4)*8+(group_pipe[3] ? 4 : 0)+(j%4));
       if(j/4<int'(rows) && (j%4)+(group_pipe[3] ? 4 : 0)<int'(lanes))begin
        extended_product={{16{product3[j][63]}},product3[j]};
        sum[destination]<=sum[destination]^carry[destination]^extended_product;
        carry[destination]<=((sum[destination]&carry[destination])|
          (sum[destination]&extended_product)|(carry[destination]&extended_product))<<1;
       end
      end
     end
     if(kind_pipe[3]==1 && !error_pipe[3] && last_pipe[3])begin
      finish_state<=1;finish_tag<=tag_pipe[3];finish_key<=key_pipe[3];
     end else begin
      out_valid<=1;out_kind<=kind_pipe[3];out_key<=key_pipe[3];out_tag<=tag_pipe[3];
      out_error<=error_pipe[3];out_done<=kind_pipe[3]==2 && !error_pipe[3];out_data<=0;
     end
    end
   end
   case(finish_state)
    1:begin
     for(integer j=0;j<OUTPUTS;j=j+1)begin
      low_add={1'b0,sum[j][39:0]}+{1'b0,carry[j][39:0]};
      final_low[j]<=low_add[39:0];final_carry[j]<=low_add[40];
     end
     finish_state<=2;
    end
    2:begin
     for(integer j=0;j<OUTPUTS;j=j+1)begin
      high_add=sum[j][79:40]+carry[j][79:40]+{39'd0,final_carry[j]};
      final_value[j]<={high_add,final_low[j]};
     end
     finish_state<=3;
    end
    3:begin
     for(integer j=0;j<OUTPUTS;j=j+1)begin
      quotient[j]<=final_value[j]>>>shift;increment[j]<=round_increment(final_value[j],shift);
     end
     finish_state<=4;
    end
    4:if(advance)begin
     out_valid<=1;out_kind<=1;out_key<=finish_key;out_tag<=finish_tag;out_error<=0;out_done<=1;
     for(integer j=0;j<OUTPUTS;j=j+1)out_data[j*32+:32]<=saturate(quotient[j],increment[j]);
     finish_state<=0;
    end
    default:begin end
   endcase
  end
 end
endmodule
