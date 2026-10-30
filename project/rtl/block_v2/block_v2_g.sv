// Two independent S16 activation/gate lanes, four-stage pipeline, II=1.
// All stages freeze together under output backpressure. Payload need not reset.
module block_v2_g(
 input wire clk,reset,in_valid,output wire in_ready,
 input wire [2:0] in_fn,input wire in_gated,
 input wire [31:0] in_x,in_gate,
 output reg out_valid,input wire out_ready,
 output reg [31:0] out_data,output reg out_error,out_saturated
);
 `include "block_v2_g_tables.svh"
 wire advance=!out_valid||out_ready;
 assign in_ready=!reset&&advance;
 reg v1,v2,v3,e1,e2,e3,g1,g2,g3;
 reg sig1,sig2,sig3;
 reg signed [15:0] base1[0:1],u1[0:1],u2[0:1],f2[0:1],f3[0:1];
 reg signed [16:0] delta1[0:1];reg [4:0] frac1[0:1];
 reg signed [31:0] product3[0:1];
 reg signed [15:0] x,lo,hi;
 reg signed [16:0] offset;
 reg [10:0] index;reg [4:0] frac;
 reg signed [22:0] interpolation;
 reg signed [31:0] value,rounded;
 reg clip;
 integer l;
 function automatic signed [31:0] rne;
  input signed [31:0] n;input [4:0] s;
  reg [31:0] r,h,m;
  begin
   r=0;h=0;m=0;
   if(s==0)rne=n;
   else begin m=(32'd1<<s)-1;r=$unsigned(n)&m;h=32'd1<<(s-1);
    rne=(n>>>s)+$signed({31'b0,(r>h)||((r==h)&&n[s])});
   end
  end
 endfunction
 always @(posedge clk)begin
  if(reset)begin v1<=0;v2<=0;v3<=0;out_valid<=0;out_data<=0;out_error<=0;out_saturated<=0;
   e1<=0;e2<=0;e3<=0;g1<=0;g2<=0;g3<=0;sig1<=0;sig2<=0;sig3<=0;end
  else if(advance)begin
   v1<=in_valid;v2<=v1;v3<=v2;out_valid<=v3;
   e1<=in_fn>3;e2<=e1;e3<=e2;out_error<=e3;
   g1<=in_gated;g2<=g1;g3<=g2;
   sig1<=in_fn==1;sig2<=sig1;sig3<=sig2;
   clip=0;value=0;rounded=0;
   for(l=0;l<2;l=l+1)begin
    x=in_x[16*l+:16];lo=0;hi=0;offset=0;index=0;frac=0;
    if(in_fn<=2)begin
     if(x< -8192)begin lo=0;hi=0;end
     else if(x>8192)begin lo=in_fn==1?16'sd16384:x;hi=lo;end
     else begin
      offset=$signed({x[15],x})+17'sd8192;index=11'(offset>>5);frac=offset[4:0];
      lo=activation_lut(in_fn[1:0],index);
      hi=activation_lut(in_fn[1:0],index==512?index:index+1'b1);
     end
    end else if(in_fn==3)begin
     if(x< -16384)begin lo=0;hi=0;end
     else if(x>16384)begin lo=x;hi=lo;end
     else begin
      offset=$signed({x[15],x})+17'sd16384;index=11'(offset>>5);frac=offset[4:0];
      lo=activation_lut(2'd3,index);
      hi=activation_lut(2'd3,index==1024?index:index+1'b1);
     end
    end
    base1[l]<=lo;delta1[l]<=$signed({hi[15],hi})-$signed({lo[15],lo});frac1[l]<=frac;
    u1[l]<=in_gate[16*l+:16];u2[l]<=u1[l];
    interpolation=delta1[l]*$signed({1'b0,frac1[l]});
    value=$signed({{16{base1[l][15]}},base1[l]})+rne({{9{interpolation[22]}},interpolation},5'd5);
    f2[l]<=value[15:0];
    product3[l]<=f2[l]*u2[l];f3[l]<=f2[l];
    rounded=g3?rne(product3[l],sig3?5'd14:5'd10):$signed({{16{f3[l][15]}},f3[l]});
    if(rounded>32767)begin rounded=32767;clip=1;end
    else if(rounded< -32768)begin rounded=-32768;clip=1;end
    out_data[16*l+:16]<=e3?16'd0:rounded[15:0];
   end
   out_saturated<=!e3&&clip;
  end
 end
endmodule
