(* blackbox *) module s_sram_256x128_freepdk45(input clk0,csb0,web0,input [7:0] addr0,input [127:0] din0,output [127:0] dout0); endmodule
module block_feed_s_macro_sram(input clk,csb,web,input [7:0] addr,input [127:0] din,output [127:0] dout,output q);
wire [127:0] r0,r1,r2,r3; wire bit0;
BUF_X2 same(.A(addr[0]),.Z(bit0));
s_sram_256x128_freepdk45 b0(.clk0(clk),.csb0(csb),.web0(web),.addr0({addr[7:1],bit0}),.din0(din),.dout0(r0));
s_sram_256x128_freepdk45 b1(.clk0(clk),.csb0(csb),.web0(web),.addr0(addr),.din0(din),.dout0(r1));
s_sram_256x128_freepdk45 b2(.clk0(clk),.csb0(csb),.web0(web),.addr0(addr),.din0(din),.dout0(r2));
s_sram_256x128_freepdk45 b3(.clk0(clk),.csb0(csb),.web0(web),.addr0(addr),.din0(din),.dout0(r3));
assign dout=r0; DFF_X1 ff(.CK(clk),.D(r0[0]),.Q(q)); endmodule
