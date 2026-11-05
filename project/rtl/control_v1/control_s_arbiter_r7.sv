// Fixed named physical configuration of the exact PR168 core.
module control_s_arbiter_r7 #(parameter integer CLIENTS=7)(
input wire clk,reset,input wire [CLIENTS-1:0] req,wr,input wire [CLIENTS*10-1:0] addr,input wire [CLIENTS*128-1:0] din,
 output wire [CLIENTS-1:0] ready,valid,input wire [CLIENTS-1:0] take,output wire [127:0] dout,
 output wire s_req,s_wr,output wire [9:0] s_addr,output wire [127:0] s_din,
 input wire s_ready,s_valid,output wire s_take,input wire [127:0] s_dout
);
 control_s_arbiter #(.CLIENTS(CLIENTS)) implementation(.clk(clk),.reset(reset),.req(req),.wr(wr),.addr(addr),.din(din),.ready(ready),.valid(valid),.take(take),.dout(dout),.s_req(s_req),.s_wr(s_wr),.s_addr(s_addr),.s_din(s_din),.s_ready(s_ready),.s_valid(s_valid),.s_take(s_take),.s_dout(s_dout));
endmodule
