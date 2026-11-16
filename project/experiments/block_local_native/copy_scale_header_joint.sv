module copy_scale_header_joint(
 input wire clk,reset,halt,start_valid,output wire start_ready,
 input wire [127:0] start_key,lease_key,
 input wire [15:0] start_generation,start_kk,start_written_mask,
 input wire [31:0] start_session,start_ticket,
 input wire [5:0] start_shift,input wire [2:0] start_mask,
 input wire start_producer_error,
 input wire [2:0] lease_valid,output wire [2:0] lease_ready,lease_error,
 input wire [2:0] frame_stall,ack_stall,metadata_ready,
 input wire [2:0] inject_ack_valid,input wire [95:0] inject_ack_tag,
 input wire [2:0] inject_ack_error,input wire [127:0] header_xor,
 output wire [2:0] frame_valid,frame_ready,
 output wire [95:0] frame_tag,output wire [383:0] frame_data,
 output wire [2:0] metadata_valid,data_enabled,
 output wire [383:0] metadata_key,output wire [17:0] metadata_shift,
 output wire [47:0] metadata_generation,metadata_kk,
 output wire [95:0] metadata_session,metadata_ticket,
 input wire [2:0] release_valid,output wire [2:0] release_ready,
 input wire release_cancel,data_drained,consumer_drained,
 output wire [2:0] rx_quiescent,
 output wire done_valid,input wire done_ready,output wire done_error,
 output wire quiescent,output wire [31:0] rejected_ack,
 output wire [95:0] rejected_frames
);
 wire [2:0] rx_ready,rx_ack_valid,rx_ack_ready,rx_ack_error,tx_ack_valid,tx_ack_ready,tx_ack_error;
 wire [95:0] rx_ack_tag,tx_ack_tag;
 assign frame_ready=rx_ready&~frame_stall;
 assign rx_ack_ready=tx_ack_ready&~ack_stall&~inject_ack_valid;
 assign tx_ack_valid=(rx_ack_valid&~ack_stall&~inject_ack_valid)|inject_ack_valid;
 assign tx_ack_error=(rx_ack_error&~inject_ack_valid)|(inject_ack_error&inject_ack_valid);
 for(genvar p=0;p<3;p=p+1)begin:ports
  assign tx_ack_tag[p*32+:32]=inject_ack_valid[p] ? inject_ack_tag[p*32+:32] : rx_ack_tag[p*32+:32];
  copy_scale_header_rx rx(.clk(clk),.reset(reset),
   .lease_valid(lease_valid[p]),.lease_ready(lease_ready[p]),.lease_key(lease_key),
   .lease_generation(start_generation),.lease_kk(start_kk),.lease_session(start_session),.lease_ticket(start_ticket),
   .lease_error(lease_error[p]),.frame_valid(frame_valid[p]&&!frame_stall[p]),.frame_ready(rx_ready[p]),
   .frame_tag(frame_tag[p*32+:32]),
   .frame_data(frame_data[p*128+:128] ^ (frame_tag[p*32] ? header_xor : 128'd0)),
   .ack_valid(rx_ack_valid[p]),.ack_ready(rx_ack_ready[p]),.ack_tag(rx_ack_tag[p*32+:32]),.ack_error(rx_ack_error[p]),
   .metadata_valid(metadata_valid[p]),.metadata_ready(metadata_ready[p]),
   .metadata_key(metadata_key[p*128+:128]),.metadata_generation(metadata_generation[p*16+:16]),
   .metadata_kk(metadata_kk[p*16+:16]),.metadata_session(metadata_session[p*32+:32]),
   .metadata_ticket(metadata_ticket[p*32+:32]),.metadata_shift(metadata_shift[p*6+:6]),
   .data_enabled(data_enabled[p]),.release_valid(release_valid[p]),.release_ready(release_ready[p]),
   .release_key(lease_key),.release_generation(start_generation),.release_cancel(release_cancel),
   .data_drained(data_drained),.consumer_drained(consumer_drained),.quiescent(rx_quiescent[p]),
   .rejected_frames(rejected_frames[p*32+:32]));
 end
 copy_scale_header_tx tx(.ack_valid(tx_ack_valid),.ack_ready(tx_ack_ready),.ack_tag(tx_ack_tag),.ack_error(tx_ack_error),.*);
endmodule
