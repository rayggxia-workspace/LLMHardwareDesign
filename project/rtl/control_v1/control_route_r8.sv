// Fixed named physical configuration of the exact PR168 core.
module control_route_r8 #(parameter integer ENDPOINTS=8)(
input wire clk,reset,input wire task_valid,output wire task_ready,input wire [3:0] task_endpoint,
 output wire [ENDPOINTS-1:0] cmd_valid,input wire [ENDPOINTS-1:0] cmd_ready,
 input wire [ENDPOINTS-1:0] endpoint_valid,output wire [ENDPOINTS-1:0] endpoint_ready,input wire [ENDPOINTS*32-1:0] endpoint_data,input wire [ENDPOINTS-1:0] endpoint_last,
 output wire done_valid,input wire done_ready,output wire [31:0] done_data,output wire done_last
);
 control_route #(.ENDPOINTS(ENDPOINTS)) implementation(.clk(clk),.reset(reset),.task_valid(task_valid),.task_ready(task_ready),.task_endpoint(task_endpoint),.cmd_valid(cmd_valid),.cmd_ready(cmd_ready),.endpoint_valid(endpoint_valid),.endpoint_ready(endpoint_ready),.endpoint_data(endpoint_data),.endpoint_last(endpoint_last),.done_valid(done_valid),.done_ready(done_ready),.done_data(done_data),.done_last(done_last));
endmodule
