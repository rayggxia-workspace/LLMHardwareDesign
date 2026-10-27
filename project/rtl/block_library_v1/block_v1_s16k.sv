// Exactly one existing 1024x128 single-1RW synchronous store.
module block_v1_s16k(input wire clk,reset,req,wr,input wire [9:0] addr,
 input wire [127:0] din,output wire ready,valid,input wire take,output wire [127:0] dout);
 store82 memory(clk,reset,req,wr,addr,din,ready,valid,take,dout);
endmodule
