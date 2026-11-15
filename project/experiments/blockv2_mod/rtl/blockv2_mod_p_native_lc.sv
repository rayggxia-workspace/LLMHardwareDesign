`timescale 1ns/1ps
// Integration hierarchy only. M and local S remain separate physical instances.
module blockv2_mod_p_native_lc #(parameter logic [7:0] TARGET=0)(
  output wire [1:0] resident_peer_req,
  input wire [1:0] resident_peer_ready,
  output wire [9:0] resident_peer_address,
  input wire [1:0] resident_peer_rsp,
  output wire [1:0] resident_peer_take,
  input wire [255:0] resident_peer_data,
  input wire [1:0] resident_peer_error,
  output wire resident_wr_valid,
  input wire resident_wr_ready,
  output wire [63:0] resident_wr_address, resident_wr_tag,
  output wire [511:0] resident_wr_data,
  input wire resident_wr_done_valid,
  output wire resident_wr_done_ready,
  input wire [63:0] resident_wr_done_tag,
  input wire resident_wr_done_error,
  output wire resident_rd_valid,
  input wire resident_rd_ready,
  output wire [63:0] resident_rd_address, resident_rd_tag,
  input wire resident_rd_rsp_valid,
  output wire resident_rd_rsp_ready,
  input wire [63:0] resident_rd_rsp_tag,
  input wire [511:0] resident_rd_rsp_data,
  input wire resident_rd_rsp_error,
  input logic clk,
  input logic reset,
  output logic vocab_busy,
  input logic vocab_phase_valid,
  output logic vocab_phase_ready,
  input logic [31:0] vocab_job, vocab_step, vocab_generation, vocab_epoch,
  input logic [31:0] vocab_version, vocab_length,
  output logic vocab_token_valid,
  input logic vocab_token_ready,
  output logic [31:0] vocab_token_job, vocab_token_step, vocab_token_value,
  output logic vocab_token_error, vocab_fault,
  input logic scope_offer,
  input logic scope_take,
  output logic scope_ready,
  output logic scope_done,
  output logic [127:0] scope_result_owner,
  output logic [31:0] scope_result_ticket,
  output logic [15:0] scope_result_status,
  output logic [31:0] scope_result_read_bytes,
  output logic [31:0] scope_result_write_bytes,
  input logic session_valid,
  output logic session_ready,
  input logic [31:0] session_generation,
  input logic [31:0] session_topology,
  input logic transport_drained,
  input logic cfg_valid,
  output logic cfg_ready,
  input logic [1:0] cfg_op,
  input logic [31:0] cfg_generation,
  input logic [31:0] cfg_abi,
  input logic [31:0] cfg_capacity,
  input logic [31:0] cfg_crc,
  input logic [15:0] cfg_bytes,
  input logic [13:0] cfg_address,
  input logic [127:0] cfg_data,
  output logic cfg_rsp_valid,
  input logic cfg_rsp_ready,
  output logic [7:0] cfg_status,
  output logic [31:0] cfg_actual_crc,
  output logic certified,
  output logic prepared,
  input logic rx_valid,
  output logic rx_ready,
  input logic [127:0] rx_data,
  input logic rx_sop,
  input logic rx_eop,
  input logic [7:0] rx_target,
  output logic tx_valid,
  input logic tx_ready,
  output logic [127:0] tx_data,
  output logic tx_sop,
  output logic tx_eop,
  output logic [7:0] tx_source,
  output logic desc_req_valid,
  input logic desc_req_ready,
  output logic [63:0] desc_req_address,
  output logic [31:0] desc_req_tag,
  output logic desc_req_channel,
  output logic [4:0] desc_req_record_beats,
  output logic desc_close_valid,
  input logic desc_close_ready,
  output logic [31:0] desc_close_tag_base,
  input logic desc_rsp_valid,
  output logic desc_rsp_ready,
  input logic [31:0] desc_rsp_tag,
  input logic [511:0] desc_rsp_data,
  output logic idle,
  output logic [31:0] protocol_fault_cycles,
  output logic pm_trace_valid,
  output logic [13:0] pm_trace_address,
  output logic [31:0] retired_instructions,
  output logic mc_fence_req_valid,
  input logic mc_fence_req_ready,
  output logic [31:0] mc_fence_req_cookie,
  output logic [8:0] mc_fence_req_epoch,
  input logic mc_fence_done_valid,
  output logic mc_fence_done_ready,
  input logic [31:0] mc_fence_done_cookie,
  input logic [8:0] mc_fence_done_epoch,
  output logic [5:0] committed_gate_words,
  output logic [5:0] committed_up_words,
  output logic window_need_valid,
  output logic [15:0] window_need_k,
  output logic [127:0] window_need_key,
  input logic lease_valid,
  output logic lease_ready,
  input logic [127:0] lease_key,
  input logic [15:0] lease_generation,
  input logic [15:0] lease_k,
  input logic [31:0] lease_session,
  input logic [31:0] lease_ticket,
  input logic header_valid,
  output logic header_ready,
  input logic [31:0] header_tag,
  input logic [127:0] header_data,
  output logic header_ack_valid,
  input logic header_ack_ready,
  output logic [31:0] header_ack_tag,
  output logic header_ack_error,
  input logic release_window,
  output logic release_ready,
  input logic copy_drained,
  input logic copy_progress_valid,
  input logic [127:0] copy_key,
  input logic [15:0] copy_progress_generation,
  input logic [15:0] copy_progress_k_elements,
  input logic [31:0] copy_progress_session,
  input logic [31:0] copy_progress_ticket,
  input logic [10:0] copy_committed_prefix,
  input logic cp_valid,
  output logic cp_ready,
  input logic [9:0] cp_address,
  input logic [31:0] cp_tag,
  input logic [127:0] cp_data,
  output logic cp_ack_valid,
  input logic cp_ack_ready,
  output logic [31:0] cp_ack_tag,
  output logic a_load_proof_valid,
  input logic a_load_proof_ready,
  output logic [5:0] a_load_proof_shift,
  output logic a_source_reads_drained,
  output logic quiescent,
  output logic window_enabled,
  output logic window_idle,
  input logic aux_valid,
  input logic aux_write,
  input logic [9:0] aux_address,
  input logic [127:0] aux_data,
  input logic [31:0] aux_tag,
  output logic aux_ready,
  output logic aux_rsp_valid,
  input logic aux_rsp_ready,
  output logic [31:0] aux_rsp_tag,
  output logic [127:0] aux_rsp_data,
  input logic aux2_valid,
  input logic aux2_write,
  input logic [9:0] aux2_address,
  input logic [127:0] aux2_data,
  input logic [31:0] aux2_tag,
  output logic aux2_ready,
  output logic aux2_rsp_valid,
  input logic aux2_rsp_ready,
  output logic [31:0] aux2_rsp_tag,
  output logic weight_req_valid,
  input logic weight_req_ready,
  output logic [63:0] weight_req_address,
  output logic [31:0] weight_req_tag,
  output logic weight_req_channel,
  output logic [4:0] weight_req_record_beats,
  output logic weight_close_valid,
  output logic [31:0] weight_close_tag_base,
  input logic weight_close_ready,
  input logic weight_rsp_valid,
  output logic weight_rsp_ready,
  input logic [31:0] weight_rsp_tag,
  input logic [511:0] weight_rsp_data
);
  logic service_cancel_ready;
  logic service_cancel_valid;
  logic [1023:0] service_descriptor;
  logic service_done_ready;
  logic [127:0] service_owner;
  logic [31:0] service_ticket;
  logic service_valid;
  logic provider_ready, provider_done, provider_take;
  logic [127:0] provider_owner;
  logic [31:0] provider_ticket, provider_read_bytes, provider_write_bytes;
  logic [15:0] provider_status;
  logic vocab_active, token_delivered, terminal_phase_ready, terminal_launch_ready;
  logic vocab_done_valid, vocab_p_done_ready;
  logic [127:0] vocab_done_owner;
  logic [15:0] vocab_done_status;
  logic [31:0] vocab_done_read_bytes, vocab_done_write_bytes;
  logic vocab_read_valid, vocab_read_ready, vocab_response_ready;
  logic [9:0] vocab_read_address;
  logic [31:0] vocab_read_tag;
  logic node_aux_ready, node_aux_rsp_valid;
  logic [31:0] node_aux_rsp_tag;
  logic [127:0] node_aux_rsp_data;
  logic [2:0] aux_pending, aux2_pending;
  logic node_aux2_ready, node_aux2_rsp_valid;
  logic signed [31:0] unused_token_logit;
  logic unused_logit_valid, unused_logit_last;
  logic [31:0] unused_logit_first;
  logic [3:0] unused_logit_mask;
  logic [127:0] unused_logit_data;

  wire resident_select = service_descriptor[31:0]==32'h314d5347 || service_descriptor[31:0]==32'd3 ||
      service_descriptor[31:0]==32'h31455052 || service_descriptor[31:0]==32'h314c5244 ||
      service_descriptor[31:0]==32'h38534446 || service_descriptor[31:0]==32'h31545441 || service_descriptor[31:0]==32'h3152564b || service_descriptor[31:0]==32'h31535744;
  reg resident_active;
  wire resident_admit = !vocab_active && aux_pending==0 && aux2_pending==0 &&
      !aux_valid && !aux2_valid && quiescent;
  wire resident_ready, resident_done, resident_cancel_ready;
  wire [127:0] resident_owner;
  wire [15:0] resident_status;
  wire [31:0] resident_reads, resident_writes;
  wire resident_s_valid,resident_s_write,resident_s_take;
  wire [9:0] resident_s_address;
  wire [127:0] resident_s_data;
  wire [31:0] resident_s_tag;
  wire p_provider_ready,p_provider_done,p_cancel_ready;
  wire [127:0] p_provider_owner;
  wire [31:0] p_provider_ticket,p_provider_read_bytes,p_provider_write_bytes;
  wire [15:0] p_provider_status;
  assign provider_ready = resident_select ? resident_admit && resident_ready : p_provider_ready;
  assign provider_done = resident_active ? resident_done : p_provider_done;
  assign provider_owner = resident_active ? resident_owner : p_provider_owner;
  assign provider_ticket = resident_active ? resident_owner[31:0] : p_provider_ticket;
  assign provider_status = resident_active ? resident_status : p_provider_status;
  assign provider_read_bytes = resident_active ? resident_reads : p_provider_read_bytes;
  assign provider_write_bytes = resident_active ? resident_writes : p_provider_write_bytes;
  assign service_cancel_ready = resident_active ? resident_cancel_ready : p_cancel_ready;
  always @(posedge clk) begin
    if (reset) resident_active<=0;
    else begin
      if (accept_scope && resident_select) resident_active<=1;
      if (resident_active && provider_done && provider_take) resident_active<=0;
    end
  end
  blockv2_mod_p_resident_services resident (
    .clk,.reset,.service_valid(launch_scope && resident_select && resident_admit),
    .service_ready(resident_ready),.service_owner,.service_ticket,.service_descriptor,
    .service_cancel_valid(service_cancel_valid && resident_active),
    .service_cancel_ready(resident_cancel_ready),.service_done_valid(resident_done),
    .service_done_ready(provider_take && resident_active),.service_done_owner(resident_owner),
    .service_done_status(resident_status),.service_done_read_bytes(resident_reads),
    .service_done_write_bytes(resident_writes),.s_valid(resident_s_valid),.s_write(resident_s_write),
    .s_ready(resident_active && node_aux_ready),.s_word(resident_s_address),.s_data(resident_s_data),
    .s_response_valid(resident_active && node_aux_rsp_valid),.s_take(resident_s_take),
    .s_response_data(node_aux_rsp_data),.s_tag(resident_s_tag),.s_response_tag(node_aux_rsp_tag),
    .resident_peer_req,.resident_peer_ready,.resident_peer_address,.resident_peer_rsp,.resident_peer_take,.resident_peer_data,.resident_peer_error,
    .resident_wr_valid,.resident_wr_ready,.resident_wr_address,.resident_wr_tag,.resident_wr_data,.resident_wr_done_valid,.resident_wr_done_ready,.resident_wr_done_tag,.resident_wr_done_error,
    .resident_rd_valid,.resident_rd_ready,.resident_rd_address,.resident_rd_tag,
    .resident_rd_rsp_valid,.resident_rd_rsp_ready,.resident_rd_rsp_tag,.resident_rd_rsp_data,.resident_rd_rsp_error
  );

  wire vocabulary_command = service_descriptor[31:0]==32'h02505001 &&
      service_descriptor[63:48]==16'd3;
  wire automatic_phase_offer = vocabulary_command && service_valid && !vocab_active &&
      service_descriptor[544+:32]==0 && aux_pending==0 && aux2_pending==0 &&
      !aux_valid && !aux2_valid && quiescent && !resident_active;
  wire automatic_phase_fire = automatic_phase_offer && terminal_phase_ready;
  wire [1023:0] compute_descriptor = vocabulary_command ?
      {service_descriptor[1023:992],96'd0,service_descriptor[895:64],16'd2,service_descriptor[47:0]} :
      service_descriptor;

  wire phase_offer = !vocab_active && idle && quiescent &&
      aux_pending == 0 && aux2_pending == 0 && !rx_valid && !aux_valid && !aux2_valid;
  wire phase_fire = (vocab_phase_valid && vocab_phase_ready) || automatic_phase_fire;
  wire ordinary_aux = !vocab_active && !resident_active;
  wire launch_scope = scope_offer && service_valid && (!vocabulary_command || vocab_active) && (!vocab_active || terminal_launch_ready);
  wire accept_scope = launch_scope && provider_ready;
  wire report_valid = vocab_active ? vocab_done_valid : provider_done;
  wire report_ready = scope_take && service_done_ready;

  assign vocab_busy = vocab_active || phase_fire;
  assign vocab_phase_ready = phase_offer && terminal_phase_ready;
  assign scope_ready = service_valid && provider_ready && (!vocabulary_command || vocab_active) && (!vocab_active || terminal_launch_ready);
  assign scope_done = report_valid && service_done_ready;
  assign provider_take = vocab_active ? vocab_p_done_ready : report_ready;
  assign scope_result_owner = vocab_active ? vocab_done_owner : provider_owner;
  assign scope_result_ticket = vocab_active ? vocab_done_owner[31:0] : provider_ticket;
  assign scope_result_status = vocab_active ? vocab_done_status : provider_status;
  assign scope_result_read_bytes = vocab_active ? vocab_done_read_bytes : provider_read_bytes;
  assign scope_result_write_bytes = vocab_active ? vocab_done_write_bytes : provider_write_bytes;
  assign aux_ready = ordinary_aux && node_aux_ready;
  assign aux_rsp_valid = ordinary_aux && node_aux_rsp_valid;
  assign aux_rsp_tag = node_aux_rsp_tag;
  assign aux_rsp_data = node_aux_rsp_data;
  assign aux2_ready = ordinary_aux && node_aux2_ready;
  assign aux2_rsp_valid = ordinary_aux && node_aux2_rsp_valid;
  assign vocab_read_ready = vocab_active && node_aux_ready;

  always_ff @(posedge clk) begin
    if (reset) begin
      vocab_active <= 0;
      token_delivered <= 0;
      aux_pending <= 0;
      aux2_pending <= 0;
    end else begin
      case ({aux_valid && aux_ready, aux_rsp_valid && aux_rsp_ready})
        2'b10: aux_pending <= aux_pending + 1'b1;
        2'b01: aux_pending <= aux_pending - 1'b1;
        default: ;
      endcase
      case ({aux2_valid && aux2_ready, aux2_rsp_valid && aux2_rsp_ready})
        2'b10: aux2_pending <= aux2_pending + 1'b1;
        2'b01: aux2_pending <= aux2_pending - 1'b1;
        default: ;
      endcase
      if (phase_fire) begin
        vocab_active <= 1;
        token_delivered <= 0;
      end else if (vocab_active) begin
        if (vocab_token_valid && vocab_token_ready) token_delivered <= 1;
        if (token_delivered && idle) vocab_active <= 0;
      end
    end
  end

  native_vocabulary_product_terminal vocab (
    .clk, .reset, .phase_valid((vocab_phase_valid && phase_offer) || automatic_phase_offer),
    .phase_ready(terminal_phase_ready), .phase_job_tag(automatic_phase_offer ? service_owner[95:64] : vocab_job), .phase_step(automatic_phase_offer ? service_descriptor[927:896] : vocab_step),
    .phase_generation(automatic_phase_offer ? service_owner[127:96] : vocab_generation), .phase_epoch(automatic_phase_offer ? service_owner[63:32] : vocab_epoch),
    .phase_version(automatic_phase_offer ? service_descriptor[351:320] : vocab_version), .phase_length(automatic_phase_offer ? service_descriptor[543:512] : vocab_length),
    .launch_valid(vocab_active && accept_scope), .launch_ready(terminal_launch_ready),
    .launch_owner(service_owner), .launch_first(service_descriptor[544+:32]),
    .launch_version(service_descriptor[320+:32]), .launch_count({service_descriptor[592+:5],3'd0}),
    .launch_s_base(service_descriptor[688+:10]),
    .p_done_valid(provider_done && vocab_active), .p_done_ready(vocab_p_done_ready),
    .p_done_owner(provider_owner), .p_done_status(provider_status),
    .p_done_read_bytes(provider_read_bytes), .p_done_write_bytes(provider_write_bytes),
    .service_done_valid(vocab_done_valid), .service_done_ready(vocab_active && report_ready),
    .service_done_owner(vocab_done_owner), .service_done_status(vocab_done_status),
    .service_done_read_bytes(vocab_done_read_bytes), .service_done_write_bytes(vocab_done_write_bytes),
    .s_read_valid(vocab_read_valid), .s_read_ready(vocab_read_ready),
    .s_read_address(vocab_read_address), .s_read_tag(vocab_read_tag),
    .s_rsp_valid(vocab_active && node_aux_rsp_valid), .s_rsp_ready(vocab_response_ready),
    .s_rsp_tag(node_aux_rsp_tag), .s_rsp_data(node_aux_rsp_data), .s_rsp_error(1'b0),
    .logit_valid(unused_logit_valid), .logit_ready(1'b1), .logit_first(unused_logit_first),
    .logit_mask(unused_logit_mask), .logit_data(unused_logit_data), .logit_last(unused_logit_last),
    .token_valid(vocab_token_valid), .token_ready(vocab_token_ready),
    .token_job_tag(vocab_token_job), .token_step(vocab_token_step),
    .token_value(vocab_token_value), .token_logit(unused_token_logit),
    .token_error(vocab_token_error), .fault(vocab_fault)
  );
  // synthesis translate_off
  always @(posedge clk) if (!reset) begin
    if (scope_offer && scope_ready) assert (service_ticket == service_owner[31:0]);
    if (scope_done) assert (scope_result_ticket == scope_result_owner[31:0]);
  end
  // synthesis translate_on
  lc_native_scope_controller #(.TARGET(TARGET)) lc(
    .clk(clk),
    .reset(reset),
    .session_valid(session_valid),
    .session_ready(session_ready),
    .session_generation(session_generation),
    .session_topology(session_topology),
    .transport_drained(transport_drained),
    .cfg_valid(cfg_valid),
    .cfg_ready(cfg_ready),
    .cfg_op(cfg_op),
    .cfg_generation(cfg_generation),
    .cfg_abi(cfg_abi),
    .cfg_capacity(cfg_capacity),
    .cfg_crc(cfg_crc),
    .cfg_bytes(cfg_bytes),
    .cfg_address(cfg_address),
    .cfg_data(cfg_data),
    .cfg_rsp_valid(cfg_rsp_valid),
    .cfg_rsp_ready(cfg_rsp_ready),
    .cfg_status(cfg_status),
    .cfg_actual_crc(cfg_actual_crc),
    .certified(certified),
    .prepared(prepared),
    .rx_valid(rx_valid),
    .rx_ready(rx_ready),
    .rx_data(rx_data),
    .rx_sop(rx_sop),
    .rx_eop(rx_eop),
    .rx_target(rx_target),
    .tx_valid(tx_valid),
    .tx_ready(tx_ready),
    .tx_data(tx_data),
    .tx_sop(tx_sop),
    .tx_eop(tx_eop),
    .tx_source(tx_source),
    .mc_req_valid(desc_req_valid),
    .mc_req_ready(desc_req_ready),
    .mc_req_address(desc_req_address),
    .mc_req_tag(desc_req_tag),
    .mc_req_channel(desc_req_channel),
    .mc_req_record_beats(desc_req_record_beats),
    .mc_close_valid(desc_close_valid),
    .mc_close_ready(desc_close_ready),
    .mc_close_tag_base(desc_close_tag_base),
    .mc_rsp_valid(desc_rsp_valid),
    .mc_rsp_ready(desc_rsp_ready),
    .mc_rsp_tag(desc_rsp_tag),
    .mc_rsp_data(desc_rsp_data),
    .service_valid(service_valid),
    .service_ready(scope_offer && scope_ready),
    .service_owner(service_owner),
    .service_ticket(service_ticket),
    .service_descriptor(service_descriptor),
    .service_cancel_valid(service_cancel_valid),
    .service_cancel_ready(service_cancel_ready),
    .service_done_valid(report_valid && scope_take),
    .service_done_ready(service_done_ready),
    .service_done_owner(scope_result_owner),
    .service_done_ticket(scope_result_owner[31:0]),
    .service_done_status(scope_result_status),
    .service_done_read_bytes(scope_result_read_bytes),
    .service_done_write_bytes(scope_result_write_bytes),
    .idle(idle),
    .protocol_fault_cycles(protocol_fault_cycles),
    .pm_trace_valid(pm_trace_valid),
    .pm_trace_address(pm_trace_address),
    .retired_instructions(retired_instructions)
  );
  p_native_coplacement_node #(.SHARED_MID_SOURCE(1'b1), .FOUR_BANK_LOOKAHEAD(1'b1), .EARLY_EXEC(1'b1)) node(
    .clk(clk),
    .reset(reset),
    .mc_fence_req_valid(mc_fence_req_valid),
    .mc_fence_req_ready(mc_fence_req_ready),
    .mc_fence_req_cookie(mc_fence_req_cookie),
    .mc_fence_req_epoch(mc_fence_req_epoch),
    .mc_fence_done_valid(mc_fence_done_valid),
    .mc_fence_done_ready(mc_fence_done_ready),
    .mc_fence_done_cookie(mc_fence_done_cookie),
    .mc_fence_done_epoch(mc_fence_done_epoch),
    .service_valid(launch_scope && !resident_select),
    .service_ready(p_provider_ready),
    .service_cancel_valid(service_cancel_valid && !resident_active),
    .service_cancel_ready(p_cancel_ready),
    .service_owner(service_owner),
    .service_descriptor(compute_descriptor),
    .service_done_valid(p_provider_done),
    .service_done_ready(provider_take && !resident_active),
    .service_done_owner(p_provider_owner),
    .service_done_ticket(p_provider_ticket),
    .service_done_status(p_provider_status),
    .service_done_read_bytes(p_provider_read_bytes),
    .service_done_write_bytes(p_provider_write_bytes),
    .committed_gate_words(committed_gate_words),
    .committed_up_words(committed_up_words),
    .window_need_valid(window_need_valid),
    .window_need_k(window_need_k),
    .window_need_key(window_need_key),
    .lease_valid(lease_valid),
    .lease_ready(lease_ready),
    .lease_key(lease_key),
    .lease_generation(lease_generation),
    .lease_k(lease_k),
    .lease_session(lease_session),
    .lease_ticket(lease_ticket),
    .header_valid(header_valid),
    .header_ready(header_ready),
    .header_tag(header_tag),
    .header_data(header_data),
    .header_ack_valid(header_ack_valid),
    .header_ack_ready(header_ack_ready),
    .header_ack_tag(header_ack_tag),
    .header_ack_error(header_ack_error),
    .release_window(release_window),
    .release_ready(release_ready),
    .copy_drained(copy_drained),
    .copy_progress_valid(copy_progress_valid),
    .copy_key(copy_key),
    .copy_progress_generation(copy_progress_generation),
    .copy_progress_k_elements(copy_progress_k_elements),
    .copy_progress_session(copy_progress_session),
    .copy_progress_ticket(copy_progress_ticket),
    .copy_committed_prefix(copy_committed_prefix),
    .cp_valid(cp_valid),
    .cp_ready(cp_ready),
    .cp_address(cp_address),
    .cp_tag(cp_tag),
    .cp_data(cp_data),
    .cp_ack_valid(cp_ack_valid),
    .cp_ack_ready(cp_ack_ready),
    .cp_ack_tag(cp_ack_tag),
    .a_load_proof_valid(a_load_proof_valid),
    .a_load_proof_ready(a_load_proof_ready),
    .a_load_proof_shift(a_load_proof_shift),
    .a_source_reads_drained(a_source_reads_drained),
    .quiescent(quiescent),
    .window_enabled(window_enabled),
    .window_idle(window_idle),
    .aux_valid(resident_active ? resident_s_valid : (vocab_active ? vocab_read_valid : ordinary_aux && aux_valid)),
    .aux_write(resident_active ? resident_s_write : (!vocab_active && aux_write)),
    .aux_address(resident_active ? resident_s_address : (vocab_active ? vocab_read_address : aux_address)),
    .aux_data(resident_active ? resident_s_data : (vocab_active ? 128'd0 : aux_data)),
    .aux_tag(resident_active ? resident_s_tag : (vocab_active ? vocab_read_tag : aux_tag)),
    .aux_ready(node_aux_ready),
    .aux_rsp_valid(node_aux_rsp_valid),
    .aux_rsp_ready(resident_active ? resident_s_take : (vocab_active ? vocab_response_ready : aux_rsp_ready)),
    .aux_rsp_tag(node_aux_rsp_tag),
    .aux_rsp_data(node_aux_rsp_data),
    .aux2_valid(ordinary_aux && aux2_valid),
    .aux2_write(aux2_write),
    .aux2_address(aux2_address),
    .aux2_data(aux2_data),
    .aux2_tag(aux2_tag),
    .aux2_ready(node_aux2_ready),
    .aux2_rsp_valid(node_aux2_rsp_valid),
    .aux2_rsp_ready(ordinary_aux && aux2_rsp_ready),
    .aux2_rsp_tag(aux2_rsp_tag),
    .mc_req_valid(weight_req_valid),
    .mc_req_ready(weight_req_ready),
    .mc_req_address(weight_req_address),
    .mc_req_tag(weight_req_tag),
    .mc_req_channel(weight_req_channel),
    .mc_req_record_beats(weight_req_record_beats),
    .mc_close_valid(weight_close_valid),
    .mc_close_tag_base(weight_close_tag_base),
    .mc_close_ready(weight_close_ready),
    .mc_rsp_valid(weight_rsp_valid),
    .mc_rsp_ready(weight_rsp_ready),
    .mc_rsp_tag(weight_rsp_tag),
    .mc_rsp_data(weight_rsp_data)
  );
endmodule
