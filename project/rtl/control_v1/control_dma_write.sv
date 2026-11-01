// Two 16-word write buffers. S reads are real request/response transactions.
// W follows actual AW acceptance order; AXI B may arrive in either ID order.
module control_dma_write(
 input wire clk,reset,
 input wire burst_valid,output wire burst_ready,input wire [39:0] burst_address,
 input wire [9:0] burst_local_word,input wire [3:0] burst_s_instance,
 input wire [4:0] burst_beats,input wire burst_id,input wire [15:0] burst_last_strobe,
 output reg ack_valid,output reg ack_id,output reg ack_error,output reg protocol_error,
 output reg awvalid,input wire awready,output reg [39:0] awaddr,output wire [1:0] awid,
 output reg [7:0] awlen,output wire [2:0] awsize,output wire [1:0] awburst,
 output reg wvalid,input wire wready,output reg [127:0] wdata,output reg [15:0] wstrb,output reg wlast,
 input wire bvalid,output wire bready,input wire [1:0] bid,input wire [1:0] bresp,
 output reg s_request,input wire s_ready,output reg [9:0] s_address,output reg [3:0] s_instance,
 input wire s_valid,output wire s_take,input wire [127:0] s_data
);
 reg [1:0] used,aw_sent,w_done,b_seen,failed;
 reg [39:0] address[0:1];reg [9:0] local_word[0:1];reg [3:0] instance_id[0:1];
 reg [4:0] beats[0:1],loaded[0:1];reg [15:0] mask[0:1];reg [127:0] payload[0:31];
 reg aw_slot,s_slot,s_waiting,next_fill;
 reg order[0:1];reg order_read,order_write;reg [1:0] order_count;reg [4:0] w_index;
 assign burst_ready=!used[burst_id];
 assign awid={1'b0,aw_slot};assign awsize=3'd4;assign awburst=2'b01;
 assign bready=1'b1;assign s_take=s_waiting;
 wire aw_take=awvalid && awready;
 wire w_take=wvalid && wready;
 wire pop_order=w_take && wlast;
 wire known_b=!bid[1] && used[bid[0]] && aw_sent[bid[0]] && !b_seen[bid[0]];
 wire finish0=used[0] && w_done[0] && b_seen[0];
 wire finish1=used[1] && w_done[1] && b_seen[1];
 reg choose_fill_valid,choose_fill;
 always @* begin
  choose_fill_valid=0;choose_fill=next_fill;
  if(used[next_fill] && loaded[next_fill]<beats[next_fill]) choose_fill_valid=1;
  else if(used[!next_fill] && loaded[!next_fill]<beats[!next_fill]) begin choose_fill_valid=1;choose_fill=!next_fill;end
 end
 integer j;
 always @(posedge clk) begin
  if(reset) begin
   used<=0;aw_sent<=0;w_done<=0;b_seen<=0;failed<=0;aw_slot<=0;s_slot<=0;s_waiting<=0;next_fill<=0;
   order_read<=0;order_write<=0;order_count<=0;order[0]<=0;order[1]<=0;w_index<=0;
   awvalid<=0;awaddr<=0;awlen<=0;wvalid<=0;wdata<=0;wstrb<=0;wlast<=0;
   s_request<=0;s_address<=0;s_instance<=0;ack_valid<=0;ack_id<=0;ack_error<=0;protocol_error<=0;
   for(j=0;j<2;j=j+1) begin address[j]<=0;local_word[j]<=0;instance_id[j]<=0;beats[j]<=0;loaded[j]<=0;mask[j]<=0;end
  end else begin
   ack_valid<=0;
   if(burst_valid && burst_ready) begin
    used[burst_id]<=1;address[burst_id]<=burst_address;local_word[burst_id]<=burst_local_word;
    instance_id[burst_id]<=burst_s_instance;beats[burst_id]<=burst_beats;mask[burst_id]<=burst_last_strobe;
    aw_sent[burst_id]<=0;w_done[burst_id]<=0;b_seen[burst_id]<=0;failed[burst_id]<=0;loaded[burst_id]<=0;
    if(burst_beats==0 || burst_beats>16) begin protocol_error<=1;w_done[burst_id]<=1;b_seen[burst_id]<=1;failed[burst_id]<=1;end
   end
   if(!s_request && !s_waiting && choose_fill_valid) begin
    s_request<=1;s_slot<=choose_fill;s_address<=local_word[choose_fill]+{5'b0,loaded[choose_fill]};s_instance<=instance_id[choose_fill];
   end else if(s_request && s_ready) begin s_request<=0;s_waiting<=1;end
   if(s_valid && s_take) begin
    payload[{s_slot,loaded[s_slot][3:0]}]<=s_data;loaded[s_slot]<=loaded[s_slot]+1;s_waiting<=0;next_fill<=!s_slot;
   end
   if(!awvalid) begin
    if(used[0] && !aw_sent[0] && !w_done[0] && loaded[0]==beats[0]) begin aw_slot<=0;awaddr<=address[0];awlen<={3'b0,beats[0]}-8'd1;awvalid<=1;end
    else if(used[1] && !aw_sent[1] && !w_done[1] && loaded[1]==beats[1]) begin aw_slot<=1;awaddr<=address[1];awlen<={3'b0,beats[1]}-8'd1;awvalid<=1;end
   end else if(aw_take) begin awvalid<=0;aw_sent[aw_slot]<=1;order[order_write]<=aw_slot;order_write<=!order_write;end
   case({aw_take,pop_order}) 2'b10:order_count<=order_count+1;2'b01:order_count<=order_count-1;default:begin end endcase
   if(!wvalid && order_count!=0) begin
    wvalid<=1;wdata<=payload[{order[order_read],w_index[3:0]}];wlast<=w_index+5'd1==beats[order[order_read]];
    wstrb<=w_index+5'd1==beats[order[order_read]]?mask[order[order_read]]:16'hffff;
   end else if(w_take) begin
    wvalid<=0;
    if(wlast) begin w_done[order[order_read]]<=1;order_read<=!order_read;w_index<=0;end
    else w_index<=w_index+1;
   end
   if(bvalid) begin
    if(!known_b) protocol_error<=1;
    else begin b_seen[bid[0]]<=1;if(bresp!=0) failed[bid[0]]<=1;
     if(!w_done[bid[0]] && !(pop_order && order[order_read]==bid[0])) begin protocol_error<=1;failed[bid[0]]<=1;end
    end
   end
   if(finish0 || finish1) begin ack_valid<=1;ack_id<=!finish0;ack_error<=failed[!finish0];used[!finish0]<=0;end
  end
 end
endmodule
