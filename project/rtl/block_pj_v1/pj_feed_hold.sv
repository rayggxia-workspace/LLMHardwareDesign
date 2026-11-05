// A one-credit feeder link. Withheld ready is independent of the sink.
module pj_feed_hold #(
 parameter WIDTH=1
)(
 input wire clk, reset,
 input wire src_valid, output wire src_ready, input wire [WIDTH-1:0] src_data,
 output reg dst_valid, input wire dst_ready, output reg [WIDTH-1:0] dst_data
);
 assign src_ready=!dst_valid;
 // A reset invalidates the slot. Its payload has no meaning while invalid.
 always @(posedge clk) if(src_valid && src_ready) dst_data<=src_data;
 always @(posedge clk) begin
  if(reset) dst_valid<=0;
  else if(src_valid && src_ready) dst_valid<=1;
  else if(dst_ready) dst_valid<=0;
 end
endmodule
