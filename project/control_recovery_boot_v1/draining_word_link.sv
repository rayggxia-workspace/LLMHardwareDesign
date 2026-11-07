`timescale 1ns/1ps
// An offered destination request is irrevocable: drain it even after halt.
module draining_word_link(
 input wire clk_i,rst_ni,halt_i,input wire source_valid,output wire source_ready,
 input wire [9:0] source_address,input wire [127:0] source_data,source_identity,
 input wire reserved,input wire [9:0] reserved_address,input wire [127:0] reserved_identity,
 output wire destination_valid,input wire destination_ready,output wire [9:0] destination_address,
 output wire [127:0] destination_data,input wire destination_ack,output wire destination_ack_ready,
 output wire ack_valid,input wire ack_ready,output wire [127:0] ack_identity,
 output wire ack_abort,ack_committed,output wire store_commit,output reg busy
);
 reg sent,committed,offered;reg [9:0] address;reg [127:0] data,identity;
 wire match=reserved && address==reserved_address && identity==reserved_identity;
 assign source_ready=rst_ni && !halt_i && !busy;
 assign destination_valid=rst_ni && busy && !sent && (offered || !halt_i && match);
 assign destination_address=address;assign destination_data=data;
 assign destination_ack_ready=rst_ni && busy && sent && !committed;
 assign store_commit=destination_ack && destination_ack_ready;
 assign ack_valid=rst_ni && busy && (committed || halt_i && !sent && !offered);
 assign ack_identity=identity;assign ack_abort=halt_i;assign ack_committed=committed;
 always @(posedge clk_i)begin
  if(!rst_ni)begin busy<=0;sent<=0;committed<=0;offered<=0;address<=0;data<=0;identity<=0;end
  else begin
   if(source_valid && source_ready)begin busy<=1;sent<=0;committed<=0;offered<=0;address<=source_address;data<=source_data;identity<=source_identity;end
   if(destination_valid)begin offered<=1;if(destination_ready)sent<=1;end
   if(store_commit)committed<=1;
   if(ack_valid && ack_ready)begin busy<=0;sent<=0;committed<=0;offered<=0;end
  end
 end
endmodule
