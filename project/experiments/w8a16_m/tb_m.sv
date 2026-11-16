`timescale 1ns/1ps
`include "counts.vh"
module tb_m;
 reg clk; always #5 clk=~clk;
 reg reset,in_valid,out_ready;
 reg in_first,in_last;
 reg [31:0] in_tag;
 reg [7:0] in_group_k,in_offset;
 reg [4:0] in_k;
 reg [3:0] in_n;
 reg [255:0] in_a;
 reg [1023:0] in_w;
 wire in_ready,out_valid,out_error;
 wire [31:0] out_tag; wire [3:0] out_n; wire [255:0] out_data;
 reg [1338:0] inputs [0:`M_IN_COUNT-1];
 reg [292:0] expected [0:`M_OUT_COUNT-1];
 integer sent,received,cycle;
 reg held; reg [292:0] held_value;
 m_group_s32 dut(.*);
 initial begin
  clk=0; reset=1; in_valid=0; out_ready=0;
  sent=0; received=0; cycle=0; held=0; held_value=0;
  $readmemh("m-in.hex",inputs); $readmemh("m-out.hex",expected);
  repeat(3) @(negedge clk); reset=0;
  // Flush a live raw group, then ensure a fresh first starts cleanly.
  in_valid=1; in_first=1; in_last=0; in_tag=32'hdeadcafe;
  in_group_k=128; in_offset=0; in_k=16; in_n=1; in_a=0; in_w=0;
  @(posedge clk); @(negedge clk); in_valid=0;
  repeat(4) @(negedge clk);
  reset=1; repeat(2) @(negedge clk); reset=0;
  if(out_valid) $fatal(1,"M reset did not flush output");
  while(received<`M_OUT_COUNT && cycle<`M_IN_COUNT*30) begin
   @(negedge clk);
   out_ready=(cycle%13<8);
   if(!in_valid || in_ready) in_valid=sent<`M_IN_COUNT && cycle%5!=0;
   if(sent<`M_IN_COUNT)
    {in_first,in_last,in_tag,in_group_k,in_offset,in_k,in_n,in_a,in_w}=inputs[sent];
   @(posedge clk);
   if(held && (!out_valid || {out_tag,out_n,out_data,out_error}!==held_value)) $fatal(1,"M output changed under backpressure");
   held=out_valid&&!out_ready; held_value={out_tag,out_n,out_data,out_error};
   if(in_valid&&in_ready) sent=sent+1;
   if(out_valid&&out_ready) begin
    if({out_tag,out_n,out_data,out_error}!==expected[received])
     $fatal(1,"M mismatch response=%0d got=%h expected=%h",received,{out_tag,out_n,out_data,out_error},expected[received]);
    received=received+1;
   end
   cycle=cycle+1;
  end
  if(received!=`M_OUT_COUNT) $fatal(1,"M timeout");
  $display("PASS M %0d beats %0d responses %0d cycles",sent,received,cycle); $finish;
 end
endmodule
