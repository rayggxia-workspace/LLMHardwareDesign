// Eight combinational lanes with synchronous reset isolation. The single
// active bit belongs to this physical macro. There is no payload register,
// FIFO, completion state or extra data cycle after reset release.
module control_link8(
 input wire clk,reset,
 input wire [7:0] in_data,
 output wire [7:0] out_data
);
 reg active;
 always @(posedge clk) active<=!reset;
 assign out_data=in_data&{8{active}};
endmodule
