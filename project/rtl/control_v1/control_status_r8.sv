// Fixed named physical configuration of the exact PR168 core.
module control_status_r8 #(parameter integer QUEUES=8)(
input wire clk,reset,input wire [QUEUES-1:0] queue_error,
 input wire dma_error,transaction_error,output wire protocol_error
);
 control_status #(.QUEUES(QUEUES)) implementation(.clk(clk),.reset(reset),.queue_error(queue_error),.dma_error(dma_error),.transaction_error(transaction_error),.protocol_error(protocol_error));
endmodule
