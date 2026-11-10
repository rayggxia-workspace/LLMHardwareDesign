`timescale 1ns/1ps
// A single immutable 4096B A16 window in the existing ordinary S128 address
// space. Sixteen per-tile shifts plus exact COPY/header proof; no payload RAM.
module resident_x16_directory(
 input logic clk,reset, input logic cfg_valid,output logic cfg_ready,
 input logic [127:0] cfg_key,input logic [9:0] cfg_base,
 input logic storage_and_consumers_drained,output logic cfg_error,
 input logic publish_valid,output logic publish_ready,output logic publish_error,
 input logic [127:0] header_key,copy_key,
 input logic [15:0] header_k,copy_k,header_gen,copy_gen,
 input logic [31:0] header_session,copy_session,header_ticket,copy_ticket,
 input logic [5:0] header_shift,
 input logic [9:0] copy_base,input logic [10:0] copy_ack_prefix,
 input logic copy_done,copy_error,
 output logic resident_sealed,output logic [127:0] resident_key,output logic [9:0] resident_base,
 input logic [127:0] lookup_key,input logic [15:0] lookup_k,
 output logic lookup_valid,output logic [5:0] lookup_shift
);
 logic live;
 logic [4:0] committed;
 logic [5:0] shift[0:15];
 wire [10:0] next_base={1'b0,resident_base}+{2'd0,committed,4'd0};
 wire [15:0] next_k={4'd0,committed,7'd0};
 wire matching_copy=copy_done&&!copy_error&&copy_ack_prefix==16&&header_key==resident_key&&
    copy_key==header_key&&header_k==next_k&&copy_k==header_k&&header_gen!=0&&copy_gen==header_gen&&
    copy_session==header_session&&copy_ticket==header_ticket&&{1'b0,copy_base}==next_base;
 assign cfg_ready=!reset&&storage_and_consumers_drained&&!publish_valid;
 assign publish_ready=!reset;
 assign resident_sealed=!reset&&live&&committed==16;
 assign lookup_valid=resident_sealed&&lookup_key==resident_key&&lookup_k[15:11]==0&&lookup_k[6:0]==0;
 assign lookup_shift=lookup_valid?shift[lookup_k[10:7]]:0;
 always_ff @(posedge clk) begin
  if(reset) begin
   live<=0;resident_key<=0;resident_base<=0;committed<=0;cfg_error<=0;publish_error<=0;
   for(integer i=0;i<16;i=i+1) shift[i]<=0;
  end else begin
   cfg_error<=0;publish_error<=0;
   if(cfg_valid&&cfg_ready)begin
    if(cfg_base[3:0]!=0||cfg_base>10'd768)cfg_error<=1;
    else begin
     live<=1;resident_key<=cfg_key;resident_base<=cfg_base;committed<=0;
    end
   end
   if(publish_valid&&publish_ready)begin
    if(!live||committed==16||!matching_copy||header_shift>17)publish_error<=1;
    else begin
     shift[committed[3:0]]<=header_shift;committed<=committed+1'b1;
    end
   end
  end
 end
endmodule
