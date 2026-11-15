module blockv2_mod_p_resident_services (
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
 output wire [31:0] s_tag,
 input wire [31:0] s_response_tag,
 input wire clk, reset, service_valid, service_cancel_valid,
 output wire service_ready, service_cancel_ready,
 input wire [127:0] service_owner,
 input wire [31:0] service_ticket,
 input wire [1023:0] service_descriptor,
 output wire service_done_valid,
 input wire service_done_ready,
 output wire [127:0] service_done_owner,
 output wire [15:0] service_done_status,
 output wire [31:0] service_done_read_bytes, service_done_write_bytes,
 output wire s_valid, s_write,
 input wire s_ready,
 output wire [9:0] s_word,
 output wire [127:0] s_data,
 input wire s_response_valid,
 output wire s_take,
 input wire [127:0] s_response_data
);
 reg active;
 reg [2:0] selected;
 wire [2:0] selected_offer =
     service_descriptor[31:0]==32'h314d5347 ? 3'd7 :
     service_descriptor[31:0]==32'h38534446 ? 3'd6 :
     service_descriptor[31:0]==32'h31545441 ? 3'd5 :
     (service_descriptor[31:0]==32'h3152564b || service_descriptor[31:0]==32'h31535744) ? 3'd4 : service_descriptor[31:0]==32'h314c5244 ? 2'd1 :
     service_descriptor[31:0]==32'h31455052 ? 2'd3 : 2'd2;
 wire [7:1] qkv_ready,qkv_done,qkv_cancel_ready,qkv_s_valid,qkv_s_write,qkv_s_take;
 wire [7:1][127:0] qkv_owner,qkv_s_data;
 wire [7:1][15:0] qkv_status;
 wire [7:1][31:0] qkv_reads,qkv_writes;
 wire [7:1][9:0] qkv_s_word;

 assign service_ready = !active && qkv_ready[selected_offer];
 assign service_done_valid = active && qkv_done[selected];
 assign service_cancel_ready = active && qkv_cancel_ready[selected];
 assign service_done_owner = qkv_owner[selected];
 assign service_done_status = qkv_status[selected];
 assign service_done_read_bytes = qkv_reads[selected];
 assign service_done_write_bytes = qkv_writes[selected];
 assign s_valid=active && qkv_s_valid[selected];
 assign s_write=qkv_s_write[selected];
 assign s_word=qkv_s_word[selected];
 assign s_data=qkv_s_data[selected];
 assign s_take=active && qkv_s_take[selected];
 always @(posedge clk) begin
   if (reset) begin active<=0; selected<=2; end
   else begin
     if (service_valid && service_ready) begin active<=1; selected<=selected_offer; end
     if (service_done_valid && service_done_ready) active<=0;
   end
 end
 logic qkv_word_valid,qkv_word_ready,qkv_word_done,qkv_word_take,qkv_word_error;
 logic [9:0] qkv_word_left,qkv_word_right,qkv_word_dest;
 logic [31:0] qkv_word_tag,qkv_word_done_tag;
 logic [3:0] qkv_word_clipped;
 s32_add_scope #(.SCHEMA(3),.PROVIDER_ABI(7),.TOPOLOGY(25001),.OPERATION(2)) qkv_add(
  .clk,.reset,.service_valid(service_valid && !active && (selected_offer==2)),
  .service_ready(qkv_ready[2]),.service_owner(service_owner),
  .service_ticket(service_ticket),.service_descriptor(service_descriptor),
  .service_cancel_valid(service_cancel_valid&&active && (selected==2)),.service_cancel_ready(qkv_cancel_ready[2]),
  .service_done_valid(qkv_done[2]),.service_done_ready(service_done_ready&&active && (selected==2)),
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
  .s_req_valid(qkv_s_valid[2]),.s_req_ready(active && (selected==2)&&s_ready),
  .s_req_write(qkv_s_write[2]),.s_req_address(qkv_s_word[2]),.s_req_data(qkv_s_data[2]),
  .s_rsp_valid(active && (selected==2)&&s_response_valid),.s_rsp_ready(qkv_s_take[2]),.s_rsp_data(s_response_data),.s_rsp_error(1'b0),
  .e_in_valid(qkv_e_valid),.e_in_ready(qkv_e_ready),.e_in_data(qkv_e_data),.e_in_op(qkv_e_op),
  .e_in_mask(qkv_e_mask),.e_in_shift(qkv_e_shift),.e_in_minus(qkv_e_minus),
  .e_out_valid(qkv_e_done),.e_out_ready(qkv_e_take),.e_out_data(qkv_e_result),
  .e_out_clipped(qkv_e_clipped),.e_out_error(qkv_e_error));
 e_s32_ap64 qkv_e(
  .clk,.reset,.in_valid(qkv_e_valid),.in_ready(qkv_e_ready),.in_data(qkv_e_data),.in_op(qkv_e_op),
  .in_mask(qkv_e_mask),.in_shift(qkv_e_shift),.in_minus(qkv_e_minus),
  .out_valid(qkv_e_done),.out_ready(qkv_e_take),.out_data(qkv_e_result),
  .out_clipped(qkv_e_clipped),.out_error(qkv_e_error));

 s128_rope_scope #(.TOPOLOGY(25001)) qkv_rope(
  .clk,.reset,.service_valid(service_valid && !active && (selected_offer==3)),
  .service_ready(qkv_ready[3]),.service_owner(service_owner),
  .service_ticket(service_ticket),.service_descriptor(service_descriptor),
  .service_cancel_valid(service_cancel_valid&&active && (selected==3)),.service_cancel_ready(qkv_cancel_ready[3]),
  .service_done_valid(qkv_done[3]),.service_done_ready(service_done_ready&&active && (selected==3)),
  .service_done_owner(qkv_owner[3]),.service_done_ticket(),.service_done_status(qkv_status[3]),
  .service_done_read_bytes(qkv_reads[3]),.service_done_write_bytes(qkv_writes[3]),
  .s_req_valid(qkv_s_valid[3]),.s_req_ready(active && (selected==3)&&s_ready),
  .s_req_write(qkv_s_write[3]),.s_req_address(qkv_s_word[3]),.s_req_data(qkv_s_data[3]),
  .s_rsp_valid(active && (selected==3)&&s_response_valid),.s_rsp_ready(qkv_s_take[3]),.s_rsp_data(s_response_data),.s_rsp_error(1'b0));

 wire store_wr_valid,store_wr_take,fds_wr_valid,fds_wr_take;
 wire [63:0] store_wr_address,store_wr_tag,fds_wr_address,fds_wr_tag;
 wire [511:0] store_wr_data,fds_wr_data;
 assign resident_wr_valid=selected==6 ? fds_wr_valid : store_wr_valid;
 assign resident_wr_address=selected==6 ? fds_wr_address : store_wr_address;
 assign resident_wr_tag=selected==6 ? fds_wr_tag : store_wr_tag;
 assign resident_wr_data=selected==6 ? fds_wr_data : store_wr_data;
 assign resident_wr_done_ready=selected==6 ? fds_wr_take : store_wr_take;
 wire load_rd_valid,load_rd_take,att_rd_valid,att_rd_take;
 wire [63:0] load_rd_address,load_rd_tag,att_rd_address,att_rd_tag;
 assign resident_rd_valid=selected==5 ? att_rd_valid : load_rd_valid;
 assign resident_rd_address=selected==5 ? att_rd_address : load_rd_address;
 assign resident_rd_tag=selected==5 ? att_rd_tag : load_rd_tag;
 assign resident_rd_rsp_ready=selected==5 ? att_rd_take : load_rd_take;
 wire [31:0] load_s_tag;
 assign s_tag=selected==1 ? load_s_tag : 32'd0;
 assign qkv_s_write[1]=1'b1;
 ddr_s128_load_scope #(.TOPOLOGY(25001),.PAYLOAD_BYTES(512)) load (
  .clk,.reset,.service_valid(service_valid && !active && selected_offer==1),
  .service_ready(qkv_ready[1]),.service_owner,.service_ticket,.service_descriptor,
  .service_cancel_valid(service_cancel_valid && active && selected==1),
  .service_cancel_ready(qkv_cancel_ready[1]),.service_done_valid(qkv_done[1]),
  .service_done_ready(service_done_ready && active && selected==1),
  .service_done_owner(qkv_owner[1]),.service_done_ticket(),
  .service_done_status(qkv_status[1]),.service_done_read_bytes(qkv_reads[1]),.service_done_write_bytes(qkv_writes[1]),
  .rd_valid(load_rd_valid),.rd_ready(selected==1 && resident_rd_ready),.rd_address(load_rd_address),.rd_tag(load_rd_tag),
  .rd_rsp_valid(selected==1 && resident_rd_rsp_valid),.rd_rsp_ready(load_rd_take),
  .rd_rsp_tag(resident_rd_rsp_tag),.rd_rsp_data(resident_rd_rsp_data),.rd_rsp_error(resident_rd_rsp_error),
  .s_valid(qkv_s_valid[1]),.s_ready(active && selected==1 && s_ready),
  .s_address(qkv_s_word[1]),.s_data(qkv_s_data[1]),.s_tag(load_s_tag),
  .s_rsp_valid(active && selected==1 && s_response_valid),.s_rsp_ready(qkv_s_take[1]),
  .s_rsp_tag(s_response_tag),.s_rsp_error(1'b0)
 );
 assign qkv_s_write[4]=1'b0;
 assign qkv_s_data[4]=128'd0;
 s128_kv_store_scope #(.TOPOLOGY(25001),.SHARED_STORE(1'b1)) store (
  .clk,.reset,.service_valid(service_valid && !active && selected_offer==4),
  .service_ready(qkv_ready[4]),.service_owner,.service_ticket,.service_descriptor,
  .service_cancel_valid(service_cancel_valid && active && selected==4),
  .service_cancel_ready(qkv_cancel_ready[4]),.service_done_valid(qkv_done[4]),
  .service_done_ready(service_done_ready && active && selected==4),
  .service_done_owner(qkv_owner[4]),.service_done_ticket(),
  .service_done_status(qkv_status[4]),.service_done_read_bytes(qkv_reads[4]),.service_done_write_bytes(qkv_writes[4]),
  .s_req_valid(qkv_s_valid[4]),.s_req_ready(active && selected==4 && s_ready),
  .s_req_address(qkv_s_word[4]),.s_rsp_valid(active && selected==4 && s_response_valid),
  .s_rsp_ready(qkv_s_take[4]),.s_rsp_data(s_response_data),.s_rsp_error(1'b0),
  .wr_valid(store_wr_valid),.wr_ready(selected==4 && resident_wr_ready),.wr_address(store_wr_address),
  .wr_tag(store_wr_tag),.wr_data(store_wr_data),.wr_done_valid(selected==4 && resident_wr_done_valid),
  .wr_done_ready(store_wr_take),.wr_done_tag(resident_wr_done_tag),.wr_done_error(resident_wr_done_error)
 );
 s128_attention_core_scope #(.TOPOLOGY(25001),.PIPELINE_KV_WRITES(1'b1),.V_READS_PER_16(4)) attention (
  .clk,.reset,.service_valid(service_valid && !active && selected_offer==5),
  .service_ready(qkv_ready[5]),.service_owner,.service_ticket,.service_descriptor,
  .service_cancel_valid(service_cancel_valid && active && selected==5),
  .service_cancel_ready(qkv_cancel_ready[5]),.service_done_valid(qkv_done[5]),
  .service_done_ready(service_done_ready && active && selected==5),
  .service_done_owner(qkv_owner[5]),.service_done_ticket(),
  .service_done_status(qkv_status[5]),.service_done_read_bytes(qkv_reads[5]),.service_done_write_bytes(qkv_writes[5]),
  .s_req_valid(qkv_s_valid[5]),.s_req_write(qkv_s_write[5]),.s_req_ready(active && selected==5 && s_ready),
  .s_req_address(qkv_s_word[5]),.s_req_data(qkv_s_data[5]),
  .s_rsp_valid(active && selected==5 && s_response_valid),.s_rsp_ready(qkv_s_take[5]),
  .s_rsp_data(s_response_data),.s_rsp_error(1'b0),
  .rd_valid(att_rd_valid),.rd_ready(selected==5 && resident_rd_ready),
  .rd_address(att_rd_address),.rd_tag(att_rd_tag),
  .rd_rsp_valid(selected==5 && resident_rd_rsp_valid),.rd_rsp_ready(att_rd_take),
  .rd_rsp_tag(resident_rd_rsp_tag),.rd_rsp_data(resident_rd_rsp_data),.rd_rsp_error(resident_rd_rsp_error)
 );
 wire [2:0] fds_s_req,fds_s_take;
 wire [9:0] fds_s_address;
 assign resident_peer_req=fds_s_req[2:1];
 assign resident_peer_take=fds_s_take[2:1];
 assign resident_peer_address=fds_s_address;
 assign qkv_s_valid[6]=fds_s_req[0];
 assign qkv_s_take[6]=fds_s_take[0];
 assign qkv_s_word[6]=fds_s_address;
 assign qkv_s_write[6]=0;
 assign qkv_s_data[6]=0;
 ffn_down_store_scope #(.TOPOLOGY(25001)) down_store (
 .clk,.reset,.service_valid(service_valid && !active && selected_offer==6),
 .service_ready(qkv_ready[6]),.service_owner,.service_ticket,.service_descriptor,
 .service_cancel_valid(service_cancel_valid && active && selected==6),
 .service_cancel_ready(qkv_cancel_ready[6]),.service_done_valid(qkv_done[6]),
 .service_done_ready(service_done_ready && active && selected==6),
 .service_done_owner(qkv_owner[6]),.service_done_ticket(),
 .service_done_status(qkv_status[6]),.service_done_read_bytes(qkv_reads[6]),.service_done_write_bytes(qkv_writes[6]),
 .s_req_valid(fds_s_req),.s_req_ready({resident_peer_ready,active && selected==6 && s_ready}),
 .s_req_address(fds_s_address),.s_rsp_valid({resident_peer_rsp,active && selected==6 && s_response_valid}),
 .s_rsp_ready(fds_s_take),.s_rsp_data({resident_peer_data,s_response_data}),.s_rsp_error({resident_peer_error,1'b0}),
 .wr_valid(fds_wr_valid),.wr_ready(selected==6 && resident_wr_ready),.wr_address(fds_wr_address),
 .wr_tag(fds_wr_tag),.wr_data(fds_wr_data),.wr_done_valid(selected==6 && resident_wr_done_valid),
 .wr_done_ready(fds_wr_take),.wr_done_tag(resident_wr_done_tag),.wr_done_error(resident_wr_done_error));
 gated_s32_scope #(.TOPOLOGY(25001)) gated_service(
 .clk,.reset,.service_valid(service_valid && !active && selected_offer==7),.service_ready(qkv_ready[7]),
 .service_owner,.service_ticket,.service_descriptor,
 .service_cancel_valid(service_cancel_valid && active && selected==7),.service_cancel_ready(qkv_cancel_ready[7]),
 .service_done_valid(qkv_done[7]),.service_done_ready(service_done_ready && active && selected==7),
 .service_done_owner(qkv_owner[7]),.service_done_status(qkv_status[7]),
 .service_done_read_bytes(qkv_reads[7]),.service_done_write_bytes(qkv_writes[7]),
 .s_req_valid(qkv_s_valid[7]),.s_req_write(qkv_s_write[7]),.s_req_ready(active && selected==7 && s_ready),
 .s_req_address(qkv_s_word[7]),.s_req_data(qkv_s_data[7]),.s_rsp_valid(active && selected==7 && s_response_valid),
 .s_rsp_ready(qkv_s_take[7]),.s_rsp_data(s_response_data));
endmodule
