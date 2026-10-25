// Adapted from Issue76 byte_core: same byte arithmetic, no wide data ALU.
module byte_alu(input wire clk, reset, input wire [7:0] request,
 input wire [31:0] opcode, input wire [63:0] a,b,c,
 output reg [7:0] response, output reg [63:0] lo,hi);
 integer i; reg [8:0] t; reg signed [15:0] p;
 reg [63:0] nl,nh;
 always @* begin
  nl=0; nh=0; t=0; p=0;
  for(integer k=0;k<8;k=k+1) begin
   case(opcode[4*k+:4])
   0,11: nl[8*k+:8]=a[8*k+:8];
   1: begin t={1'b0,a[8*k+:8]}+{1'b0,b[8*k+:8]}+c[8*k];nl[8*k+:8]=t[7:0];nh[8*k+:8]={7'b0,t[8]};end
   2: begin t={1'b0,a[8*k+:8]}-{1'b0,b[8*k+:8]}-c[8*k];nl[8*k+:8]=t[7:0];nh[8*k+:8]={7'b0,({1'b0,a[8*k+:8]}<({1'b0,b[8*k+:8]}+c[8*k]))};end
   3: begin p=$signed(a[8*k+:8])*$signed(b[8*k+:8]);nl[8*k+:8]=p[7:0];nh[8*k+:8]=p[15:8];end
   4: nl[8*k+:8]=b[8*k+:8]<8 ? a[8*k+:8]<<b[8*k+:3] : 8'b0;
   5: nl[8*k+:8]=b[8*k+:8]<8 ? a[8*k+:8]>>b[8*k+:3] : 8'b0;
   6: nl[8*k+:8]=a[8*k+:8]|b[8*k+:8];
   7: nl[8*k+:8]=a[8*k+:8]&b[8*k+:8];
   8: nl[8*k+:8]=a[8*k+:8]^b[8*k+:8];
   9: begin nl[8*k+:8]={7'b0,a[8*k+:8]<b[8*k+:8]};nh[8*k+:8]={7'b0,a[8*k+:8]==b[8*k+:8]};end
   10: nl[8*k+:8]=c[8*k] ? a[8*k+:8] : b[8*k+:8];
   default: begin nl[8*k+:8]=0;nh[8*k+:8]=0;end
   endcase
  end
 end
 always @(posedge clk) begin
  if(reset) begin response<=0;lo<=0;hi<=0;end
  else begin response<=request;for(i=0;i<8;i=i+1)if(request[i])begin lo[8*i+:8]<=nl[8*i+:8];hi[8*i+:8]<=nh[8*i+:8];end end
 end
endmodule
