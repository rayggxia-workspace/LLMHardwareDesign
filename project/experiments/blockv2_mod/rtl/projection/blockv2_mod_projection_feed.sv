`timescale 1ns/1ps
// Descriptor-started single-P activation supply. The selected plan owns the
// source row and scratch until completion. P independently executes its scope.
// All progress follows SRAM/COPY/header/lease acknowledgements.
module blockv2_mod_projection_feed #(parameter logic [31:0] TOPOLOGY=25001)(
 input logic clk,reset,
 input logic service_valid, output logic service_ready,
 input logic [1023:0] descriptor, input logic descriptor_crc_ok,
 input logic [127:0] service_owner,
 output logic done_valid, input logic done_ready,
 output logic [127:0] done_owner, output logic [15:0] done_status,
 output logic busy,
 input logic window_need_valid, input logic [15:0] window_need_k,
 input logic [127:0] window_need_key,
 output logic lease_valid, input logic lease_ready,
 output logic [127:0] lease_key,
 output logic [15:0] lease_generation,lease_k,
 output logic [31:0] lease_session,lease_ticket,
 output logic release_window,input logic release_ready,window_enabled,
 output logic header_valid,input logic header_ready,
 output logic [31:0] header_tag,output logic [127:0] header_data,
 input logic header_ack_valid,output logic header_ack_ready,
 input logic [31:0] header_ack_tag,input logic header_ack_error,
 output logic cp_valid,input logic cp_ready,
 output logic [9:0] cp_address,output logic [31:0] cp_tag,
 output logic [127:0] cp_data,
 input logic cp_ack_valid,output logic cp_ack_ready,
 input logic [31:0] cp_ack_tag,input logic cp_ack_error,
 output logic copy_drained,copy_progress_valid,
 output logic [127:0] copy_key,
 output logic [15:0] copy_generation,copy_k,
 output logic [31:0] copy_session,copy_ticket,
 output logic [10:0] copy_committed_prefix,
 input logic proof_valid,output logic proof_ready,
 input logic [5:0] proof_shift,input logic source_reads_drained,
 output logic q_valid,input logic q_ready,output logic q_write,
 output logic [9:0] q_address,output logic [127:0] q_data,
 output logic [31:0] q_tag,
 input logic q_rsp_valid,output logic q_rsp_ready,
 input logic [31:0] q_rsp_tag,input logic [127:0] q_rsp_data,
 input logic q_rsp_error,
 output logic u_valid,input logic u_ready,
 output logic [9:0] u_address,output logic [31:0] u_tag,
 input logic u_rsp_valid,output logic u_rsp_ready,
 input logic [31:0] u_rsp_tag,input logic [127:0] u_rsp_data,
 input logic u_rsp_error
);
 localparam logic [31:0] SCHEMA=32'h44454650, ABI=32'h02500002;
 logic occupied,bad;
 logic [9:0] source_base,scratch_base,p_base;
 logic [127:0] input_key;
 logic [31:0] session,last_session;
 logic [15:0] first_k;
 wire ranged=descriptor[48+:16]==2;
 wire [15:0] in_first=ranged?descriptor[352+:16]:16'd0;
 wire [15:0] in_source=descriptor[128+:16],in_scratch=descriptor[144+:16],
             in_dest=descriptor[160+:16],in_tiles=descriptor[176+:16];
 wire [31:0] source_end={16'd0,in_source}+({16'd0,in_tiles}<<5);
 wire valid_desc=descriptor_crc_ok && descriptor[31:0]==SCHEMA &&
   descriptor[32+:16]==128 && (descriptor[48+:16]==1 || ranged) &&
   descriptor[64+:32]==ABI && descriptor[96+:32]==TOPOLOGY &&
   in_tiles>0 && in_tiles<=32 && source_end<=1024 &&
   in_scratch<=1008 && in_dest<=1008 &&
   (source_end<={16'd0,in_scratch} || {16'd0,in_scratch}+16<={16'd0,in_source}) &&
   descriptor[192+:128]!=0 && descriptor[320+:32]>last_session &&
   (ranged ? descriptor[991:368]==0 : descriptor[991:352]==0) &&
   in_first[6:0]==0 && ({16'd0,in_first}+({16'd0,in_tiles}<<7))<=65535;
 logic seq_ready,seq_done,seq_error;
 wire accept=service_valid&&service_ready;
 assign service_ready=!reset&&!occupied&&seq_ready;
 assign busy=!reset&&occupied;
 assign done_valid=!reset&&occupied&&(bad||seq_done);
 assign done_status=bad?16'h02e0:seq_error?16'h02e1:16'h0000;
 always_ff @(posedge clk) begin
  if(reset)begin
   occupied<=0;bad<=0;source_base<=0;scratch_base<=0;p_base<=0;
   first_k<=0;input_key<=0;session<=0;last_session<=0;done_owner<=0;
  end else begin
   if(accept)begin
    occupied<=1;bad<=!valid_desc;done_owner<=service_owner;
    source_base<=in_source[9:0];scratch_base<=in_scratch[9:0];p_base<=in_dest[9:0];
    first_k<=in_first;input_key<=descriptor[192+:128];session<=descriptor[320+:32];
    if(valid_desc)last_session<=descriptor[320+:32];
   end
   // A live-protocol error retains ownership until coordinated reset.
   if(done_valid&&done_ready&&(bad||!seq_error))occupied<=0;
  end
 end
 logic quant_valid,quant_ready,quant_done,quant_error,quant_cancelled,quant_take;
 logic [5:0] quant_shift,scale;
 logic [127:0] quant_owner;
 logic [15:0] quant_k,quant_mask;
 logic [4:0] quant_words;
 logic [31:0] quant_rejected;
 logic h_valid,h_ready,h_done,h_error,h_take,h_idle;
 logic c_valid,c_ready,c_done,c_error,c_take;
 logic [2:0] hf_valid,hf_ready,ha_valid,ha_ready,ha_error;
 logic [95:0] hf_tag,ha_tag;
 logic [383:0] hf_data;
 logic [2:0] pc_valid,pc_ready,pc_ack_valid,pc_ack_ready,pc_ack_error;
 logic [29:0] pc_address;
 logic [95:0] pc_tag,pc_ack_tag;
 logic [383:0] pc_data;
 logic [32:0] copy_prefix;
 logic [31:0] header_rejected,copy_faults,copy_count;
 assign lease_key=input_key;
 assign lease_session=session;
 assign copy_committed_prefix=copy_prefix[10:0];
 assign header_valid=hf_valid[0];assign header_tag=hf_tag[31:0];assign header_data=hf_data[127:0];
 assign hf_ready={2'b00,header_ready};assign ha_valid={2'b00,header_ack_valid};
 assign ha_tag={64'd0,header_ack_tag};assign ha_error={2'b00,header_ack_error};
 assign header_ack_ready=ha_ready[0];
 assign cp_valid=pc_valid[0];assign cp_address=pc_address[9:0];
 assign cp_tag=pc_tag[31:0];assign cp_data=pc_data[127:0];assign cp_ack_ready=pc_ack_ready[0];
 assign pc_ready={2'b00,cp_ready};assign pc_ack_valid={2'b00,cp_ack_valid};
 assign pc_ack_tag={64'd0,cp_ack_tag};assign pc_ack_error={2'b00,cp_ack_error};
 always_ff @(posedge clk)
  if(reset)scale<=0;else if(quant_done&&quant_take)scale<=quant_shift;
 ffn_k_window_sequencer #(.RESET_GENERATION_ON_COMMAND(1'b1),.RANGED_COMMAND(1'b1)) windows(
  .clk,.reset,.namespace_rearm(1'b0),.command_valid(accept&&valid_desc),.command_ready(seq_ready),
  .command_tiles(in_tiles[6:0]),.command_first_k(in_first),.command_quantize(1'b1),.command_early(1'b0),
  .need_match(window_need_valid&&window_need_k==lease_k&&window_need_key==input_key),
  .need_bad_owner(window_need_valid&&window_need_key!=input_key),.previous_drained(1'b0),
  .tile_k(lease_k),.tile_generation(lease_generation),.tile_ticket(lease_ticket),
  .quant_valid,.quant_ready,.quant_done,.quant_bad(quant_error||quant_cancelled),
  .publish_ready(1'b1),.quant_take,.shift_valid(1'b1),.header_idle(h_idle),.source_idle(copy_drained),
  .lease_ready({2'b11,lease_ready}),.lease_start(lease_valid),
  .header_valid(h_valid),.header_ready(h_ready),.header_done(h_done),.header_bad(h_error),.header_take(h_take),
  .copy_valid(c_valid),.copy_ready(c_ready),.copy_done(c_done),.copy_bad(c_error),.copy_take(c_take),
  .proof_valid({2'b11,proof_valid}),.proof_bad(proof_shift!=scale||!source_reads_drained),.proof_take(proof_ready),
  .release_ready({2'b11,release_ready}),.lease_release(release_window),
  .done_valid(seq_done),.done_error(seq_error),.done_ready(done_ready&&occupied&&!bad));
 s32_a16_tile_quantizer #(.SESSION_IDS(1'b1)) quant(
  .observe_start(1'b0),.observe_valid(1'b0),.observe_data(128'd0),.observed_valid(),.observed_shift(),
  .clk,.reset,.cmd_valid(quant_valid),.cmd_ready(quant_ready),.cmd_key(input_key),
  .cmd_generation(lease_generation),.cmd_kk(lease_k),.cmd_session(session),
  .cmd_source(source_base+10'((lease_k-first_k)>>2)),.cmd_destination(scratch_base),
  .cmd_shift_known(1'b0),.cmd_shift(6'd0),.cancel_valid(1'b0),.cancel_key(128'd0),
  .s_valid(q_valid),.s_ready(q_ready),.s_write(q_write),.s_address(q_address),.s_data(q_data),.s_tag(q_tag),
  .rsp_valid(q_rsp_valid),.rsp_ready(q_rsp_ready),.rsp_tag(q_rsp_tag),.rsp_data(q_rsp_data),.rsp_error(q_rsp_error),
  .done_valid(quant_done),.done_ready(quant_take),.done_key(quant_owner),.done_kk(quant_k),
  .done_error(quant_error),.done_cancelled(quant_cancelled),.done_words(quant_words),
  .done_written_mask(quant_mask),.done_shift(quant_shift),.rejected_responses(quant_rejected));
 copy_scale_header_tx headers(
  .clk,.reset,.halt(1'b0),.start_valid(h_valid),.start_ready(h_ready),.start_key(input_key),
  .start_generation(lease_generation),.start_kk(lease_k),.start_written_mask(16'hffff),
  .start_session(session),.start_ticket(lease_ticket),.start_shift(scale),
  .start_mask(3'b001),.start_producer_error(1'b0),
  .frame_valid(hf_valid),.frame_ready(hf_ready),.frame_tag(hf_tag),.frame_data(hf_data),
  .ack_valid(ha_valid),.ack_ready(ha_ready),.ack_tag(ha_tag),.ack_error(ha_error),
  .done_valid(h_done),.done_ready(h_take),.done_error(h_error),.quiescent(h_idle),.rejected_ack(header_rejected));
 early_copy_epoch_3p #(.SESSION_IDS(1'b1)) copy(
  .clk,.reset,.halt(1'b0),.start_valid(c_valid),.start_ready(c_ready),.start_key(input_key),
  .start_generation(lease_generation),.start_kk(lease_k),.start_session(session),.start_ticket(lease_ticket),
  .start_U_base(scratch_base),.start_P_bases({20'd0,p_base}),.start_words(11'd16),
  .start_P_mask(3'b001),.destination_window_released(window_enabled),
  .u_valid,.u_ready,.u_address,.u_tag,.u_response_valid(u_rsp_valid),.u_response_ready(u_rsp_ready),
  .u_response_tag(u_rsp_tag),.u_response_data(u_rsp_data),.u_response_error(u_rsp_error),
  .p_valid(pc_valid),.p_ready(pc_ready),.p_address(pc_address),.p_tag(pc_tag),.p_data(pc_data),
  .p_ack_valid(pc_ack_valid),.p_ack_ready(pc_ack_ready),.p_ack_tag(pc_ack_tag),.p_ack_error(pc_ack_error),
  .copy_key,.copy_committed_prefix(copy_prefix),.copy_generation,.copy_kk(copy_k),
  .copy_identity_valid(copy_progress_valid),.copy_session,.copy_ticket,
  .done_valid(c_done),.done_ready(c_take),.done_error(c_error),.quiescent(copy_drained),
  .fault_cycles(copy_faults),.committed_words(copy_count));
endmodule
