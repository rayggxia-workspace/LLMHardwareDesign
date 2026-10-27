// Two parallel three-stage, II=1 function lanes; Q16.16 input/output.
// EXP domain [-16,0]; positive EXP is an error. Other domains/extensions
// and independent coefficient/error evidence: docs/BLOCK_LIBRARY_V1.md.
module block_v1_v_function(
 input wire clk,reset,in_valid, input wire [2:0] fn,
 input wire signed [31:0] x0,x1,
 output reg out_valid,output reg signed [31:0] y0,y1,output reg error
);
 `include "block_v1_v_tables.svh"
 reg valid1,valid2,error1,error2;
 reg signed [31:0] base1[0:1],base2[0:1];
 reg signed [32:0] delta1[0:1];reg [10:0] frac1[0:1];
 reg [3:0] shift1,shift2;
 reg signed [44:0] product2[0:1];
 reg signed [31:0] xv;reg signed [32:0] offset;
 reg [11:0] index;reg [10:0] frac;
 reg signed [31:0] lo,hi;
 reg signed [44:0] quotient;reg [44:0] remn,half;
 reg signed [45:0] total;
 integer l;
 always @(posedge clk)begin
  if(reset)begin valid1<=0;valid2<=0;out_valid<=0;error1<=0;error2<=0;error<=0;y0<=0;y1<=0;end
  else begin
   valid1<=in_valid;valid2<=valid1;out_valid<=valid2;
   error1<=fn>4||(fn==0&&(x0>0||x1>0));error2<=error1;error<=error2;
   shift1<=fn==0?9:11;shift2<=shift1;
   for(l=0;l<2;l=l+1)begin
    xv=l==0?x0:x1;offset=0;index=0;frac=0;lo=0;hi=0;
    if(fn==0)begin
     if(xv<=-32'sd1048576)begin lo=v_lut(0,0);hi=lo;end
     else if(xv>=0)begin lo=32'sd65536;hi=lo;end
     else begin offset=$signed({xv[31],xv})+33'sd1048576;index=offset>>9;frac={2'b0,offset[8:0]};lo=v_lut(fn,index);hi=v_lut(fn,index+1'b1);end
    end else if(fn<=3)begin
     if(xv<=-32'sd524288)begin lo=xv==-32'sd524288 ? v_lut(fn,0):32'sd0;hi=lo;end
     else if(xv>=32'sd524288)begin lo=xv==32'sd524288 ? v_lut(fn,12'd512):(fn==1?32'sd65536:xv);hi=lo;end
     else begin offset=$signed({xv[31],xv})+33'sd524288;index=offset>>11;frac=offset[10:0];lo=v_lut(fn,index);hi=v_lut(fn,index+1'b1);end
    end else if(fn==4)begin
     if(xv<=-32'sd1048576)begin lo=xv==-32'sd1048576 ? v_lut(fn,0):32'sd0;hi=lo;end
     else if(xv>=32'sd1048576)begin lo=xv==32'sd1048576 ? v_lut(fn,12'd1024):xv;hi=lo;end
     else begin offset=$signed({xv[31],xv})+33'sd1048576;index=offset>>11;frac=offset[10:0];lo=v_lut(fn,index);hi=v_lut(fn,index+1'b1);end
    end
    base1[l]<=lo;delta1[l]<=$signed({hi[31],hi})-$signed({lo[31],lo});frac1[l]<=frac;
    base2[l]<=base1[l];product2[l]<=delta1[l]*$signed({1'b0,frac1[l]});
    quotient=product2[l]>>>shift2;remn=$unsigned(product2[l])&((45'd1<<shift2)-1);half=45'd1<<(shift2-1);
    total=$signed({{14{base2[l][31]}},base2[l]})+quotient+((remn>half)||((remn==half)&&quotient[0]));
    if(l==0)y0<=total[31:0];else y1<=total[31:0];
   end
  end
 end
endmodule
