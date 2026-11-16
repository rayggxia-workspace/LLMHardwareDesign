`timescale 1ns/1ps
// Adds only 12 scale bits to the existing two A leases. The original frontend
// owns key/kk/generation/use-count/data lifetimes. Matching committed metadata
// may arrive after a load command is offered; no A load is accepted before it.
// Capture and A command admission are atomic; the 8 A beats share one shift.
// Private-S copy prefix and real read ACKs remain the original data readiness.
module private_a_scaled_abort_frontend(
  input logic clk, reset, halt, flush,
  input logic abort_valid, output logic abort_ready,
  input logic abort_transport_drained,
  input logic [127:0] abort_key,
  input logic abort_slot,
  input logic [15:0] abort_generation,abort_kk,abort_use_sequence,
  input logic scale_valid, input logic [127:0] scale_key,
  input logic [15:0] scale_kk, input logic [5:0] scale_shift,
  output wire [5:0] a_shift,
  input logic cmd_valid, output logic cmd_ready,
  input logic cmd_slot,
  input logic [15:0] cmd_generation, cmd_kk, cmd_planned_uses,
  input logic [127:0] cmd_key,
  input logic [9:0] cmd_S_base, cmd_copy_offset,
  input logic [127:0] copy_key,
  input logic [10:0] copy_committed_prefix,
  output logic load_done_valid, input logic load_done_ready,
  output logic load_done_slot, load_done_error,
  output logic [15:0] load_done_generation,
  output logic [127:0] load_done_key,
  output logic s_valid, input logic s_ready,
  output logic [9:0] s_address, output logic [31:0] s_tag,
  input logic response_valid, output logic response_ready,
  input logic [31:0] response_tag,
  input logic [127:0] response_data,
  input logic w_valid, output logic w_ready,
  input logic w_slot,
  input logic [15:0] w_generation, w_kk, w_use_sequence,
  input logic [127:0] w_key,
  input logic [31:0] w_record,
  input logic use_valid, output logic use_ready,
  input logic use_slot,
  input logic [15:0] use_generation, use_kk, use_sequence,
  input logic [127:0] use_key,
  output logic a_valid, input logic a_ready,
  output logic [255:0] a_data,
  output logic [2:0] a_step,
  output logic [31:0] a_weight_record,
  output logic [127:0] a_key,
  output logic a_slot,
  output logic [15:0] a_generation, a_kk, a_use_sequence,
  input logic close_valid, output logic close_ready,
  input logic close_slot,
  input logic [15:0] close_generation,
  input logic release_valid, output logic release_ready,
  input logic release_slot,
  input logic [15:0] release_generation,
  output logic quiescent, source_reads_drained,
  output logic [1:0] live_slots,
  output logic [31:0] fault_cycles
);
  wire native_cmd_ready;
  wire scale_match=scale_valid && scale_key==cmd_key && scale_kk==cmd_kk && scale_shift<=17;
  wire native_cmd_valid=cmd_valid && scale_match;
  reg [5:0] slot_shift[0:1];
  assign cmd_ready=native_cmd_ready && scale_match;
  assign a_shift=slot_shift[a_slot];
  private_a_tile_abort_frontend data_front(.cmd_valid(native_cmd_valid),.cmd_ready(native_cmd_ready),.*);
  always @(posedge clk)begin
    if(reset)begin slot_shift[0]<=0;slot_shift[1]<=0;end
    else if(cmd_valid && cmd_ready)slot_shift[cmd_slot]<=scale_shift;
  end
endmodule
