`timescale 1ns/1ps
// One producer's <=64 S32 values occupy every third N8 group in the
// destination 256-value ring. Reuse the actual finite copier and its real
// write acknowledgements; only address translation/lease metadata are new.
// start_first_col is a GLOBAL S32 element column, never a byte address.
// The caller must reserve the entire destination span against G consumers.
// When using one S for both sides, reserve a disjoint source scratch span.
module s32_stripe_copy(
 input wire clk,reset,halt,start_valid,output wire start_ready,
 input wire [127:0] start_key,input wire [15:0] start_generation,
 input wire [31:0] start_first_col,
 input wire [9:0] start_source_base,start_ring_base,
 input wire [4:0] start_words,input wire [15:0] start_written_mask,
 input wire start_producer_error,destination_window_released,
 output wire source_valid,input wire source_ready,
 output wire [9:0] source_address,output wire [31:0] source_tag,
 input wire source_response_valid,output wire source_response_ready,
 input wire [31:0] source_response_tag,input wire [127:0] source_response_data,
 input wire source_response_error,
 output wire destination_valid,input wire destination_ready,
 output wire [9:0] destination_address,output wire [31:0] destination_tag,
 output wire [127:0] destination_data,
 input wire destination_ack_valid,output wire destination_ack_ready,
 input wire [31:0] destination_ack_tag,input wire destination_ack_error,
 output wire [127:0] copy_key,output wire [10:0] committed_prefix,
 output wire done_valid,input wire done_ready,output wire done_error,
 output wire quiescent,output wire [31:0] fault_cycles,committed_words
);
 reg [5:0] first_word;
 reg [9:0] ring_base;
 wire [2:0] p_valid,p_ack_ready;
 wire [29:0] p_address;
 wire [95:0] p_tag;
 wire [383:0] p_data;
 wire [32:0] prefixes;
 wire [15:0] expected_mask=16'hffff>>(5'd16-start_words);
 wire shape=start_words!=0&&start_words<=16&&!start_producer_error&&
   start_first_col[2:0]==0&&start_written_mask==expected_mask&&
   {1'b0,start_ring_base}+11'd64<=1024;
 // Only bits[7:2] survive modulo 64. Explicitly consume the full global
 // index in this expression; no truncated arithmetic before modulo.
 wire [31:0] initial_word=start_first_col>>2;
 wire [5:0] scatter_offset=first_word+6'(p_address[9:1])*6'd6+6'(p_address[0]);
 assign destination_valid=p_valid[0];
 assign destination_address=ring_base+{4'd0,scatter_offset};
 assign destination_tag=p_tag[31:0];assign destination_data=p_data[127:0];
 assign destination_ack_ready=p_ack_ready[0];assign committed_prefix=prefixes[10:0];
 // Upper lanes never issue. Their replicated outputs are pruned with the
 // constant destination mask; they are not additional physical ports.
 wire unused_ports=|{p_valid[2:1],p_address[29:10],p_tag[95:32],p_data[383:128],prefixes[32:11],p_ack_ready[2:1]};
 // On a shared ordered S response port a prefetched read can block
 // the outstanding write ACK that would otherwise free the copy hold.
 early_copy_3p #(.PREFETCH_NEXT_WORD(1'b0)) core(.clk,.reset,.halt,.start_valid,.start_ready,.start_key,.start_generation,
  .start_U_base(start_source_base),.start_P_bases(30'd0),
  .start_words(shape?{6'd0,start_words}:11'd0),.start_P_mask(3'b001),.destination_window_released,
  .u_valid(source_valid),.u_ready(source_ready),.u_address(source_address),.u_tag(source_tag),
  .u_response_valid(source_response_valid),.u_response_ready(source_response_ready),
  .u_response_tag(source_response_tag),.u_response_data(source_response_data),.u_response_error(source_response_error),
  .p_valid,.p_ready({2'b00,destination_ready}),.p_address,.p_tag,.p_data,
  .p_ack_valid({2'b00,destination_ack_valid}),.p_ack_ready,
  .p_ack_tag({64'd0,destination_ack_tag}),.p_ack_error({2'b00,destination_ack_error}),
  .copy_key,.copy_committed_prefix(prefixes),.done_valid,.done_ready,.done_error,
  .quiescent,.fault_cycles,.committed_words);
 always @(posedge clk)begin
  if(reset)begin first_word<=0;ring_base<=0;end
  else if(start_valid&&start_ready)begin first_word<=initial_word[5:0];ring_base<=start_ring_base;end
 end
 // This signal has no control or data-path effect. Tools may optimize it;
 // explicitly naming the unused replicated core outputs documents scope.
 wire [26:0] _unused={unused_ports,initial_word[31:6]};
endmodule
