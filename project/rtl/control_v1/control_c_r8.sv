// Fixed named physical configuration of the exact PR168 core.
module control_c_r8 #(parameter integer ENDPOINTS=8)(
input wire clk,reset,
 input wire cfg_valid,output wire cfg_ready,input wire cfg_write,
 input wire [15:0] cfg_addr,input wire [31:0] cfg_wdata,input wire [3:0] cfg_wstrb,
 output wire cfg_rsp_valid,input wire cfg_rsp_ready,output wire [31:0] cfg_rdata,output wire cfg_error,
 output wire task_valid,input wire task_ready,output wire [31:0] task_data,
 output wire [3:0] task_endpoint,output wire task_last,
 input wire done_valid,output wire done_ready,input wire [31:0] done_data,input wire done_last,
 output wire busy,output wire ended,output wire [3:0] fault,output wire [7:0] error_pc
);
 control_c #(.ENDPOINTS(ENDPOINTS)) implementation(.clk(clk),.reset(reset),.cfg_valid(cfg_valid),.cfg_ready(cfg_ready),.cfg_write(cfg_write),.cfg_addr(cfg_addr),.cfg_wdata(cfg_wdata),.cfg_wstrb(cfg_wstrb),.cfg_rsp_valid(cfg_rsp_valid),.cfg_rsp_ready(cfg_rsp_ready),.cfg_rdata(cfg_rdata),.cfg_error(cfg_error),.task_valid(task_valid),.task_ready(task_ready),.task_data(task_data),.task_endpoint(task_endpoint),.task_last(task_last),.done_valid(done_valid),.done_ready(done_ready),.done_data(done_data),.done_last(done_last),.busy(busy),.ended(ended),.fault(fault),.error_pc(error_pc));
endmodule
