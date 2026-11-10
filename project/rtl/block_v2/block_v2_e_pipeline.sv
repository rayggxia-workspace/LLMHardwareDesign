// Optional eight-S16 E pipeline. Same arithmetic ABI as block_v2_e;
// four registered stages, II=1 with parallel A/B/C, global backpressure.
// Compact/local-S frontends retain their own operand and command limits.
module block_v2_e_pipeline(
 input wire clk,reset,in_valid,output wire in_ready,
 input wire [3:0] in_op,input wire [4:0] in_shift,
 input wire [127:0] in_a,in_b,in_c,
 output reg out_valid,input wire out_ready,
 output reg [127:0] out_data,output reg out_error,out_saturated
);
 wire advance=!out_valid||out_ready;
 assign in_ready=!reset&&advance;
 reg v1,v2,v3;
 reg [3:0] op1,op2,op3;
 reg [4:0] shift1,shift2,shift3;
 reg signed [15:0] a1[0:7],b1[0:7],c1[0:7];
 reg signed [15:0] a2[0:7],b2[0:7],c2[0:7];
 reg signed [31:0] product2[0:7],rot2[0:7];
 reg signed [47:0] total3[0:7];
 reg signed [47:0] value,rounded;
 reg [47:0] mask,remainder,half;
 reg [127:0] packed_result;
 reg clipped;
 always @* begin
  packed_result=0;clipped=0;value=0;rounded=0;mask=0;remainder=0;half=0;
  for(integer j=0;j<8;j=j+1)begin
   value=total3[j];rounded=value;
   if((op3==2||op3==3||op3==9||op3==10||op3==13)&&shift3!=0)begin
    mask=(48'd1<<shift3)-1;remainder=$unsigned(value)&mask;half=48'd1<<(shift3-1);
    rounded=(value>>>shift3)+$signed({47'b0,(remainder>half)||((remainder==half)&&value[{1'b0,shift3}])});
   end
   if(op3==12)begin
    if(rounded>127)begin rounded=127;clipped=1;end
    else if(rounded< -128)begin rounded=-128;clipped=1;end
    packed_result[8*j+:8]=rounded[7:0];
   end else begin
    if(rounded>32767)begin rounded=32767;clipped=1;end
    else if(rounded< -32768)begin rounded=-32768;clipped=1;end
    packed_result[16*j+:16]=rounded[15:0];
   end
  end
 end
 always @(posedge clk)begin
  if(reset)begin
   v1<=0;v2<=0;v3<=0;out_valid<=0;out_data<=0;out_error<=0;out_saturated<=0;
   op1<=0;op2<=0;op3<=0;shift1<=0;shift2<=0;shift3<=0;
  end else if(advance)begin
   v1<=in_valid;v2<=v1;v3<=v2;out_valid<=v3;
   op1<=in_op;op2<=op1;op3<=op2;
   shift1<=in_shift;shift2<=shift1;shift3<=shift2;
   for(integer i=0;i<8;i=i+1)begin
    a1[i]<=in_a[16*i+:16];b1[i]<=in_b[16*i+:16];c1[i]<=in_c[16*i+:16];
    a2[i]<=a1[i];b2[i]<=b1[i];c2[i]<=c1[i];
    product2[i]<=a1[i]*(op1==9?b1[i&6]:b1[i]);
    rot2[i]<=a1[i^1]*b1[i|1];
    case(op2)
     0:total3[i]<=$signed({{32{a2[i][15]}},a2[i]})+$signed({{32{b2[i][15]}},b2[i]});
     1:total3[i]<=$signed({{32{a2[i][15]}},a2[i]})-$signed({{32{b2[i][15]}},b2[i]});
     2:total3[i]<={{16{product2[i][31]}},product2[i]};
     3:total3[i]<=$signed({{16{product2[i][31]}},product2[i]})+$signed({{32{c2[i][15]}},c2[i]});
     4:total3[i]<=a2[i]>b2[i]?{{32{a2[i][15]}},a2[i]}:{{32{b2[i][15]}},b2[i]};
     5:total3[i]<=a2[i]<b2[i]?{{32{a2[i][15]}},a2[i]}:{{32{b2[i][15]}},b2[i]};
     6:total3[i]<=c2[i]!=0?{{32{a2[i][15]}},a2[i]}:{{32{b2[i][15]}},b2[i]};
     7:total3[i]<=$signed({{32{a2[i][15]}},a2[i]})<<<shift2;
     8:total3[i]<=$signed({{32{a2[i][15]}},a2[i]})>>>shift2;
     9:total3[i]<=i%2==0?
      $signed({{16{product2[i][31]}},product2[i]})-$signed({{16{rot2[i][31]}},rot2[i]}):
      $signed({{16{product2[i][31]}},product2[i]})+$signed({{16{rot2[i][31]}},rot2[i]});
     10:total3[i]<={{32{a2[i][15]}},a2[i]};
     11:total3[i]<=a2[i]<0?-$signed({{32{a2[i][15]}},a2[i]}):$signed({{32{a2[i][15]}},a2[i]});
     13:total3[i]<=i<4?{{16{a2[2*(i&3)+1][15]}},a2[2*(i&3)+1],a2[2*(i&3)]}:48'sd0;
     default:total3[i]<={{32{a2[i][15]}},a2[i]};
    endcase
   end
   out_data<=op3>13?128'd0:packed_result;
   out_error<=op3>13;out_saturated<=op3<=13&&clipped;
  end
 end
endmodule
