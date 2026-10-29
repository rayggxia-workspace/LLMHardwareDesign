// Exactly 4 x 256 x 128 bits = 16KiB of standard-cell payload storage.
// Each bank is single 1RW. Wide reads occupy ALL banks; narrow access loses
// arbitration that cycle. Distinct finite response registers hold under stall.
module block_feed_s16k (
 input wire clk,reset,
 input wire req,wr,input wire [9:0] addr,input wire [127:0] din,
 output wire ready,output reg valid,input wire take,output reg [127:0] dout,
 input wire wide_req,input wire [7:0] wide_addr,output wire wide_ready,
 output reg wide_valid,input wire wide_take,output reg [511:0] wide_dout
);
 reg [127:0] bank0[0:255],bank1[0:255],bank2[0:255],bank3[0:255];
 assign wide_ready=!reset&&(!wide_valid||wide_take);
 wire wide_fire=wide_req&&wide_ready;
 assign ready=!reset&&(!valid||take)&&!wide_fire;
 always @(posedge clk)begin
  if(reset)begin valid<=0;wide_valid<=0;dout<=0;wide_dout<=0;end
  else begin
   if(valid&&take)valid<=0;
   if(wide_valid&&wide_take)wide_valid<=0;
   if(wide_fire)begin
    wide_valid<=1;
    wide_dout<={bank3[wide_addr],bank2[wide_addr],bank1[wide_addr],bank0[wide_addr]};
   end else if(req&&ready)begin
    valid<=1;
    case(addr[1:0])
     0:begin dout<=bank0[addr[9:2]];if(wr)bank0[addr[9:2]]<=din;end
     1:begin dout<=bank1[addr[9:2]];if(wr)bank1[addr[9:2]]<=din;end
     2:begin dout<=bank2[addr[9:2]];if(wr)bank2[addr[9:2]]<=din;end
     3:begin dout<=bank3[addr[9:2]];if(wr)bank3[addr[9:2]]<=din;end
    endcase
    // Match the old S write-ack payload, not read-before-write bytes.
    if(wr)dout<=din;
   end
  end
 end
endmodule
