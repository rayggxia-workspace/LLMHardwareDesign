// All leaf resets have the same one-clock latency. Replicated state is an
// intentional physical fanout boundary; acceptance must count all 25 DFFs.
module control_reset_distribution(
 input wire clk,reset_in,output wire [24:0] reset_out
);
 (* keep = 1, dont_touch = 1 *) reg [24:0] reset_q;
 always @(posedge clk) reset_q<={25{reset_in}};
 assign reset_out=reset_q;
endmodule
