// One reset state bit, with 25 explicit independent physical output drivers.
// Every leaf observes the same one-clock latency; this is not asynchronous.
module control_reset_distribution(
 input wire clk,reset_in,output wire [24:0] reset_out
);
 reg reset_q;
 always @(posedge clk) reset_q<=reset_in;
 for(genvar branch=0;branch<25;branch=branch+1) begin: distribution
  (* keep = 1, dont_touch = 1 *) BUF_X16 driver(.A(reset_q),.Z(reset_out[branch]));
 end
endmodule
