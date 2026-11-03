// Issue151 H2: one accepted completion, one stable public terminal tuple.
// No fallthrough or simultaneous dequeue/enqueue. This is not a rollback log.
module block_w5_completion_hold(
 input wire clk,reset,
 input wire in_valid,output wire in_ready,
 input wire in_error,in_saturated,input wire [8:0] in_words,
 input wire [31:0] in_generation,
 output wire out_valid,input wire out_ready,
 output reg out_error,out_saturated,out_partial,
 output reg [8:0] out_words,output reg [31:0] out_generation
);
 reg occupied;
 assign in_ready=!reset&&!occupied;
 assign out_valid=!reset&&occupied;
 always @(posedge clk)begin
  if(reset)begin
   occupied<=0;out_error<=0;out_saturated<=0;out_partial<=0;out_words<=0;out_generation<=0;
  end else if(occupied)begin
   if(out_ready)occupied<=0;
  end else if(in_valid&&in_ready)begin
   occupied<=1;out_error<=in_error;out_saturated<=in_saturated;
   out_partial<=in_error&&(in_words!=0);out_words<=in_words;out_generation<=in_generation;
  end
 end
endmodule
