// Execute RMSNorm over two leased halves of U0's existing 16 KiB private SRAM.
module u_resident_add (
    input wire clk, reset, svc_valid,
    output wire svc_ready,
    input wire [1023:0] descriptor,
    output wire rsp_valid,
    input wire rsp_ready,
    output wire [15:0] status,
    output wire [31:0] read_bytes, write_bytes,
    output wire s_req_valid, s_req_write,
    input wire s_req_ready,
    output wire [9:0] s_req_address,
    output wire [127:0] s_req_data,
    input wire s_rsp_valid,
    output wire s_rsp_ready,
    input wire [127:0] s_rsp_data
);

 wire [2:2] qkv_ready,qkv_done,qkv_cancel_ready,qkv_s_valid,qkv_s_write,qkv_s_take;
 wire [2:2][127:0] qkv_owner,qkv_s_data;
 wire [2:2][15:0] qkv_status;
 wire [2:2][31:0] qkv_reads,qkv_writes;
 wire [2:2][9:0] qkv_s_word;
 wire [1023:0] service_descriptor = {832'd0,descriptor[512+:64],32'd25001,32'd7,16'd2,16'd128,(descriptor[1023:576]==0 ? 32'd3 : 32'd0)};
 assign svc_ready=qkv_ready[2];
 assign rsp_valid=qkv_done[2];
 assign status=qkv_status[2];
 assign read_bytes=qkv_reads[2];
 assign write_bytes=qkv_writes[2];
 assign s_req_valid=qkv_s_valid[2];
 assign s_req_write=qkv_s_write[2];
 assign s_req_address=qkv_s_word[2];
 assign s_req_data=qkv_s_data[2];
 assign s_rsp_ready=qkv_s_take[2];
 logic qkv_word_valid,qkv_word_ready,qkv_word_done,qkv_word_take,qkv_word_error;
 logic [9:0] qkv_word_left,qkv_word_right,qkv_word_dest;
 logic [31:0] qkv_word_tag,qkv_word_done_tag;
 logic [3:0] qkv_word_clipped;
 s32_add_scope #(.SCHEMA(3),.PROVIDER_ABI(7),.TOPOLOGY(25001),.OPERATION(2)) qkv_add(
  .clk,.reset,.service_valid(svc_valid),
  .service_ready(qkv_ready[2]),.service_owner(128'd0),
  .service_ticket(32'd0),.service_descriptor(service_descriptor),
  .service_cancel_valid(1'b0),.service_cancel_ready(qkv_cancel_ready[2]),
  .service_done_valid(qkv_done[2]),.service_done_ready(rsp_ready),
  .service_done_owner(qkv_owner[2]),.service_done_ticket(),.service_done_status(qkv_status[2]),
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
  .s_rsp_valid(s_rsp_valid),.s_rsp_ready(qkv_s_take[2]),.s_rsp_data(s_rsp_data),.s_rsp_error(1'b0),
  .e_in_valid(qkv_e_valid),.e_in_ready(qkv_e_ready),.e_in_data(qkv_e_data),.e_in_op(qkv_e_op),
  .e_in_mask(qkv_e_mask),.e_in_shift(qkv_e_shift),.e_in_minus(qkv_e_minus),
  .e_out_valid(qkv_e_done),.e_out_ready(qkv_e_take),.e_out_data(qkv_e_result),
  .e_out_clipped(qkv_e_clipped),.e_out_error(qkv_e_error));
 e_s32_ap64 qkv_e(
  .clk,.reset,.in_valid(qkv_e_valid),.in_ready(qkv_e_ready),.in_data(qkv_e_data),.in_op(qkv_e_op),
  .in_mask(qkv_e_mask),.in_shift(qkv_e_shift),.in_minus(qkv_e_minus),
  .out_valid(qkv_e_done),.out_ready(qkv_e_take),.out_data(qkv_e_result),
  .out_clipped(qkv_e_clipped),.out_error(qkv_e_error));


endmodule
