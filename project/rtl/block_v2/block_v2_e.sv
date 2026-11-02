// Issue143 element/pair engine. Eight S16 lanes; no vector reduction/replay RAM.
// MUL/FMA/RoPE round the full intermediate once; results saturate, never wrap.
// Op13 reinterprets the existing A bank as four S32 words, RNE-narrows to
// four S16 values in out_data[63:0], and clears out_data[127:64].
module block_v2_e(
 input wire clk,reset,in_valid,output wire in_ready,
 input wire [3:0] in_op,input wire [4:0] in_shift,
 input wire [127:0] in_a,in_b,in_c,
 output reg out_valid,input wire out_ready,
 output reg [127:0] out_data,output reg out_error,out_saturated
);
 localparam IDLE=0,MUL=1,ROT_MUL=2,TOTAL=3,WRITE=4;
 reg [2:0] phase;
 reg [3:0] op;reg [4:0] shift;
 reg signed [15:0] a[0:7],b[0:7],c[0:7];
 reg signed [31:0] product[0:7],rot_product[0:7];
 reg signed [47:0] total[0:7];
 wire signed [15:0] multiplier_b[0:7];
 for(genvar k=0;k<8;k=k+1)begin: operand_select
  assign multiplier_b[k]=op==9?b[k&6]:b[k];
 end
 reg signed [47:0] value,rounded;reg [47:0] mask,remainder,half;
 reg [127:0] packed_result;reg clipped;
 integer i;
 assign in_ready=!reset&&phase==IDLE&&(!out_valid||out_ready);
 always @* begin
  packed_result=0;clipped=0;value=0;rounded=0;mask=0;remainder=0;half=0;
  for(integer j=0;j<8;j=j+1)begin
   value=total[j];rounded=value;
   if((op==2||op==3||op==9||op==10||op==13)&&shift!=0)begin
    mask=(48'd1<<shift)-1;remainder=$unsigned(value)&mask;half=48'd1<<(shift-1);
    rounded=(value>>>shift)+$signed({47'b0,(remainder>half)||((remainder==half)&&value[{1'b0,shift}])});
   end
   if(op==12)begin
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
  if(reset)begin phase<=IDLE;out_valid<=0;out_data<=0;out_error<=0;out_saturated<=0;op<=0;shift<=0;end
  else begin
   if(out_valid&&out_ready)out_valid<=0;
   case(phase)
    IDLE:if(in_valid&&in_ready)begin
     if(in_op>13)begin out_valid<=1;out_data<=0;out_error<=1;out_saturated<=0;end
     else begin
      op<=in_op;shift<=in_shift;out_error<=0;out_saturated<=0;
      for(i=0;i<8;i=i+1)begin a[i]<=in_a[16*i+:16];b[i]<=in_b[16*i+:16];c[i]<=in_c[16*i+:16];end
      phase<=MUL;
     end
    end
    MUL:begin
     for(i=0;i<8;i=i+1)product[i]<=a[i]*multiplier_b[i];
     phase<=op==9?ROT_MUL:TOTAL;
    end
    ROT_MUL:begin
     for(i=0;i<8;i=i+1)rot_product[i]<=a[i^1]*b[i|1];
     phase<=TOTAL;
    end
    TOTAL:begin
     for(i=0;i<8;i=i+1)case(op)
      0:total[i]<=$signed({{32{a[i][15]}},a[i]})+$signed({{32{b[i][15]}},b[i]});
      1:total[i]<=$signed({{32{a[i][15]}},a[i]})-$signed({{32{b[i][15]}},b[i]});
      2:total[i]<={{16{product[i][31]}},product[i]};
      3:total[i]<=$signed({{16{product[i][31]}},product[i]})+$signed({{32{c[i][15]}},c[i]});
      4:total[i]<=a[i]>b[i]?{{32{a[i][15]}},a[i]}:{{32{b[i][15]}},b[i]};
      5:total[i]<=a[i]<b[i]?{{32{a[i][15]}},a[i]}:{{32{b[i][15]}},b[i]};
      6:total[i]<=c[i]!=0?{{32{a[i][15]}},a[i]}:{{32{b[i][15]}},b[i]};
      7:total[i]<=$signed({{32{a[i][15]}},a[i]})<<<shift;
      8:total[i]<=$signed({{32{a[i][15]}},a[i]})>>>shift;
      9:total[i]<=i%2==0?
       $signed({{16{product[i][31]}},product[i]})-$signed({{16{rot_product[i][31]}},rot_product[i]}):
       $signed({{16{product[i][31]}},product[i]})+$signed({{16{rot_product[i][31]}},rot_product[i]});
      10:total[i]<={{32{a[i][15]}},a[i]};
      11:total[i]<=a[i]<0?-$signed({{32{a[i][15]}},a[i]}):$signed({{32{a[i][15]}},a[i]});
      13:total[i]<=i<4?{{16{a[2*(i&3)+1][15]}},a[2*(i&3)+1],a[2*(i&3)]}:48'sd0;
      default:total[i]<={{32{a[i][15]}},a[i]};
     endcase
     phase<=WRITE;
    end
    WRITE:begin out_data<=packed_result;out_saturated<=clipped;out_valid<=1;phase<=IDLE;end
    default:begin phase<=IDLE;out_valid<=1;out_error<=1;out_data<=0;out_saturated<=0;end
   endcase
  end
 end
endmodule
