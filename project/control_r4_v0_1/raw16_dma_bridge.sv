`timescale 1ns/1ps
// Single-word bounded provider. A 16-bit DMA tag indexes a full saved identity;
// it is never a truncated job/epoch/task. Exhaustion requires cohort reset.
module raw16_dma_bridge #(parameter [15:0] TAG_LIMIT=16'hffff)(
 input wire clk,reset,admit,protocol_error,
 input wire req,wr,input wire [9:0] address,input wire [127:0] data,
 input wire [140:0] context_i,input wire [39:0] external_read,external_write,
 output wire ready,output wire valid,input wire take,output wire [127:0] result,
 output wire desc_valid,input wire desc_ready,output wire desc_write,
 output wire [39:0] desc_address,output wire [9:0] desc_local,
 output wire [10:0] desc_words,output wire [15:0] desc_tag,
 input wire complete_valid,output wire complete_ready,input wire [1:0] complete_status,
 input wire [10:0] complete_words,input wire [15:0] complete_tag,
 input wire native_valid,native_take,native_write,input wire [127:0] native_result,
 output wire [140:0] context_o,output reg poison,output wire busy
);
 localparam [1:0] IDLE=0,DESC=1,WAITING=2,RESULT=3;
 reg [1:0] state;reg saved_write,observed,exhausted;
 reg [9:0] saved_address;reg [39:0] saved_external;
 reg [15:0] next_tag,saved_tag;reg [127:0] expected_payload,read_payload;
 reg [140:0] saved_context;
 assign ready=!reset&&admit&&!poison&&!exhausted&&state==IDLE;
 assign valid=!reset&&!poison&&state==RESULT;
 assign result=saved_write?expected_payload:read_payload;
 assign busy=state!=IDLE;
 assign desc_valid=!reset&&!poison&&state==DESC;
 assign desc_write=!saved_write;assign desc_address=saved_external;
 assign desc_local=saved_address;assign desc_words=11'd1;assign desc_tag=saved_tag;
 assign complete_ready=!reset&&!poison&&state==WAITING;
 assign context_o=saved_context;
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;poison<=0;next_tag<=1;saved_tag<=0;saved_write<=0;observed<=0;exhausted<=0;
   saved_address<=0;saved_external<=0;expected_payload<=0;read_payload<=0;saved_context<=0;
  end else begin
   if(protocol_error)poison<=1;
   if(req&&ready)begin
    saved_write<=wr;saved_address<=address;expected_payload<=data;saved_context<=context_i;
    saved_external<=wr?external_read:external_write;observed<=0;saved_tag<=next_tag;
    if(next_tag==TAG_LIMIT)exhausted<=1;else next_tag<=next_tag+1'b1;
    state<=DESC;
   end
   if(req&&state==IDLE&&exhausted)poison<=1;
   if(desc_valid&&desc_ready)state<=WAITING;
   if(native_valid&&native_take)begin
    if(state!=WAITING||observed||native_write!=saved_write||saved_write&&native_result!=expected_payload)poison<=1;
    else begin observed<=1;read_payload<=native_result;end
   end
   if(complete_valid)begin
    if(state!=WAITING||complete_tag!=saved_tag||complete_status!=0||complete_words!=1||!observed)poison<=1;
    else if(complete_ready)state<=RESULT;
   end
   if(valid&&take)state<=IDLE;
  end
 end
endmodule
