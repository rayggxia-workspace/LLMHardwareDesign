// Two AXI read slots, each with exactly sixteen 128-bit payload entries.
// R may interleave/reorder IDs. ACK is delayed until real S writes complete.
module control_dma_read(
 input wire clk,reset,
 input wire burst_valid,output wire burst_ready,input wire [39:0] burst_address,
 input wire [9:0] burst_local_word,input wire [3:0] burst_s_instance,
 input wire [4:0] burst_beats,input wire burst_id,input wire [15:0] burst_last_strobe,
 output reg ack_valid,output reg ack_id,output reg ack_error,output reg protocol_error,
 output reg arvalid,input wire arready,output reg [39:0] araddr,output wire [1:0] arid,
 output reg [7:0] arlen,output wire [2:0] arsize,output wire [1:0] arburst,
 input wire rvalid,output wire rready,input wire [127:0] rdata,input wire [1:0] rid,
 input wire [1:0] rresp,input wire rlast,
 output reg s_valid,input wire s_ready,output reg [9:0] s_address,
 output reg [3:0] s_instance,output reg [127:0] s_data
);
 reg [1:0] used,ar_sent,closed,failed;
 reg [39:0] address[0:1];reg [9:0] local_word[0:1];reg [3:0] instance_id[0:1];
 reg [4:0] beats[0:1],received[0:1],stored[0:1];reg [15:0] mask[0:1];
 reg [127:0] payload[0:31];reg ar_slot,s_slot;reg next_store;
 assign burst_ready=!used[burst_id];
 assign arid={1'b0,ar_slot};assign arsize=3'd4;assign arburst=2'b01;
 wire known_r=!rid[1] && used[rid[0]] &&
  (ar_sent[rid[0]] || (arvalid && arready && ar_slot==rid[0])) && !closed[rid[0]];
 // Every accepted burst already owns its entire 16-word slot, so RREADY
 // needs no combinational dependency on AXI RID/RVALID/ARREADY inputs.
 assign rready=1'b1;
 wire [4:0] receive_next=received[rid[0]]+5'd1;
 wire beat_last=receive_next==beats[rid[0]];
 reg [127:0] masked_rdata;
 always @* begin
  masked_rdata=rdata;
  if(beat_last) for(integer byte_index=0;byte_index<16;byte_index=byte_index+1)
   if(!mask[rid[0]][byte_index]) masked_rdata[byte_index*8+:8]=8'b0;
 end
 wire finish0=used[0] && closed[0] && (failed[0] || stored[0]==received[0]) && !(s_valid && !s_slot);
 wire finish1=used[1] && closed[1] && (failed[1] || stored[1]==received[1]) && !(s_valid && s_slot);
 reg choose_store_valid,choose_store;
 always @* begin
  choose_store_valid=0;choose_store=next_store;
  if(used[next_store] && !failed[next_store] && stored[next_store]<received[next_store]) choose_store_valid=1;
  else if(used[!next_store] && !failed[!next_store] && stored[!next_store]<received[!next_store]) begin choose_store_valid=1;choose_store=!next_store;end
 end
 integer j;
 always @(posedge clk) begin
  if(reset) begin
   used<=0;ar_sent<=0;closed<=0;failed<=0;ar_slot<=0;s_slot<=0;next_store<=0;
   arvalid<=0;araddr<=0;arlen<=0;s_valid<=0;s_address<=0;s_instance<=0;s_data<=0;
   ack_valid<=0;ack_id<=0;ack_error<=0;protocol_error<=0;
   for(j=0;j<2;j=j+1) begin address[j]<=0;local_word[j]<=0;instance_id[j]<=0;beats[j]<=0;received[j]<=0;stored[j]<=0;mask[j]<=0;end
  end else begin
   ack_valid<=0;
   if(burst_valid && burst_ready) begin
    used[burst_id]<=1;address[burst_id]<=burst_address;local_word[burst_id]<=burst_local_word;
    instance_id[burst_id]<=burst_s_instance;beats[burst_id]<=burst_beats;mask[burst_id]<=burst_last_strobe;
    ar_sent[burst_id]<=0;closed[burst_id]<=0;failed[burst_id]<=0;received[burst_id]<=0;stored[burst_id]<=0;
    if(burst_beats==0 || burst_beats>16) begin protocol_error<=1;closed[burst_id]<=1;failed[burst_id]<=1;end
   end
   if(!arvalid) begin
    if(used[0] && !ar_sent[0] && !closed[0]) begin ar_slot<=0;araddr<=address[0];arlen<={3'b0,beats[0]}-8'd1;arvalid<=1;end
    else if(used[1] && !ar_sent[1] && !closed[1]) begin ar_slot<=1;araddr<=address[1];arlen<={3'b0,beats[1]}-8'd1;arvalid<=1;end
   end else if(arready) begin arvalid<=0;ar_sent[ar_slot]<=1;end
   if(rvalid && rready) begin
    if(!known_r) protocol_error<=1;
    else begin
     payload[{rid[0],received[rid[0]][3:0]}]<=masked_rdata;
     received[rid[0]]<=receive_next;
     if(rresp!=0 || rlast!=beat_last) failed[rid[0]]<=1;
     if(rlast!=beat_last) protocol_error<=1;
     if(rlast || beat_last) closed[rid[0]]<=1;
    end
   end
   if(!s_valid && choose_store_valid) begin
    s_valid<=1;s_slot<=choose_store;s_address<=local_word[choose_store]+{5'b0,stored[choose_store]};
    s_instance<=instance_id[choose_store];s_data<=payload[{choose_store,stored[choose_store][3:0]}];
   end else if(s_valid && s_ready) begin s_valid<=0;stored[s_slot]<=stored[s_slot]+1;next_store<=!s_slot;end
   if(finish0 || finish1) begin
    ack_valid<=1;ack_id<=!finish0;ack_error<=failed[!finish0];used[!finish0]<=0;
   end
  end
 end
endmodule
