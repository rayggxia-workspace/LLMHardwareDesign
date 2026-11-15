`timescale 1ns/1ps
// Assign a physical native64 DMA serial independently of the issuing local
// controller's command ticket. The client permits a bounded window of independent 64 B beats.
// An exhausted serial namespace is reused only after a matched physical fence.
module native64_dma_read_window_client #(
    parameter integer OUTSTANDING=4,
    parameter logic [30:0] SERIAL_LIMIT = 31'h7fff_ffff
) (
    input logic clk, reset,
    input logic req_valid,
    output logic req_ready,
    input logic [63:0] req_address, req_tag,
    output logic rsp_valid,
    input logic rsp_ready,
    output logic [63:0] rsp_tag,
    output logic [511:0] rsp_data,
    output logic rsp_error,
    output logic dma_valid,
    input logic dma_ready,
    output logic [63:0] dma_address,
    output logic [31:0] dma_tag,
    input logic dma_rsp_valid,
    output logic dma_rsp_ready,
    input logic [31:0] dma_rsp_tag,
    input logic [511:0] dma_rsp_data,
    output logic fence_valid,
    input logic fence_ready,
    output logic [31:0] fence_cookie,
    output logic [8:0] fence_epoch,
    input logic fence_done_valid,
    output logic fence_done_ready,
    input logic [31:0] fence_done_cookie,
    input logic [8:0] fence_done_epoch,
    output logic idle, protocol_fault
);

 localparam AVAILABLE=0,FENCE_OFFER=1,FENCE_WAIT=2;
 reg [1:0] state;
 reg [30:0] serial;
 reg exhausted;
 reg [40:0] fence_identity;
 reg [OUTSTANDING-1:0] live;
 reg [30:0] serials[0:OUTSTANDING-1];
 reg [63:0] tags[0:OUTSTANDING-1];
 integer free_slot,response_slot;
 reg has_free,matched;
 always @*begin
  free_slot=0;has_free=0;response_slot=0;matched=0;
  for(integer j=OUTSTANDING-1;j>=0;j=j-1)begin
   if(!live[j])begin free_slot=j;has_free=1;end
   if(live[j]&&serials[j]==dma_rsp_tag[31:1])begin response_slot=j;matched=1;end
  end
 end
 assign dma_valid=!reset&&state==AVAILABLE&&!exhausted&&has_free&&req_valid;
 assign req_ready=!reset&&state==AVAILABLE&&!exhausted&&has_free&&dma_ready;
 assign dma_address=req_address;assign dma_tag={serial,1'b0};
 assign rsp_valid=!reset&&state==AVAILABLE&&dma_rsp_valid&&matched;
 assign rsp_tag=tags[response_slot];assign rsp_data=dma_rsp_data;assign rsp_error=dma_rsp_tag[0];
 assign dma_rsp_ready=!reset&&(!matched||rsp_ready);
 assign fence_valid=!reset&&state==FENCE_OFFER;
 assign {fence_epoch,fence_cookie}=fence_identity;
 assign fence_done_ready=!reset;
 assign idle=!reset&&state==AVAILABLE&&live==0;
 wire match_fence={fence_done_epoch,fence_done_cookie}==fence_identity;
 integer i;
 always @(posedge clk)begin
  if(reset)begin
   state<=AVAILABLE;serial<=0;exhausted<=0;fence_identity<=1;live<=0;protocol_fault<=0;
   for(i=0;i<OUTSTANDING;i=i+1)begin serials[i]<=0;tags[i]<=0;end
  end else begin
   if(dma_rsp_valid&&dma_rsp_ready&&!matched)protocol_fault<=1;
   if(fence_done_valid&&(state!=FENCE_WAIT||!match_fence))protocol_fault<=1;
   if(dma_valid&&dma_ready)begin
    live[free_slot]<=1;serials[free_slot]<=serial;tags[free_slot]<=req_tag;
    if(serial==SERIAL_LIMIT)exhausted<=1;else serial<=serial+1;
   end
   if(rsp_valid&&rsp_ready)live[response_slot]<=0;
   if(state==AVAILABLE&&exhausted&&live==0&&req_valid)state<=FENCE_OFFER;
   if(state==FENCE_OFFER&&fence_ready)state<=FENCE_WAIT;
   if(state==FENCE_WAIT&&fence_done_valid&&match_fence)begin
    serial<=0;exhausted<=0;fence_identity<=fence_identity+1;state<=AVAILABLE;
   end
  end
 end
endmodule
