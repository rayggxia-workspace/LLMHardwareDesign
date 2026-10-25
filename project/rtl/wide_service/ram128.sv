// One128-bit read OR write. No byte mask. Response must retire before reuse.
module ram128(input wire clk,reset,input wire req,input wire wr,
 input wire [4:0] addr,input wire [127:0] din,output wire ready,
 output reg valid,input wire take,output reg [127:0] dout);
 reg [127:0] words[0:31];
 assign ready=!valid;
 always @(posedge clk)begin
  if(reset)begin valid<=0;dout<=0;end
  else if(req&&ready)begin valid<=1;if(wr)begin words[addr]<=din;dout<=0;end else dout<=words[addr];end
  else if(valid&&take)valid<=0;
 end
endmodule
module lut32(input wire clk,reset,input wire req,input wire [14:0] addr,
 output reg valid,output reg [31:0] data);
 reg [31:0] words[0:32767];reg [31:0] q0,q1;reg v0,v1;
 initial $readmemh("rom.hex",words);
 always @(posedge clk)begin
  if(reset)begin v0<=0;v1<=0;valid<=0;q0<=0;q1<=0;data<=0;end
  else begin v0<=req;v1<=v0;valid<=v1;if(req)q0<=words[addr];q1<=q0;data<=q1;end
 end
endmodule
