`timescale 1ns/1ps
`include "counts.vh"
module tb_scale;
 reg clk; always #5 clk=~clk;
 reg reset, in_valid, out_ready;
 wire in_ready,out_valid,out_error;
 reg [31:0] in_tag;
 reg [3:0] in_n;
 reg in_first,in_final;
 reg [5:0] in_a_shift;
 reg [255:0] in_partial,in_previous,in_bias;
 reg [127:0] in_scale_fp16;
 wire [31:0] out_tag; wire [255:0] out_data;
 reg [1196:0] vectors [0:`SCALE_COUNT-1];
 integer sent,received,cycle;
 reg held; reg [288:0] held_value;
 scale_group_s32 dut(.*);
 initial begin
  clk=0; reset=1; in_valid=0; out_ready=0;
  sent=0; received=0; cycle=0; held=0; held_value=0;
  $readmemh("scale.hex",vectors);
  repeat(3) @(negedge clk); reset=0;
  // A reset must cancel a response held by backpressure.
  in_valid=1; in_tag=32'hdeadcafe; in_n=1; in_first=1; in_final=1;
  in_a_shift=0; in_partial=0; in_scale_fp16={8{16'h3c00}};
  in_previous=0; in_bias=0;
  @(posedge clk); @(negedge clk); in_valid=0;
  repeat(2) @(negedge clk);
  if(!out_valid) $fatal(1,"scale reset setup did not produce held response");
  reset=1; repeat(2) @(negedge clk); reset=0;
  if(out_valid) $fatal(1,"scale reset did not flush output");
  while(received<`SCALE_COUNT && cycle<`SCALE_COUNT*30) begin
   @(negedge clk);
   out_ready=(cycle%11<7);
   if(!in_valid || in_ready) in_valid=sent<`SCALE_COUNT && cycle%7!=0;
   if(sent<`SCALE_COUNT)
    {in_tag,in_n,in_first,in_final,in_a_shift,in_partial,in_scale_fp16,in_previous,in_bias}=vectors[sent][1196:257];
   @(posedge clk);
   if(held && (!out_valid || {out_tag,out_data,out_error}!==held_value)) $fatal(1,"scale output changed under backpressure");
   held=out_valid&&!out_ready; held_value={out_tag,out_data,out_error};
   if(in_valid&&in_ready) sent=sent+1;
   if(out_valid&&out_ready) begin
    if(out_tag!==received || {out_data,out_error}!==vectors[received][256:0])
     $fatal(1,"scale mismatch vector=%0d got=%h/%b expected=%h",received,out_data,out_error,vectors[received][256:0]);
    received=received+1;
   end
   cycle=cycle+1;
  end
  if(received!=`SCALE_COUNT) $fatal(1,"scale timeout");
  $display("PASS scale %0d vectors %0d cycles",received,cycle); $finish;
 end
endmodule
