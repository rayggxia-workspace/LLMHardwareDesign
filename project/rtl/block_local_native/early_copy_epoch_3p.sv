`timescale 1ns/1ps
// STREAM_A16_TILE_COPY: version the real progress of a single 256B tile.
// Same-key K tiles may reuse one S window while old A leases remain live.
// The unversioned legacy prefix must not admit a new LOAD before new COPY.
// No payload storage added. Identity registers and logic count as LC area.
module early_copy_epoch_3p(
 input wire clk,reset,halt,start_valid,output wire start_ready,
 input wire [127:0] start_key,input wire [15:0] start_generation,start_kk,
 input wire [31:0] start_session,start_ticket,
 input wire [9:0] start_U_base,input wire [29:0] start_P_bases,
 input wire [10:0] start_words,input wire [2:0] start_P_mask,
 input wire destination_window_released,
 output wire u_valid,input wire u_ready,output wire [9:0] u_address,output wire [31:0] u_tag,
 input wire u_response_valid,output wire u_response_ready,input wire [31:0] u_response_tag,
 input wire [127:0] u_response_data,input wire u_response_error,
 output wire [2:0] p_valid,input wire [2:0] p_ready,output wire [29:0] p_address,
 output wire [95:0] p_tag,output wire [383:0] p_data,
 input wire [2:0] p_ack_valid,output wire [2:0] p_ack_ready,
 input wire [95:0] p_ack_tag,input wire [2:0] p_ack_error,
 output wire [127:0] copy_key,output wire [32:0] copy_committed_prefix,
 output reg [15:0] copy_generation,copy_kk,output reg copy_identity_valid,
 output reg [31:0] copy_session,copy_ticket,
 output wire done_valid,input wire done_ready,output wire done_error,
 output wire quiescent,output wire [31:0] fault_cycles,committed_words
);
 reg [15:0] last_generation;
 wire tile_shape=start_words==16&&start_kk[6:0]==0;
 wire valid_shape=tile_shape&&start_generation>last_generation&&start_P_mask!=0&&
    {1'b0,start_U_base}+11'd16<=1024&&
    (!start_P_mask[0]||{1'b0,start_P_bases[9:0]}+11'd16<=1024)&&
    (!start_P_mask[1]||{1'b0,start_P_bases[19:10]}+11'd16<=1024)&&
    (!start_P_mask[2]||{1'b0,start_P_bases[29:20]}+11'd16<=1024);
 // STREAM can route a private P S back to the same P and its peers. Wait
 // for the previous destination ACKs before offering the next source read;
 // otherwise one ordered local S port can deadlock. No extra payload FIFO.
 early_copy_3p #(.PREFETCH_NEXT_WORD(1'b0)) data_copy(.start_words(tile_shape?start_words:11'd0),.*);
 always @(posedge clk)begin
  if(reset)begin last_generation<=0;copy_generation<=0;copy_kk<=0;copy_identity_valid<=0;copy_session<=0;copy_ticket<=0;end
  else begin
   if(start_valid&&start_ready)begin
    if(start_generation>last_generation)last_generation<=start_generation;
    // Same edge as the actual copier resets its ACK prefix to zero. An
    // invalid start never relabels a previous nonzero prefix as new data.
    copy_identity_valid<=valid_shape;copy_generation<=start_generation;copy_kk<=start_kk;
    copy_session<=start_session;copy_ticket<=start_ticket;
   end
   if(done_valid&&done_error)copy_identity_valid<=0;
  end
 end
endmodule
