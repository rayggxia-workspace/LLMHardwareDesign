`timescale 1ns/1ps
// Typed P service over the actual range and M2 providers. Descriptor bytes
// have already passed CRC in the local fetch and remain held until DONE.
// The original M, S, COPY/header and control route are independent peers.
// No new W/A/result payload bank or duplicate descriptor register here.
module p_stream_scope_node #(
 parameter logic [31:0] TOPOLOGY=32'd25001,
 parameter bit FOUR_BANK_LOOKAHEAD=1'b0,EARLY_EXEC=1'b0
)(
 input logic clk,reset,
 input logic service_valid,output logic service_ready,
 input logic [127:0] service_owner,input logic [31:0] service_ticket,
 input logic [1023:0] service_descriptor,
 input logic service_cancel_valid,output logic service_cancel_ready,
 output logic service_done_valid,input logic service_done_ready,
 output logic [127:0] service_done_owner,output logic [31:0] service_done_ticket,
 output logic [15:0] service_done_status,
 output logic [31:0] service_done_read_bytes,service_done_write_bytes,
 output logic window_need_valid,output logic [15:0] window_need_k,
 output logic [127:0] window_need_key,
 // Header/window admission and actual COPY progress have distinct owners.
 // A new header is insufficient to relabel an old same-key prefix.
 input logic stream_window_valid,input logic [127:0] stream_window_key,
 input logic [15:0] stream_window_generation,stream_window_k_elements,
 input logic [31:0] stream_window_session,stream_window_ticket,
 input logic copy_progress_valid,input logic [15:0] copy_progress_generation,
 input logic [31:0] copy_progress_session,copy_progress_ticket,
 input logic [15:0] copy_progress_k_elements,
 output logic a_load_proof_valid,input logic a_load_proof_ready,
 output logic [127:0] a_load_proof_key,output logic [15:0] a_load_proof_window_generation,
 output logic [31:0] a_load_proof_window_session,a_load_proof_window_ticket,
 output logic [15:0] a_load_proof_k_elements,a_load_proof_A_generation,
 output logic a_load_proof_A_slot,a_load_proof_error,output logic [5:0] a_load_proof_shift,
 output logic a_source_reads_drained,
 input logic [127:0] copy_key,input logic [10:0] copy_committed_prefix,
 output logic [127:0] scale_lookup_key,output logic [15:0] scale_lookup_kk,
 input logic scale_lookup_valid,input logic [5:0] scale_lookup_shift,
 output logic ar_valid,input logic ar_ready,output logic [9:0] ar_address,output logic [31:0] ar_tag,
 input logic ar_rsp_valid,output logic ar_rsp_ready,input logic [31:0] ar_rsp_tag,input logic [127:0] ar_rsp_data,
 output logic sw_valid,input logic sw_ready,output logic [511:0] sw_ticket,
 output logic sw_word,output logic [9:0] sw_address,output logic [127:0] sw_data,
 input logic sw_ack_valid,output logic sw_ack_ready,input logic [511:0] sw_ack_ticket,
 input logic sw_ack_word,sw_ack_error,
 output logic lc_valid,input logic lc_ready,output logic lc_sop,lc_eop,output logic [127:0] lc_data,
 input logic lr_valid,output logic lr_ready,input logic lr_sop,lr_eop,input logic [127:0] lr_data,
 output logic a_valid,input logic a_ready,output logic [255:0] a_data,
 output logic [31:0] a_session,output logic [2:0] a_beat,
 output logic quiescent,quarantine,output logic [31:0] protocol_faults,
 output logic [1:0] A_live,result_occupied,command_occupied
);
 logic exec_ready,range_ready;
 logic record_valid,record_ready,complete_valid,complete_ready;
 logic [127:0] record_owner,complete_owner,input_key;
 logic [31:0] record_sequence,record_col,complete_sequence;
 logic [63:0] record_address;
 logic [15:0] record_full_k,record_k,record_bytes,complete_next_k;
 logic [3:0] record_context,record_n,complete_context;
 logic record_way,record_head16,record_create,record_restore,record_final,record_spill,record_A_first,record_A_last;
 logic [4:0] record_A_uses;
 logic complete_error;
 logic [31:0] confirmed_weight_read_bytes,confirmed_result_write_bytes;
 logic [31:0] rf0,rf1,out_version;
 logic [63:0] bias0,bias1;
 logic [9:0] input_s,out_s0,out_s1,scratch_s,snapshot_s;
 logic rejected_complete;
 wire scope_fire=service_valid&&service_ready;
 wire scope_end=service_done_valid&&service_done_ready;
 assign service_ready=range_ready&&exec_ready;
 assign window_need_valid=record_valid&&record_A_first;
 assign window_need_k=record_k;
 assign window_need_key=input_key;
 p_scope_range_service #(.NATIVE_STREAM_A16(1'b1)) ranges(
   .clk,.reset,.service_valid(service_valid&&exec_ready),.service_ready(range_ready),
   .service_owner,.service_ticket,.service_descriptor,.expected_topology(TOPOLOGY),
   .service_cancel_valid,.service_cancel_ready,.service_done_valid,.service_done_ready,
   .service_done_owner,.service_done_ticket,.service_done_status,
   .native_confirmed_read_bytes(confirmed_weight_read_bytes),.native_confirmed_write_bytes(confirmed_result_write_bytes),
   .service_done_read_bytes,.service_done_write_bytes,.input_key,
   .rf_object_base0(rf0),.rf_object_base1(rf1),.output_version(out_version),
   .bias_address0(bias0),.bias_address1(bias1),.input_s_base(input_s),.output_s_base0(out_s0),
   .output_s_base1(out_s1),.scratch_s_base(scratch_s),.snapshot_s_base(snapshot_s),
   .record_valid,.record_ready,.record_owner,.record_sequence,.record_address,.record_bytes,.record_full_k,
   .record_k,.record_col,.record_context,.record_n,.record_way,.record_head16,.record_create,.record_restore,
   .record_final,.record_spill,.record_A_first,.record_A_last,.record_A_uses,
   .complete_valid,.complete_ready,.complete_owner,.complete_sequence,.complete_context,.complete_next_k,
   .complete_error,.rejected_complete);
 if(EARLY_EXEC)begin: early_exec
   p_native_weight_overlap_candidate #(.FOUR_BANK_LOOKAHEAD(1'b1)) exec(
     .scope_valid(scope_fire),.scope_ready(exec_ready),.scope_end,
     .scope_cancel(service_cancel_valid&&service_cancel_ready),
     .scope_owner(service_owner),.scope_data(service_descriptor),.*);
 end else if(FOUR_BANK_LOOKAHEAD)begin: four_w
   p_native_weight_prefill #(.FOUR_BANK_LOOKAHEAD(1'b1)) exec(
     .scope_valid(scope_fire),.scope_ready(exec_ready),.scope_end,
     .scope_cancel(service_cancel_valid&&service_cancel_ready),
     .scope_owner(service_owner),.scope_data(service_descriptor),.*);
 end else begin: serial_w
   p_native_stream_m2_bounded exec(
     .scope_valid(scope_fire),.scope_ready(exec_ready),.scope_end,
     .scope_cancel(service_cancel_valid&&service_cancel_ready),
     .scope_owner(service_owner),.scope_data(service_descriptor),.*);
 end
 // These outputs are already validated by the real range service. They do
 // not instantiate a second parser or storage and may optimize away here.
 wire _unused_decoded=^{rf0,rf1,out_version,bias0,bias1,input_s,out_s0,out_s1,scratch_s,snapshot_s,record_bytes,rejected_complete};
endmodule
