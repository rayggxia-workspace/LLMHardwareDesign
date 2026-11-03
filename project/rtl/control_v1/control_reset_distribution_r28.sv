// Fixed named physical configuration of the exact PR168 core.
module control_reset_distribution_r28 #(parameter integer BRANCHES=28)(
input wire clk,reset_in,output wire [BRANCHES-1:0] reset_out
);
 control_reset_distribution #(.BRANCHES(BRANCHES)) implementation(.clk(clk),.reset_in(reset_in),.reset_out(reset_out));
endmodule
