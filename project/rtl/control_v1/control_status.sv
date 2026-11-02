// Fixed physical owner of system error aggregation; sticky until system reset.
module control_status(
 input wire clk,reset,input wire [6:0] queue_error,
 input wire dma_error,transaction_error,output reg protocol_error
);
 always @(posedge clk) begin
  if(reset) protocol_error<=1'b0;
  else protocol_error<=protocol_error || (|queue_error) || dma_error || transaction_error;
 end
endmodule
