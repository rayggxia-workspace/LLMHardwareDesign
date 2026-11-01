// Test-only port harness. S and V are unchanged. Data passes through their
// existing response registers; no extra payload RAM/FIFO exists in this top.
module sv_workspace_bench(
 input wire clk,reset,cmd_valid,output wire cmd_ready,
 input wire [3:0] cmd_op,input wire [7:0] cmd_index,input wire [127:0] cmd_data,
 output wire rsp_valid,input wire rsp_ready,output wire [127:0] rsp_data,
 output wire rsp_error,rsp_saturated,busy,
 input wire s_req,s_wr,input wire [9:0] s_addr,input wire [127:0] s_din,
 output wire s_ready,s_valid,input wire s_take,output wire [127:0] s_dout
);
 block_v1_v v(clk,reset,cmd_valid,cmd_ready,cmd_op,cmd_index,cmd_data,
  rsp_valid,rsp_ready,rsp_data,rsp_error,rsp_saturated,busy);
 block_v1_s16k s(clk,reset,s_req,s_wr,s_addr,s_din,s_ready,s_valid,s_take,s_dout);
endmodule
