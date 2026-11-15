// Parent ADD service; native descriptor/identity/completion, selected E macro.
module add_s32_service_controller #(parameter logic [31:0] TOPOLOGY=0)(
 input wire clk,
 input wire reset,
 input wire service_valid,
 output wire service_ready,
 input wire [127:0] service_owner,
 input wire [31:0] service_ticket,
 input wire [1023:0] service_descriptor,
 input wire service_cancel_valid,
 output wire service_cancel_ready,
 output wire service_done_valid,
 input wire service_done_ready,
 output wire [127:0] service_done_owner,
 output wire [31:0] service_done_ticket,
 output wire [15:0] service_done_status,
 output wire [31:0] service_done_read_bytes,
 output wire [31:0] service_done_write_bytes,
 output wire s_req_valid,
 output wire s_req_write,
 input wire s_req_ready,
 output wire [9:0] s_req_address,
 output wire [127:0] s_req_data,
 input wire s_rsp_valid,
 input wire s_rsp_error,
 output wire s_rsp_ready,
 input wire [127:0] s_rsp_data,
 output wire resource_e_in_valid,
 input wire resource_e_in_ready,
 output wire [63:0] resource_e_in_data,
 output wire [3:0] resource_e_in_op,
 output wire [3:0] resource_e_in_mask,
 output wire [7:0] resource_e_in_shift,
 output wire [2:0] resource_e_in_minus,
 input wire resource_e_out_valid,
 output wire resource_e_out_ready,
 input wire [63:0] resource_e_out_data,
 input wire [3:0] resource_e_out_clipped,
 input wire resource_e_out_error
);

 wire [2:2] qkv_ready,qkv_done,qkv_cancel_ready,qkv_s_valid,qkv_s_write,qkv_s_take;
 wire [2:2][127:0] qkv_owner,qkv_s_data;
 wire [2:2][15:0] qkv_status;
 wire [2:2][31:0] qkv_reads,qkv_writes;
 wire [2:2][9:0] qkv_s_word;
 assign service_ready=qkv_ready[2];
 assign service_done_valid=qkv_done[2];
 assign service_done_status=qkv_status[2];
 assign service_done_read_bytes=qkv_reads[2];
 assign service_done_write_bytes=qkv_writes[2];
 assign s_req_valid=qkv_s_valid[2];
 assign s_req_write=qkv_s_write[2];
 assign s_req_address=qkv_s_word[2];
 assign s_req_data=qkv_s_data[2];
 assign s_rsp_ready=qkv_s_take[2];
 logic qkv_word_valid,qkv_word_ready,qkv_word_done,qkv_word_take,qkv_word_error;
 logic [9:0] qkv_word_left,qkv_word_right,qkv_word_dest;
 logic [31:0] qkv_word_tag,qkv_word_done_tag;
 logic [3:0] qkv_word_clipped;
 s32_add_scope #(.SCHEMA(3),.PROVIDER_ABI(7),.TOPOLOGY(TOPOLOGY),.OPERATION(2)) qkv_add(
  .clk,.reset,.service_valid(service_valid),
  .service_ready(qkv_ready[2]),.service_owner(service_owner),
  .service_ticket(service_ticket),.service_descriptor(service_descriptor),
  .service_cancel_valid(service_cancel_valid),.service_cancel_ready(service_cancel_ready),
  .service_done_valid(qkv_done[2]),.service_done_ready(service_done_ready),
  .service_done_owner(service_done_owner),.service_done_ticket(service_done_ticket),.service_done_status(qkv_status[2]),
  .service_done_read_bytes(qkv_reads[2]),.service_done_write_bytes(qkv_writes[2]),
  .word_valid(qkv_word_valid),.word_ready(qkv_word_ready),.word_left(qkv_word_left),.word_right(qkv_word_right),
  .word_destination(qkv_word_dest),.word_tag(qkv_word_tag),.word_done_valid(qkv_word_done),
  .word_done_ready(qkv_word_take),.word_done_tag(qkv_word_done_tag),.word_error(qkv_word_error),
  .word_clipped(qkv_word_clipped));
 logic qkv_e_valid,qkv_e_ready,qkv_e_done,qkv_e_take,qkv_e_error;
 logic [63:0] qkv_e_data,qkv_e_result;
 logic [3:0] qkv_e_op,qkv_e_mask,qkv_e_clipped;
 logic [7:0] qkv_e_shift;
 logic [2:0] qkv_e_minus;
 projection_bias_e32_s128 qkv_add_word(
  .clk,.reset,.cmd_valid(qkv_word_valid),.cmd_ready(qkv_word_ready),.cmd_projection(qkv_word_left),
  .cmd_bias(qkv_word_right),.cmd_dst(qkv_word_dest),.cmd_tag(qkv_word_tag),.busy(),
  .done_valid(qkv_word_done),.done_ready(qkv_word_take),.done_tag(qkv_word_done_tag),
  .done_clipped(qkv_word_clipped),.done_error(qkv_word_error),
  .s_req_valid(qkv_s_valid[2]),.s_req_ready(s_req_ready),
  .s_req_write(qkv_s_write[2]),.s_req_address(qkv_s_word[2]),.s_req_data(qkv_s_data[2]),
  .s_rsp_valid(s_rsp_valid),.s_rsp_ready(qkv_s_take[2]),.s_rsp_data(s_rsp_data),.s_rsp_error(s_rsp_error),
  .e_in_valid(qkv_e_valid),.e_in_ready(qkv_e_ready),.e_in_data(qkv_e_data),.e_in_op(qkv_e_op),
  .e_in_mask(qkv_e_mask),.e_in_shift(qkv_e_shift),.e_in_minus(qkv_e_minus),
  .e_out_valid(qkv_e_done),.e_out_ready(qkv_e_take),.e_out_data(qkv_e_result),
  .e_out_clipped(qkv_e_clipped),.e_out_error(qkv_e_error));
 // Resource e is supplied by the selected parent binding.




    assign resource_e_in_valid = qkv_e_valid;
    assign qkv_e_ready = resource_e_in_ready;
    assign resource_e_in_data = qkv_e_data;
    assign resource_e_in_op = qkv_e_op;
    assign resource_e_in_mask = qkv_e_mask;
    assign resource_e_in_shift = qkv_e_shift;
    assign resource_e_in_minus = qkv_e_minus;
    assign qkv_e_done = resource_e_out_valid;
    assign resource_e_out_ready = qkv_e_take;
    assign qkv_e_result = resource_e_out_data;
    assign qkv_e_clipped = resource_e_out_clipped;
    assign qkv_e_error = resource_e_out_error;
endmodule
