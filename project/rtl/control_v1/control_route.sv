// Fixed control topology: shared command flit bus and seven local valid lines.
// Completion ownership stays locked for both flits, including backpressure.
module control_route #(parameter integer ENDPOINTS=7)(
 input wire clk,reset,input wire task_valid,output wire task_ready,input wire [3:0] task_endpoint,
 output wire [ENDPOINTS-1:0] cmd_valid,input wire [ENDPOINTS-1:0] cmd_ready,
 input wire [ENDPOINTS-1:0] endpoint_valid,output wire [ENDPOINTS-1:0] endpoint_ready,input wire [ENDPOINTS*32-1:0] endpoint_data,input wire [ENDPOINTS-1:0] endpoint_last,
 output wire done_valid,input wire done_ready,output wire [31:0] done_data,output wire done_last
);
 reg [2:0] owner,next_owner;reg active,found;reg [2:0] selected;
 always @* begin
  found=0;selected=0;
  for(integer k=0;k<ENDPOINTS;k=k+1) if(!found && endpoint_valid[(32'(next_owner)+k)%ENDPOINTS]) begin found=1;selected=3'((32'(next_owner)+k)%ENDPOINTS);end
 end
 assign cmd_valid=(32'(task_endpoint)<ENDPOINTS)?({{(ENDPOINTS-1){1'b0}},1'b1}<<task_endpoint)&{ENDPOINTS{task_valid}}:{ENDPOINTS{1'b0}};
 assign task_ready=32'(task_endpoint)<ENDPOINTS && cmd_ready[task_endpoint[2:0]];
 assign done_valid=active && endpoint_valid[owner];assign done_data=endpoint_data[owner*32+:32];assign done_last=endpoint_last[owner];
 assign endpoint_ready=active?({{(ENDPOINTS-1){1'b0}},1'b1}<<owner)&{ENDPOINTS{done_ready}}:{ENDPOINTS{1'b0}};
 always @(posedge clk) begin
  if(reset) begin owner<=0;next_owner<=0;active<=0;end
  else if(!active && found) begin owner<=selected;active<=1;end
  else if(done_valid && done_ready && done_last) begin active<=0;next_owner<=32'(owner)==ENDPOINTS-1?3'd0:owner+1;end
 end
endmodule
