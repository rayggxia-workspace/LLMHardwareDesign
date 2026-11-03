// Functional timing stand-in ONLY. Never include in a physical source list.
// Models OpenRAM 1RW: rising-edge command capture, falling-edge read/write.
// It does not model access delay, setup/hold, power or a physical SRAM layout.
`ifndef S_SRAM_SIM
 SRAM_SIMULATION_MODEL_REQUIRES_EXPLICIT_S_SRAM_SIM_DEFINE invalid_build();
`else
module s_sram_256x128_freepdk45(
 input wire clk0,csb0,web0,input wire [7:0] addr0,
 input wire [127:0] din0,output reg [127:0] dout0
);
 reg csb_q,web_q;reg [7:0] addr_q;reg [127:0] din_q;
 reg [127:0] cells[0:255];
 // One simulation process models both phases; this is not synthesizable RTL.
 always @(posedge clk0 or negedge clk0)begin
  if(clk0)begin
   csb_q<=csb0;web_q<=web0;addr_q<=addr0;din_q<=din0;
   dout0<=128'bx;
  end else if(!csb_q)begin
   if(!web_q)cells[addr_q]<=din_q;
   else dout0<=cells[addr_q];
  end
 end
endmodule
`endif
