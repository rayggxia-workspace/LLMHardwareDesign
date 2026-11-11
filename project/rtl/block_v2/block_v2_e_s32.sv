// Four signed32 lanes. Positive shift is RNE right shift, negative shift is
// saturating left shift for MUL/FMA/RoPE/Convert. No intermediate narrowing.
// Opcodes 12..15 are rejected in this ABI; S16 packing is not implicit.
module block_v2_e_s32(
 input wire clk,reset,in_valid,output wire in_ready,
 input wire [3:0] in_op,input wire signed [6:0] in_shift,
 input wire [127:0] in_a,in_b,in_c,
 output reg out_valid,input wire out_ready,
 output reg [127:0] out_data,output reg out_error,out_saturated
);
 reg busy;reg [3:0] op;reg signed [6:0] shift;
 reg signed [64:0] total[0:3];
 wire signed [31:0] a[0:3],b[0:3],c[0:3];
 wire signed [63:0] product[0:3],rot[0:3];
 for(genvar j=0;j<4;j=j+1)begin: lanes
  assign a[j]=in_a[32*j+:32];assign b[j]=in_b[32*j+:32];assign c[j]=in_c[32*j+:32];
  assign product[j]=a[j]*(in_op==9?b[j&2]:b[j]);
  assign rot[j]=a[j^1]*b[j|1];
 end
 reg signed [95:0] value,rounded;
 reg [95:0] mask,remainder,half;integer amount;
 reg [127:0] packed_result;reg clipped;
 assign in_ready=!reset&&!busy&&(!out_valid||out_ready);
 always @* begin
  packed_result=0;clipped=0;value=0;rounded=0;mask=0;remainder=0;half=0;amount=0;
  for(integer j=0;j<4;j=j+1)begin
   value={{31{total[j][64]}},total[j]};rounded=value;
   if(op==2||op==3||op==9||op==10)begin
    if(shift>0)begin
     amount=int'(shift);mask=(96'd1<<amount)-1;remainder=$unsigned(value)&mask;half=96'd1<<(amount-1);
     rounded=(value>>>amount)+$signed({95'd0,(remainder>half)||((remainder==half)&&value[amount])});
    end else if(shift<0)begin
     amount=-int'(shift);
     if(amount>=32&&value!=0)begin rounded=value<0?-96'sd2147483649:96'sd2147483648;end
     else rounded=value<<<amount;
    end
   end
   if(rounded>2147483647)begin rounded=2147483647;clipped=1;end
   else if(rounded< -96'sd2147483648)begin rounded=-96'sd2147483648;clipped=1;end
   packed_result[32*j+:32]=rounded[31:0];
  end
 end
 always @(posedge clk)begin
  if(reset)begin busy<=0;out_valid<=0;out_data<=0;out_error<=0;out_saturated<=0;op<=0;shift<=0;end
  else begin
   if(out_valid&&out_ready)out_valid<=0;
   if(busy)begin out_valid<=1;out_data<=packed_result;out_error<=0;out_saturated<=clipped;busy<=0;end
   if(in_valid&&in_ready)begin
    if(in_op>=12 || ((in_op==7||in_op==8)&&in_shift<0))begin out_valid<=1;out_data<=0;out_error<=1;out_saturated<=0;end
    else begin
     busy<=1;op<=in_op;shift<=in_shift;
     for(integer j=0;j<4;j=j+1)case(in_op)
      0:total[j]<=$signed({{33{a[j][31]}},a[j]})+$signed({{33{b[j][31]}},b[j]});
      1:total[j]<=$signed({{33{a[j][31]}},a[j]})-$signed({{33{b[j][31]}},b[j]});
      2:total[j]<={product[j][63],product[j]};
      3:total[j]<=$signed({product[j][63],product[j]})+$signed({{33{c[j][31]}},c[j]});
      4:total[j]<=a[j]>b[j]?{{33{a[j][31]}},a[j]}:{{33{b[j][31]}},b[j]};
      5:total[j]<=a[j]<b[j]?{{33{a[j][31]}},a[j]}:{{33{b[j][31]}},b[j]};
      6:total[j]<=c[j]!=0?{{33{a[j][31]}},a[j]}:{{33{b[j][31]}},b[j]};
      7:total[j]<=in_shift>=32&&a[j]!=0?(a[j]<0?-65'sd2147483649:65'sd2147483648):$signed({{33{a[j][31]}},a[j]})<<<in_shift;
      8:total[j]<=$signed({{33{a[j][31]}},a[j]})>>>in_shift;
      9:total[j]<=j%2==0?$signed({product[j][63],product[j]})-$signed({rot[j][63],rot[j]}):$signed({product[j][63],product[j]})+$signed({rot[j][63],rot[j]});
      10:total[j]<={{33{a[j][31]}},a[j]};
      11:total[j]<=a[j]<0?-$signed({{33{a[j][31]}},a[j]}):$signed({{33{a[j][31]}},a[j]});
      default:total[j]<=0;
     endcase
    end
   end
  end
 end
endmodule
