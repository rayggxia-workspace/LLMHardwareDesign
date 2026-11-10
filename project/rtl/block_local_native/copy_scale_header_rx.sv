// One finite receive lease for the two metadata frames. Full expected identity
// is registered (28B), plus one 6-bit pending shift, not an unbounded directory.
// Headers never reach SRAM. Header1 ACK proves the shift was actually captured.
// A load may consume metadata later while the copied tile waits in its window.
module copy_scale_header_rx(
 input wire clk,reset,
 input wire lease_valid,output wire lease_ready,
 input wire [127:0] lease_key,input wire [15:0] lease_generation,lease_kk,
 input wire [31:0] lease_session,lease_ticket,
 output wire lease_error,
 input wire frame_valid,output wire frame_ready,
 input wire [31:0] frame_tag,input wire [127:0] frame_data,
 output reg ack_valid,input wire ack_ready,
 output reg [31:0] ack_tag,output reg ack_error,
 output wire metadata_valid,input wire metadata_ready,
 output wire [127:0] metadata_key,
 output wire [15:0] metadata_generation,metadata_kk,
 output wire [31:0] metadata_session,metadata_ticket,
 output wire [5:0] metadata_shift,
 output wire data_enabled,
 input wire release_valid,output wire release_ready,
 input wire [127:0] release_key,input wire [15:0] release_generation,
 input wire release_cancel,input wire data_drained,consumer_drained,
 output wire quiescent,output reg [31:0] rejected_frames
);
 reg bound,bad_lease,key_seen,published,consumed;
 reg [127:0] key_q;
 reg [15:0] generation_q,last_generation,kk_q;
 reg [31:0] session_q,ticket_q;
 reg [5:0] shift_q;
 wire key_frame=frame_tag=={generation_q,16'h8000};
 wire header_frame=frame_tag=={generation_q,16'h8001};
 wire header_good=key_seen&&!published && header_frame &&
    frame_data[127:112]==16'h0251 && frame_data[111:96]==16'd256 &&
    frame_data[95:80]==kk_q && frame_data[79:74]<=17 && frame_data[73:64]==0 &&
    frame_data[63:32]==session_q && frame_data[31:0]==ticket_q;
 wire key_good=!key_seen&&!published && key_frame && frame_data==key_q;
 wire matching_release=bound&&release_key==key_q&&release_generation==generation_q;
 assign lease_ready=!reset&&!bound&&!ack_valid;
 assign lease_error=bound&&bad_lease;
 assign frame_ready=!reset&&bound&&!ack_valid;
 assign metadata_valid=bound&&published&&!consumed;
 assign metadata_key=key_q;assign metadata_generation=generation_q;
 assign metadata_kk=kk_q;assign metadata_session=session_q;assign metadata_ticket=ticket_q;
 assign metadata_shift=shift_q;
 assign data_enabled=bound&&published;
 // Normal release waits for the actual load admission AND its window/use
 // drains. Explicit coordinated cancellation may discard unconsumed metadata
 // only once both the link/S traffic and A consumers really drained.
 assign release_ready=!reset&&matching_release&&!ack_valid&&!frame_valid&&data_drained&&consumer_drained&&
    (release_cancel || (published&&consumed));
 assign quiescent=!bound&&!ack_valid;
 always @(posedge clk)begin
  if(reset)begin
   bound<=0;bad_lease<=0;key_seen<=0;published<=0;consumed<=0;
   key_q<=0;generation_q<=0;last_generation<=0;kk_q<=0;session_q<=0;ticket_q<=0;shift_q<=0;
   ack_valid<=0;ack_tag<=0;ack_error<=0;rejected_frames<=0;
  end else begin
   if(ack_valid&&ack_ready)ack_valid<=0;
   if(lease_valid&&lease_ready)begin
    bound<=1;key_seen<=0;published<=0;consumed<=0;shift_q<=0;
    bad_lease<=lease_generation<=last_generation || lease_kk[6:0]!=0;
    if(lease_generation>last_generation)last_generation<=lease_generation;
    key_q<=lease_key;generation_q<=lease_generation;kk_q<=lease_kk;
    session_q<=lease_session;ticket_q<=lease_ticket;
   end
   if(frame_valid&&frame_ready)begin
    ack_valid<=1;ack_tag<=frame_tag;
    ack_error<=bad_lease || !(key_good||header_good);
    if(!bad_lease&&key_good)key_seen<=1;
    else if(!bad_lease&&header_good)begin shift_q<=frame_data[79:74];published<=1;end
    else rejected_frames<=rejected_frames+1'b1;
   end
   if(metadata_valid&&metadata_ready)consumed<=1;
   if(release_valid&&release_ready)begin
    bound<=0;bad_lease<=0;key_seen<=0;published<=0;consumed<=0;shift_q<=0;
   end
  end
 end
endmodule
