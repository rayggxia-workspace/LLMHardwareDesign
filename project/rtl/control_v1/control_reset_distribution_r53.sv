// One registered reset state;28 original leaves and25 independent Link8 banks.
module control_reset_distribution_r53 #(parameter integer BRANCHES=53)(
 input wire clk,reset_in,output wire [BRANCHES-1:0] reset_out
);
 control_reset_distribution #(.BRANCHES(BRANCHES)) implementation(.clk(clk),.reset_in(reset_in),.reset_out(reset_out));
endmodule
