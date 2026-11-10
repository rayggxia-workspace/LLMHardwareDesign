`timescale 1ns/1ps
`include "counts.vh"
module tb_context;
 reg clk; always #5 clk=~clk;
 reg reset,cmd_valid,rsp_ready;
 wire cmd_ready,rsp_valid,rsp_error;
 reg [2:0] cmd_kind; reg [3:0] cmd_context;
 reg [127:0] cmd_owner; reg [31:0] cmd_tag;
 reg [15:0] cmd_full_k,cmd_k_offset;
 reg [7:0] cmd_group_k; reg [3:0] cmd_n;
 reg cmd_final; reg [5:0] cmd_a_shift;
 reg [255:0] cmd_partial,cmd_previous,cmd_bias;
 reg [127:0] cmd_scale_fp16;
 wire [2:0] rsp_kind; wire [3:0] rsp_context;
 wire [127:0] rsp_owner; wire [31:0] rsp_tag;
 wire [15:0] rsp_full_k; wire [7:0] rsp_group_k; wire [3:0] rsp_n;
 wire [15:0] rsp_next_k; wire rsp_final; wire [255:0] rsp_data;
 reg [`CONTEXT_WIDTH-1:0] vectors [0:`CONTEXT_COUNT-1];
 wire [`RESPONSE_WIDTH-1:0] response={rsp_kind,rsp_context,rsp_owner,rsp_tag,rsp_full_k,rsp_group_k,rsp_n,rsp_next_k,rsp_final,rsp_data,rsp_error};
 reg held; reg [`RESPONSE_WIDTH-1:0] held_value;
 integer sent,received,cycle,consecutive,peak_consecutive;
 projection_context_s32 dut(.*);
 initial begin
  clk=0;reset=1;cmd_valid=0;rsp_ready=0;sent=0;received=0;cycle=0;
  held=0;held_value=0;consecutive=0;peak_consecutive=0;
  $readmemh("context.hex",vectors);
  repeat(3) @(negedge clk); reset=0;
  // Create a held response, then reset must cancel both ownership and event.
  {cmd_kind,cmd_context,cmd_owner,cmd_tag,cmd_full_k,cmd_k_offset,cmd_group_k,cmd_n,cmd_final,cmd_a_shift,cmd_partial,cmd_previous,cmd_bias,cmd_scale_fp16}=vectors[0][`CONTEXT_WIDTH-1:`RESPONSE_WIDTH];
  cmd_valid=1;@(posedge clk);@(negedge clk);cmd_valid=0;
  repeat(2) @(negedge clk);
  if(!rsp_valid) $fatal(1,"reset setup response missing");
  reset=1;repeat(2) @(negedge clk);reset=0;
  if(rsp_valid) $fatal(1,"reset response leak");
  while(received<`CONTEXT_COUNT && cycle<`CONTEXT_COUNT*30) begin
   @(negedge clk);
   // First 1000 cycles continuously ready to expose same-slot RAW hazards.
   rsp_ready=cycle<1000 || cycle%13<8;
   if(!cmd_valid || cmd_ready) cmd_valid=sent<`CONTEXT_COUNT && (cycle<1000 || cycle%7!=0);
   if(sent<`CONTEXT_COUNT)
    {cmd_kind,cmd_context,cmd_owner,cmd_tag,cmd_full_k,cmd_k_offset,cmd_group_k,cmd_n,cmd_final,cmd_a_shift,cmd_partial,cmd_previous,cmd_bias,cmd_scale_fp16}=vectors[sent][`CONTEXT_WIDTH-1:`RESPONSE_WIDTH];
   @(posedge clk);
   if(held && (!rsp_valid || response!==held_value)) $fatal(1,"response changed under backpressure");
   held=rsp_valid&&!rsp_ready;held_value=response;
   if(cmd_valid&&cmd_ready) begin sent=sent+1;consecutive=consecutive+1;end
   else consecutive=0;
   if(consecutive>peak_consecutive) peak_consecutive=consecutive;
   if(rsp_valid&&rsp_ready) begin
    if(response!==vectors[received][`RESPONSE_WIDTH-1:0])
     $fatal(1,"context mismatch %0d actual=%h expected=%h",received,response,vectors[received][`RESPONSE_WIDTH-1:0]);
    received=received+1;
   end
   cycle=cycle+1;
  end
  if(received!=`CONTEXT_COUNT || peak_consecutive<64) $fatal(1,"timeout or missing continuous forwarding coverage");
  $display("PASS context %0d commands %0d cycles peak_consecutive=%0d",received,cycle,peak_consecutive);$finish;
 end
endmodule
