// Exactly 1024x128 standard-cell payload bits and one response holding register.
// Retire/refill share an edge; there is still only one access per clock.
// Reset abandons the response but never clears payload. Initialize before read.
module block_v1_s16k(input wire clk,reset,req,wr,input wire [9:0] addr,
 input wire [127:0] din,output wire ready,output reg valid,input wire take,output reg [127:0] dout);
 reg [127:0] words[0:1023];
 assign ready=!reset&&(!valid||take);
 always @(posedge clk)begin
  if(reset)begin valid<=0;dout<=0;end
  else if(req&&ready)begin
   valid<=1;
   if(wr)begin words[addr]<=din;dout<=0;end
   else dout<=words[addr];
  end else if(valid&&take)valid<=0;
 end
endmodule
