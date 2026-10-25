module wide_test104(input wire clk,reset,req,cancel,input wire signed [63:0] a,input wire signed [31:0] b,input wire hold,output wire ready,busy,valid,input wire take,output wire signed [63:0] value,output wire error,output wire [31:0] grants);
 wire mr,mready,mvalid,mt;wire signed [31:0] ma,mb;wire signed [63:0] my;wire x,y;wire signed [63:0] z;wire [31:0] a0,a1,a2,a3;
 wide104 dut(clk,reset,req,cancel,a,b,ready,busy,valid,take,value,error,mr,ma,mb,mready,mvalid,mt,my);
 mul84 #(1) service(clk,reset,hold,mr,ma,mb,mready,mvalid,mt,my,1'b0,32'sd0,32'sd0,x,y,1'b1,z,grants,a0,a1,a2,a3);
endmodule
