// Evaluation-only two-stream rendezvous. Two 32-bit slots per input (16 B total).
// No arithmetic or scale conversion is added. Both inputs are native S16/Q5.10.
// gated is a burst configuration: hold it until input FIFOs and G are drained.
module bn_g_bridge(
 input wire clk,reset,gated,
 input wire x_valid,output wire x_ready,input wire [31:0] x_data,
 input wire u_valid,output wire u_ready,input wire [31:0] u_data,
 output wire out_valid,input wire out_ready,output wire [31:0] out_data,
 output wire out_error,out_saturated,
 output reg [1:0] x_level,u_level
);
 reg [31:0] x_fifo[0:1],u_fifo[0:1];
 reg xr,xw,ur,uw;
 wire g_ready;
 wire pop=(x_level!=0)&&(u_level!=0)&&g_ready;
 wire push_x=x_valid&&x_ready,push_u=u_valid&&u_ready;
 assign x_ready=!reset&&((x_level<2)||pop);
 assign u_ready=!reset&&((u_level<2)||pop);
 block_v2_g g(.clk(clk),.reset(reset),.in_valid((x_level!=0)&&(u_level!=0)),
  .in_ready(g_ready),.in_fn(3'd0),.in_gated(gated),.in_x(x_fifo[xr]),.in_gate(u_fifo[ur]),
  .out_valid(out_valid),.out_ready(out_ready),.out_data(out_data),.out_error(out_error),.out_saturated(out_saturated));
 always @(posedge clk)begin
  if(reset)begin xr<=0;xw<=0;ur<=0;uw<=0;x_level<=0;u_level<=0;end
  else begin
   if(push_x)begin x_fifo[xw]<=x_data;xw<=!xw;end
   if(push_u)begin u_fifo[uw]<=u_data;uw<=!uw;end
   if(pop)begin xr<=!xr;ur<=!ur;end
   case({push_x,pop})2'b10:x_level<=x_level+1'b1;2'b01:x_level<=x_level-1'b1;default:begin end endcase
   case({push_u,pop})2'b10:u_level<=u_level+1'b1;2'b01:u_level<=u_level-1'b1;default:begin end endcase
  end
 end
endmodule
