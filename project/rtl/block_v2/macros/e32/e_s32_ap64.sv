`timescale 1ns/1ps
// Compact E32 physical aperture. Each S128 operand becomes two ordered
// 64b beats. Metadata is sampled on the low beat; result flags cover both.
// No extra result buffer: the original core holds its 128b result.
module e_s32_ap64(
 input wire clk,reset,
 input wire in_valid,output wire in_ready,input wire [63:0] in_data,
 input wire [3:0] in_op,in_mask,input wire [7:0] in_shift,input wire [2:0] in_minus,
 output wire out_valid,input wire out_ready,output wire [63:0] out_data,
 output wire [3:0] out_clipped,output wire out_error
);
 reg in_high,out_high;
 reg [63:0] in_low;
 reg [3:0] held_op,held_mask;
 reg [7:0] held_shift;
 reg [2:0] held_minus;
 wire core_in_ready,core_out_valid;
 wire [127:0] core_out;
 assign in_ready=!reset&&core_in_ready;
 assign out_valid=!reset&&core_out_valid;
 assign out_data=out_high ? core_out[127:64] : core_out[63:0];
 e_s32_native core(.clk,.reset,.in_valid(in_valid&&in_high),.in_ready(core_in_ready),
  .in_op(held_op),.in_mask(held_mask),.in_shift(held_shift),.in_minus(held_minus),
  .in_data({in_data,in_low}),.out_valid(core_out_valid),.out_ready(out_ready&&out_high),
  .out_data(core_out),.out_clipped,.out_error);
 always @(posedge clk)begin
  if(reset)begin
   in_high<=0;out_high<=0;in_low<=0;held_op<=0;held_mask<=0;held_shift<=0;held_minus<=0;
  end else begin
   if(in_valid&&in_ready)begin
    in_high<=!in_high;
    if(!in_high)begin in_low<=in_data;held_op<=in_op;held_mask<=in_mask;held_shift<=in_shift;held_minus<=in_minus;end
   end
   if(out_valid&&out_ready)out_high<=!out_high;
  end
 end
endmodule
