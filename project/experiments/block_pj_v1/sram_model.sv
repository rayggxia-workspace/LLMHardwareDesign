// Digital bank model for RTL transaction tests. The physical view is independently qualified.
module s_sram_256x128_freepdk45 (
 input wire clk0, csb0, web0, input wire [7:0] addr0,
 input wire [127:0] din0, output reg [127:0] dout0
);
 reg [127:0] words [0:255];
 reg selected, write_word;
 reg [7:0] address;
 reg [127:0] data;
 always @(posedge clk0) begin
  selected<=!csb0; write_word<=!web0; address<=addr0; data<=din0;
 end
 always @(negedge clk0) if(selected) begin
  if(write_word) words[address]<=data;
  else dout0<=words[address];
 end
endmodule
