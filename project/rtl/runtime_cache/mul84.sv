// Two finite response slots; one shared or two dedicated signed32 multipliers.
module mul84 #(parameter SHARE=0)(input wire clk,reset,hold,
 input wire r0,input wire signed [31:0] a0,b0,output wire ready0,output reg v0,input wire take0,output reg signed [63:0] y0,
 input wire r1,input wire signed [31:0] a1,b1,output wire ready1,output reg v1,input wire take1,output reg signed [63:0] y1,
 output reg [31:0] grants0,grants1,wait0,wait1,contested);
 reg turn;wire eligible0=r0&&!v0,eligible1=r1&&!v1;
 wire grant0=!hold&&!v0&&(!SHARE||!eligible1||!turn);
 wire grant1=!hold&&!v1&&(!SHARE||!eligible0||turn);
 assign ready0=grant0;assign ready1=grant1;
 wire signed [63:0] p0,p1;
 generate if(SHARE)begin:SHARED
  wire select1=eligible1&&(!eligible0||turn);
  wire signed [31:0] a=select1?a1:a0,b=select1?b1:b0;
  wire signed [63:0] p=a*b;assign p0=p;assign p1=p;
 end else begin:DEDICATED
  assign p0=a0*b0;assign p1=a1*b1;
 end endgenerate
 always @(posedge clk)begin
  if(reset)begin v0<=0;v1<=0;y0<=0;y1<=0;turn<=0;grants0<=0;grants1<=0;wait0<=0;wait1<=0;contested<=0;end
  else begin
   if(v0&&take0)v0<=0;if(v1&&take1)v1<=0;
   if(r0&&!ready0)wait0<=wait0+1;if(r1&&!ready1)wait1<=wait1+1;
   if(eligible0&&eligible1)contested<=contested+1;
   if(r0&&ready0)begin y0<=p0;v0<=1;grants0<=grants0+1;turn<=1;end
   if(r1&&ready1)begin y1<=p1;v1<=1;grants1<=grants1+1;turn<=0;end
  end
 end
endmodule
