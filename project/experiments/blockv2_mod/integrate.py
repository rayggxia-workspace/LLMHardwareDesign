from pathlib import Path
import sys

src = Path(sys.argv[1]).read_text()
out = Path(sys.argv[2])
src = src.replace("module p_native_lc_coplacement #(", "module blockv2_mod_p_native_lc #(", 1)
src = src.replace(
    "  input logic reset,\n",
    """  input logic reset,
  output logic vocab_busy,
  input logic vocab_phase_valid,
  output logic vocab_phase_ready,
  input logic [31:0] vocab_job, vocab_step, vocab_generation, vocab_epoch,
  input logic [31:0] vocab_version, vocab_length,
  output logic vocab_token_valid,
  input logic vocab_token_ready,
  output logic [31:0] vocab_token_job, vocab_token_step, vocab_token_value,
  output logic vocab_token_error, vocab_fault,
""", 1)
start = src.index("  logic provider_ready, provider_done;")
end = src.index("  // synthesis translate_off", start)
src = src[:start] + """  logic provider_ready, provider_done, provider_take;
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

  wire phase_offer = !vocab_active && idle && quiescent &&
      aux_pending == 0 && aux2_pending == 0 && !rx_valid;
  wire phase_fire = vocab_phase_valid && vocab_phase_ready;
  wire ordinary_aux = !vocab_active && !phase_fire;
  wire launch_scope = scope_offer && service_valid && (!vocab_active || terminal_launch_ready);
  wire accept_scope = launch_scope && provider_ready;
  wire report_valid = vocab_active ? vocab_done_valid : provider_done;
  wire report_ready = scope_take && service_done_ready;

  assign vocab_busy = vocab_active || phase_fire;
  assign vocab_phase_ready = phase_offer && terminal_phase_ready;
  assign scope_ready = service_valid && provider_ready && (!vocab_active || terminal_launch_ready);
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
    .clk, .reset, .phase_valid(vocab_phase_valid && phase_offer),
    .phase_ready(terminal_phase_ready), .phase_job_tag(vocab_job), .phase_step(vocab_step),
    .phase_generation(vocab_generation), .phase_epoch(vocab_epoch),
    .phase_version(vocab_version), .phase_length(vocab_length),
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
""" + src[end:]
src = src.replace(".service_ready(scope_offer && provider_ready)", ".service_ready(scope_offer && scope_ready)")
src = src.replace(".service_done_valid(provider_done && scope_take)", ".service_done_valid(report_valid && scope_take)")
start = src.index("  p_native_coplacement_node")
head, node = src[:start], src[start:]
node = node.replace(".service_valid(scope_offer && service_valid)", ".service_valid(launch_scope)")
node = node.replace(".service_done_ready(scope_take && service_done_ready)", ".service_done_ready(provider_take)")
for name in ("owner", "ticket", "status", "read_bytes", "write_bytes"):
    node = node.replace(f".service_done_{name}(scope_result_{name})", f".service_done_{name}(provider_{name})")
aux = {
    "valid": "vocab_active ? vocab_read_valid : ordinary_aux && aux_valid",
    "write": "!vocab_active && aux_write",
    "address": "vocab_active ? vocab_read_address : aux_address",
    "data": "vocab_active ? 128'd0 : aux_data",
    "tag": "vocab_active ? vocab_read_tag : aux_tag",
    "ready": "node_aux_ready",
    "rsp_valid": "node_aux_rsp_valid",
    "rsp_ready": "vocab_active ? vocab_response_ready : aux_rsp_ready",
    "rsp_tag": "node_aux_rsp_tag",
    "rsp_data": "node_aux_rsp_data",
}
for name, expr in aux.items():
    old = f".aux_{name}(aux_{name})"
    assert old in node, old
    node = node.replace(old, f".aux_{name}({expr})")
for name, expr in {
    "valid": "ordinary_aux && aux2_valid",
    "ready": "node_aux2_ready",
    "rsp_valid": "node_aux2_rsp_valid",
    "rsp_ready": "ordinary_aux && aux2_rsp_ready",
}.items():
    old = f".aux2_{name}(aux2_{name})"
    assert old in node, old
    node = node.replace(old, f".aux2_{name}({expr})")
out.write_text(head + node)
