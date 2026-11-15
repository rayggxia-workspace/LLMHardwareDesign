// Parent standard cells only. No U/P link or functional macro is instantiated.
module e32_service_cluster #(parameter logic [31:0] TOPOLOGY=0)(
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
 output wire rd_valid,
 input wire rd_ready,
 output wire [63:0] rd_address,
 output wire [63:0] rd_tag,
 input wire rd_rsp_valid,
 output wire rd_rsp_ready,
 input wire [63:0] rd_rsp_tag,
 input wire [511:0] rd_rsp_data,
 input wire rd_rsp_error,
 output wire s_req_valid,
 output wire s_req_write,
 input wire s_req_ready,
 output wire [9:0] s_req_address,
 output wire [127:0] s_req_data,
 input wire s_rsp_valid,
 output wire s_rsp_ready,
 input wire [127:0] s_rsp_data,
 input wire s_rsp_error,
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
 input wire resource_e_out_error,
 output wire wr_valid,
 input wire wr_ready,
 output wire [63:0] wr_address,
 output wire [63:0] wr_tag,
 output wire [511:0] wr_data,
 input wire wr_done_valid,
 output wire wr_done_ready,
 input wire [63:0] wr_done_tag,
 input wire wr_done_error
);
 wire [5:0] provider_valid,provider_ready,provider_cancel_valid,provider_cancel_ready;
 wire [5:0] provider_done_valid,provider_done_ready;
 wire [127:0] provider_owner;wire [31:0] provider_ticket;wire [1023:0] provider_descriptor;
 wire [767:0] provider_done_owner;wire [191:0] provider_done_ticket;
 wire [95:0] provider_done_status;wire [191:0] provider_done_read_bytes,provider_done_write_bytes;
 macro_service_dispatch #(.SLOTS(6),.ROUTES(6),.TOPOLOGY(TOPOLOGY),
  .SCHEMAS({32'h31414d52,32'h31455052,32'd3,32'h31535744,32'h314c5244,32'h31444d45}),
  .ABIS({32'h02504504,32'h02500002,32'd7,32'h02500002,32'h02500002,32'h02504503}),
  .OPCODES({16'd1,16'd1,16'd2,16'd1,16'd1,16'd1}),.SLOT_MAP({8'd5,8'd4,8'd3,8'd2,8'd1,8'd0})) dispatch(.*);
 wire p_rd_valid;
 wire p_rd_ready;
 wire [63:0] p_rd_address;
 wire [63:0] p_rd_tag;
 wire p_rd_rsp_valid;
 wire p_rd_rsp_ready;
 wire [63:0] p_rd_rsp_tag;
 wire [511:0] p_rd_rsp_data;
 wire p_rd_rsp_error;
 wire p_s_req_valid;
 wire p_s_req_write;
 wire p_s_req_ready;
 wire [9:0] p_s_req_address;
 wire [127:0] p_s_req_data;
 wire p_s_rsp_valid;
 wire p_s_rsp_ready;
 wire [127:0] p_s_rsp_data;
 wire p_s_rsp_error;
 wire p_resource_e_in_valid;
 wire p_resource_e_in_ready;
 wire [63:0] p_resource_e_in_data;
 wire [3:0] p_resource_e_in_op;
 wire [3:0] p_resource_e_in_mask;
 wire [7:0] p_resource_e_in_shift;
 wire [2:0] p_resource_e_in_minus;
 wire p_resource_e_out_valid;
 wire p_resource_e_out_ready;
 wire [63:0] p_resource_e_out_data;
 wire [3:0] p_resource_e_out_clipped;
 wire p_resource_e_out_error;
 wire l_rd_valid;
 wire l_rd_ready;
 wire [63:0] l_rd_address;
 wire [63:0] l_rd_tag;
 wire l_rd_rsp_valid;
 wire l_rd_rsp_ready;
 wire [63:0] l_rd_rsp_tag;
 wire [511:0] l_rd_rsp_data;
 wire l_rd_rsp_error;
 wire l_s_valid;
 wire l_s_ready;
 wire [9:0] l_s_address;
 wire [127:0] l_s_data;
 wire [31:0] l_s_tag;
 wire l_s_rsp_valid;
 wire l_s_rsp_ready;
 wire [31:0] l_s_rsp_tag;
 wire l_s_rsp_error;
 wire w_s_req_valid;
 wire w_s_req_ready;
 wire [9:0] w_s_req_address;
 wire w_s_rsp_valid;
 wire w_s_rsp_ready;
 wire [127:0] w_s_rsp_data;
 wire w_s_rsp_error;
 wire a_s_req_valid;
 wire a_s_req_write;
 wire a_s_req_ready;
 wire [9:0] a_s_req_address;
 wire [127:0] a_s_req_data;
 wire a_s_rsp_valid;
 wire a_s_rsp_error;
 wire a_s_rsp_ready;
 wire [127:0] a_s_rsp_data;
 wire a_resource_e_in_valid;
 wire a_resource_e_in_ready;
 wire [63:0] a_resource_e_in_data;
 wire [3:0] a_resource_e_in_op;
 wire [3:0] a_resource_e_in_mask;
 wire [7:0] a_resource_e_in_shift;
 wire [2:0] a_resource_e_in_minus;
 wire a_resource_e_out_valid;
 wire a_resource_e_out_ready;
 wire [63:0] a_resource_e_out_data;
 wire [3:0] a_resource_e_out_clipped;
 wire a_resource_e_out_error;
 wire r_s_req_valid;
 wire r_s_req_ready;
 wire r_s_req_write;
 wire [9:0] r_s_req_address;
 wire [127:0] r_s_req_data;
 wire r_s_rsp_valid;
 wire r_s_rsp_ready;
 wire [127:0] r_s_rsp_data;
 wire r_s_rsp_error;
 wire r_resource_e_in_valid;
 wire r_resource_e_in_ready;
 wire [63:0] r_resource_e_in_data;
 wire [3:0] r_resource_e_in_op;
 wire [3:0] r_resource_e_in_mask;
 wire [7:0] r_resource_e_in_shift;
 wire [2:0] r_resource_e_in_minus;
 wire r_resource_e_out_valid;
 wire r_resource_e_out_ready;
 wire [63:0] r_resource_e_out_data;
 wire [3:0] r_resource_e_out_clipped;
 wire r_resource_e_out_error;
 wire n_s_req_valid;
 wire n_s_req_ready;
 wire n_s_req_write;
 wire [9:0] n_s_req_address;
 wire [127:0] n_s_req_data;
 wire n_s_rsp_valid;
 wire n_s_rsp_ready;
 wire [127:0] n_s_rsp_data;
 wire n_s_rsp_error;
 wire n_resource_e_in_valid;
 wire n_resource_e_in_ready;
 wire [63:0] n_resource_e_in_data;
 wire [3:0] n_resource_e_in_op;
 wire [3:0] n_resource_e_in_mask;
 wire [7:0] n_resource_e_in_shift;
 wire [2:0] n_resource_e_in_minus;
 wire n_resource_e_out_valid;
 wire n_resource_e_out_ready;
 wire [63:0] n_resource_e_out_data;
 wire [3:0] n_resource_e_out_clipped;
 wire n_resource_e_out_error;
 e32_dot_service_controller #(.TOPOLOGY(TOPOLOGY)) p(.clk(clk),.reset(reset),.service_valid(provider_valid[0]),.service_ready(provider_ready[0]),.service_owner(provider_owner),.service_ticket(provider_ticket),.service_descriptor(provider_descriptor),.service_cancel_valid(provider_cancel_valid[0]),.service_cancel_ready(provider_cancel_ready[0]),.service_done_valid(provider_done_valid[0]),.service_done_ready(provider_done_ready[0]),.service_done_owner(provider_done_owner[0+:128]),.service_done_ticket(provider_done_ticket[0+:32]),.service_done_status(provider_done_status[0+:16]),.service_done_read_bytes(provider_done_read_bytes[0+:32]),.service_done_write_bytes(provider_done_write_bytes[0+:32]),.rd_valid(p_rd_valid),.rd_ready(p_rd_ready),.rd_address(p_rd_address),.rd_tag(p_rd_tag),.rd_rsp_valid(p_rd_rsp_valid),.rd_rsp_ready(p_rd_rsp_ready),.rd_rsp_tag(p_rd_rsp_tag),.rd_rsp_data(p_rd_rsp_data),.rd_rsp_error(p_rd_rsp_error),.s_req_valid(p_s_req_valid),.s_req_write(p_s_req_write),.s_req_ready(p_s_req_ready),.s_req_address(p_s_req_address),.s_req_data(p_s_req_data),.s_rsp_valid(p_s_rsp_valid),.s_rsp_ready(p_s_rsp_ready),.s_rsp_data(p_s_rsp_data),.s_rsp_error(p_s_rsp_error),.resource_e_in_valid(p_resource_e_in_valid),.resource_e_in_ready(p_resource_e_in_ready),.resource_e_in_data(p_resource_e_in_data),.resource_e_in_op(p_resource_e_in_op),.resource_e_in_mask(p_resource_e_in_mask),.resource_e_in_shift(p_resource_e_in_shift),.resource_e_in_minus(p_resource_e_in_minus),.resource_e_out_valid(p_resource_e_out_valid),.resource_e_out_ready(p_resource_e_out_ready),.resource_e_out_data(p_resource_e_out_data),.resource_e_out_clipped(p_resource_e_out_clipped),.resource_e_out_error(p_resource_e_out_error));
 add_s32_service_controller #(.TOPOLOGY(TOPOLOGY)) a(.clk(clk),.reset(reset),.service_valid(provider_valid[3]),.service_ready(provider_ready[3]),.service_owner(provider_owner),.service_ticket(provider_ticket),.service_descriptor(provider_descriptor),.service_cancel_valid(provider_cancel_valid[3]),.service_cancel_ready(provider_cancel_ready[3]),.service_done_valid(provider_done_valid[3]),.service_done_ready(provider_done_ready[3]),.service_done_owner(provider_done_owner[384+:128]),.service_done_ticket(provider_done_ticket[96+:32]),.service_done_status(provider_done_status[48+:16]),.service_done_read_bytes(provider_done_read_bytes[96+:32]),.service_done_write_bytes(provider_done_write_bytes[96+:32]),.s_req_valid(a_s_req_valid),.s_req_write(a_s_req_write),.s_req_ready(a_s_req_ready),.s_req_address(a_s_req_address),.s_req_data(a_s_req_data),.s_rsp_valid(a_s_rsp_valid),.s_rsp_error(a_s_rsp_error),.s_rsp_ready(a_s_rsp_ready),.s_rsp_data(a_s_rsp_data),.resource_e_in_valid(a_resource_e_in_valid),.resource_e_in_ready(a_resource_e_in_ready),.resource_e_in_data(a_resource_e_in_data),.resource_e_in_op(a_resource_e_in_op),.resource_e_in_mask(a_resource_e_in_mask),.resource_e_in_shift(a_resource_e_in_shift),.resource_e_in_minus(a_resource_e_in_minus),.resource_e_out_valid(a_resource_e_out_valid),.resource_e_out_ready(a_resource_e_out_ready),.resource_e_out_data(a_resource_e_out_data),.resource_e_out_clipped(a_resource_e_out_clipped),.resource_e_out_error(a_resource_e_out_error));
 rope_native_service_controller #(.TOPOLOGY(TOPOLOGY)) r(.clk(clk),.reset(reset),.service_valid(provider_valid[4]),.service_ready(provider_ready[4]),.service_owner(provider_owner),.service_ticket(provider_ticket),.service_descriptor(provider_descriptor),.service_cancel_valid(provider_cancel_valid[4]),.service_cancel_ready(provider_cancel_ready[4]),.service_done_valid(provider_done_valid[4]),.service_done_ready(provider_done_ready[4]),.service_done_owner(provider_done_owner[512+:128]),.service_done_ticket(provider_done_ticket[128+:32]),.service_done_status(provider_done_status[64+:16]),.service_done_read_bytes(provider_done_read_bytes[128+:32]),.service_done_write_bytes(provider_done_write_bytes[128+:32]),.s_req_valid(r_s_req_valid),.s_req_ready(r_s_req_ready),.s_req_write(r_s_req_write),.s_req_address(r_s_req_address),.s_req_data(r_s_req_data),.s_rsp_valid(r_s_rsp_valid),.s_rsp_ready(r_s_rsp_ready),.s_rsp_data(r_s_rsp_data),.s_rsp_error(r_s_rsp_error),.resource_e_in_valid(r_resource_e_in_valid),.resource_e_in_ready(r_resource_e_in_ready),.resource_e_in_data(r_resource_e_in_data),.resource_e_in_op(r_resource_e_in_op),.resource_e_in_mask(r_resource_e_in_mask),.resource_e_in_shift(r_resource_e_in_shift),.resource_e_in_minus(r_resource_e_in_minus),.resource_e_out_valid(r_resource_e_out_valid),.resource_e_out_ready(r_resource_e_out_ready),.resource_e_out_data(r_resource_e_out_data),.resource_e_out_clipped(r_resource_e_out_clipped),.resource_e_out_error(r_resource_e_out_error));
 rms_apply_native_service_controller #(.TOPOLOGY(TOPOLOGY)) n(.clk(clk),.reset(reset),.service_valid(provider_valid[5]),.service_ready(provider_ready[5]),.service_owner(provider_owner),.service_ticket(provider_ticket),.service_descriptor(provider_descriptor),.service_cancel_valid(provider_cancel_valid[5]),.service_cancel_ready(provider_cancel_ready[5]),.service_done_valid(provider_done_valid[5]),.service_done_ready(provider_done_ready[5]),.service_done_owner(provider_done_owner[640+:128]),.service_done_ticket(provider_done_ticket[160+:32]),.service_done_status(provider_done_status[80+:16]),.service_done_read_bytes(provider_done_read_bytes[160+:32]),.service_done_write_bytes(provider_done_write_bytes[160+:32]),.s_req_valid(n_s_req_valid),.s_req_ready(n_s_req_ready),.s_req_write(n_s_req_write),.s_req_address(n_s_req_address),.s_req_data(n_s_req_data),.s_rsp_valid(n_s_rsp_valid),.s_rsp_ready(n_s_rsp_ready),.s_rsp_data(n_s_rsp_data),.s_rsp_error(n_s_rsp_error),.resource_e_in_valid(n_resource_e_in_valid),.resource_e_in_ready(n_resource_e_in_ready),.resource_e_in_data(n_resource_e_in_data),.resource_e_in_op(n_resource_e_in_op),.resource_e_in_mask(n_resource_e_in_mask),.resource_e_in_shift(n_resource_e_in_shift),.resource_e_in_minus(n_resource_e_in_minus),.resource_e_out_valid(n_resource_e_out_valid),.resource_e_out_ready(n_resource_e_out_ready),.resource_e_out_data(n_resource_e_out_data),.resource_e_out_clipped(n_resource_e_out_clipped),.resource_e_out_error(n_resource_e_out_error));
 ddr_s128_load_scope #(.TOPOLOGY(TOPOLOGY),.PAYLOAD_BYTES(512),.LOCAL_DMA_SEQUENCE(1'b1)) l(.clk(clk),.reset(reset),.service_valid(provider_valid[1]),.service_ready(provider_ready[1]),.service_owner(provider_owner),.service_ticket(provider_ticket),.service_descriptor(provider_descriptor),.service_cancel_valid(provider_cancel_valid[1]),.service_cancel_ready(provider_cancel_ready[1]),.service_done_valid(provider_done_valid[1]),.service_done_ready(provider_done_ready[1]),.service_done_owner(provider_done_owner[128+:128]),.service_done_ticket(provider_done_ticket[32+:32]),.service_done_status(provider_done_status[16+:16]),.service_done_read_bytes(provider_done_read_bytes[32+:32]),.service_done_write_bytes(provider_done_write_bytes[32+:32]),.rd_valid(l_rd_valid),.rd_ready(l_rd_ready),.rd_address(l_rd_address),.rd_tag(l_rd_tag),.rd_rsp_valid(l_rd_rsp_valid),.rd_rsp_ready(l_rd_rsp_ready),.rd_rsp_tag(l_rd_rsp_tag),.rd_rsp_data(l_rd_rsp_data),.rd_rsp_error(l_rd_rsp_error),.s_valid(l_s_valid),.s_ready(l_s_ready),.s_address(l_s_address),.s_data(l_s_data),.s_tag(l_s_tag),.s_rsp_valid(l_s_rsp_valid),.s_rsp_ready(l_s_rsp_ready),.s_rsp_tag(l_s_rsp_tag),.s_rsp_error(l_s_rsp_error));
 s128_kv_store_scope #(.TOPOLOGY(TOPOLOGY),.ACTIVATION_SPAN(1'b1)) w(.clk(clk),.reset(reset),.service_valid(provider_valid[2]),.service_ready(provider_ready[2]),.service_owner(provider_owner),.service_ticket(provider_ticket),.service_descriptor(provider_descriptor),.service_cancel_valid(provider_cancel_valid[2]),.service_cancel_ready(provider_cancel_ready[2]),.service_done_valid(provider_done_valid[2]),.service_done_ready(provider_done_ready[2]),.service_done_owner(provider_done_owner[256+:128]),.service_done_ticket(provider_done_ticket[64+:32]),.service_done_status(provider_done_status[32+:16]),.service_done_read_bytes(provider_done_read_bytes[64+:32]),.service_done_write_bytes(provider_done_write_bytes[64+:32]),.s_req_valid(w_s_req_valid),.s_req_ready(w_s_req_ready),.s_req_address(w_s_req_address),.s_rsp_valid(w_s_rsp_valid),.s_rsp_ready(w_s_rsp_ready),.s_rsp_data(w_s_rsp_data),.s_rsp_error(w_s_rsp_error),.wr_valid(wr_valid),.wr_ready(wr_ready),.wr_address(wr_address),.wr_tag(wr_tag),.wr_data(wr_data),.wr_done_valid(wr_done_valid),.wr_done_ready(wr_done_ready),.wr_done_tag(wr_done_tag),.wr_done_error(wr_done_error));
 wire [3:0]client_in_valid;
 assign client_in_valid[0]=a_resource_e_in_valid;
 assign client_in_valid[1]=r_resource_e_in_valid;
 assign client_in_valid[2]=n_resource_e_in_valid;
 assign client_in_valid[3]=p_resource_e_in_valid;
 wire [3:0]client_in_ready;
 assign a_resource_e_in_ready=client_in_ready[0];
 assign r_resource_e_in_ready=client_in_ready[1];
 assign n_resource_e_in_ready=client_in_ready[2];
 assign p_resource_e_in_ready=client_in_ready[3];
 wire [3:0][63:0]client_in_data;
 assign client_in_data[0]=a_resource_e_in_data;
 assign client_in_data[1]=r_resource_e_in_data;
 assign client_in_data[2]=n_resource_e_in_data;
 assign client_in_data[3]=p_resource_e_in_data;
 wire [3:0][3:0]client_in_op;
 assign client_in_op[0]=a_resource_e_in_op;
 assign client_in_op[1]=r_resource_e_in_op;
 assign client_in_op[2]=n_resource_e_in_op;
 assign client_in_op[3]=p_resource_e_in_op;
 wire [3:0][3:0]client_in_mask;
 assign client_in_mask[0]=a_resource_e_in_mask;
 assign client_in_mask[1]=r_resource_e_in_mask;
 assign client_in_mask[2]=n_resource_e_in_mask;
 assign client_in_mask[3]=p_resource_e_in_mask;
 wire [3:0][7:0]client_in_shift;
 assign client_in_shift[0]=a_resource_e_in_shift;
 assign client_in_shift[1]=r_resource_e_in_shift;
 assign client_in_shift[2]=n_resource_e_in_shift;
 assign client_in_shift[3]=p_resource_e_in_shift;
 wire [3:0][2:0]client_in_minus;
 assign client_in_minus[0]=a_resource_e_in_minus;
 assign client_in_minus[1]=r_resource_e_in_minus;
 assign client_in_minus[2]=n_resource_e_in_minus;
 assign client_in_minus[3]=p_resource_e_in_minus;
 wire [3:0]client_out_valid;
 assign a_resource_e_out_valid=client_out_valid[0];
 assign r_resource_e_out_valid=client_out_valid[1];
 assign n_resource_e_out_valid=client_out_valid[2];
 assign p_resource_e_out_valid=client_out_valid[3];
 wire [3:0]client_out_ready;
 assign client_out_ready[0]=a_resource_e_out_ready;
 assign client_out_ready[1]=r_resource_e_out_ready;
 assign client_out_ready[2]=n_resource_e_out_ready;
 assign client_out_ready[3]=p_resource_e_out_ready;
 wire [3:0][63:0]client_out_data;
 assign a_resource_e_out_data=client_out_data[0];
 assign r_resource_e_out_data=client_out_data[1];
 assign n_resource_e_out_data=client_out_data[2];
 assign p_resource_e_out_data=client_out_data[3];
 wire [3:0][3:0]client_out_clipped;
 assign a_resource_e_out_clipped=client_out_clipped[0];
 assign r_resource_e_out_clipped=client_out_clipped[1];
 assign n_resource_e_out_clipped=client_out_clipped[2];
 assign p_resource_e_out_clipped=client_out_clipped[3];
 wire [3:0]client_out_error;
 assign a_resource_e_out_error=client_out_error[0];
 assign r_resource_e_out_error=client_out_error[1];
 assign n_resource_e_out_error=client_out_error[2];
 assign p_resource_e_out_error=client_out_error[3];
 e32_service_selector #(.CLIENTS(4),.MAC_CONTEXT(1)) e_selector(.clk(clk),.reset(reset),.busy(),.client_in_valid(client_in_valid),.macro_in_valid(resource_e_in_valid),.client_in_ready(client_in_ready),.macro_in_ready(resource_e_in_ready),.client_in_data(client_in_data),.macro_in_data(resource_e_in_data),.client_in_op(client_in_op),.macro_in_op(resource_e_in_op),.client_in_mask(client_in_mask),.macro_in_mask(resource_e_in_mask),.client_in_shift(client_in_shift),.macro_in_shift(resource_e_in_shift),.client_in_minus(client_in_minus),.macro_in_minus(resource_e_in_minus),.client_out_valid(client_out_valid),.macro_out_valid(resource_e_out_valid),.client_out_ready(client_out_ready),.macro_out_ready(resource_e_out_ready),.client_out_data(client_out_data),.macro_out_data(resource_e_out_data),.client_out_clipped(client_out_clipped),.macro_out_clipped(resource_e_out_clipped),.client_out_error(client_out_error),.macro_out_error(resource_e_out_error));

 wire [3:0] c_ready,c_valid;
 wire [127:0] c_tag,c_data;
 wire [1:0] owners;
 native_s128_mux4 sram_arbiter(.clk,.reset,
  .c_valid({x_s_req_valid,w_s_req_valid,l_s_valid,p_s_req_valid}),
  .c_write({x_s_req_write,1'b0,1'b1,p_s_req_write}),
  .c_address({x_s_req_address,w_s_req_address,l_s_address,p_s_req_address}),
  .c_data({x_s_req_data,128'd0,l_s_data,p_s_req_data}),
  .c_tag({32'd0,32'd0,l_s_tag,32'd0}),.c_ready,
  .c_response_valid(c_valid),.c_response_ready({x_s_rsp_ready,w_s_rsp_ready,l_s_rsp_ready,p_s_rsp_ready}),
  .c_response_data(c_data),.c_response_tag(c_tag),.owners_occupied(owners),
  .req_valid(s_req_valid),.req_write(s_req_write),.req_address(s_req_address),.req_data(s_req_data),
  .req_ready(s_req_ready),.rsp_valid(s_rsp_valid),.rsp_ready(s_rsp_ready),.rsp_data(s_rsp_data));
 assign p_s_req_ready=c_ready[0];assign l_s_ready=c_ready[1];assign w_s_req_ready=c_ready[2];
 assign p_s_rsp_valid=c_valid[0];assign l_s_rsp_valid=c_valid[1];assign w_s_rsp_valid=c_valid[2];
 assign p_s_rsp_data=c_data;assign w_s_rsp_data=c_data;assign l_s_rsp_tag=c_tag[63:32];
 assign p_s_rsp_error=s_rsp_error;assign l_s_rsp_error=s_rsp_error;assign w_s_rsp_error=s_rsp_error;
 wire x_s_req_valid,x_s_req_write,x_s_rsp_ready;
 wire [9:0] x_s_req_address;wire [127:0] x_s_req_data;
 wire [2:0] pair_ready,pair_valid;
 s128_service_selector #(.CLIENTS(3)) elementwise_sram_selector(.clk,.reset,
 .c_valid({n_s_req_valid,r_s_req_valid,a_s_req_valid}),.c_write({n_s_req_write,r_s_req_write,a_s_req_write}),
 .c_ready(pair_ready),.c_response_valid(pair_valid),
 .c_response_ready({n_s_rsp_ready,r_s_rsp_ready,a_s_rsp_ready}),
 .c_address({n_s_req_address,r_s_req_address,a_s_req_address}),.c_data({n_s_req_data,r_s_req_data,a_s_req_data}),
 .req_valid(x_s_req_valid),.req_write(x_s_req_write),.req_ready(c_ready[3]),
 .req_address(x_s_req_address),.req_data(x_s_req_data),
 .rsp_valid(c_valid[3]),.rsp_ready(x_s_rsp_ready));
 assign a_s_req_ready=pair_ready[0];assign a_s_rsp_valid=pair_valid[0];
 assign r_s_req_ready=pair_ready[1];assign r_s_rsp_valid=pair_valid[1];
 assign r_s_rsp_data=c_data;assign r_s_rsp_error=s_rsp_error;
 assign n_s_req_ready=pair_ready[2];assign n_s_rsp_valid=pair_valid[2];
 assign n_s_rsp_data=c_data;assign n_s_rsp_error=s_rsp_error;
 assign a_s_rsp_data=c_data;assign a_s_rsp_error=s_rsp_error;
 // Four bounded read slots retain original tags and owners across reordered returns.
 reg [3:0] read_used,read_sent;
 reg [1:0] read_tail,read_issue;
 reg [63:0] read_sequence;
 reg [63:0] read_original[0:3],read_token[0:3],read_address[0:3];
 reg [3:0] read_owner;
 wire choose_load=!p_rd_valid;
 wire accept_read=!reset&&!read_used[read_tail];
 assign p_rd_ready=accept_read&&!choose_load;
 assign l_rd_ready=accept_read&&choose_load;
 assign rd_valid=!reset&&read_used[read_issue]&&!read_sent[read_issue];
 assign rd_address=read_address[read_issue];
 assign rd_tag=read_token[read_issue];
 reg response_match;reg [1:0] response_slot;
 integer ri;
 always @*begin
  response_match=0;response_slot=0;
  for(integer j=0;j<4;j=j+1)
   if(read_used[j]&&read_sent[j]&&read_token[j]==rd_rsp_tag)begin response_match=1;response_slot=j;end
 end
 assign p_rd_rsp_valid=!reset&&rd_rsp_valid&&response_match&&!read_owner[response_slot];
 assign l_rd_rsp_valid=!reset&&rd_rsp_valid&&response_match&&read_owner[response_slot];
 assign p_rd_rsp_tag=read_original[response_slot];assign l_rd_rsp_tag=read_original[response_slot];
 assign p_rd_rsp_data=rd_rsp_data;assign l_rd_rsp_data=rd_rsp_data;
 assign p_rd_rsp_error=rd_rsp_error;assign l_rd_rsp_error=rd_rsp_error;
 assign rd_rsp_ready=!reset&&response_match&&(read_owner[response_slot]?l_rd_rsp_ready:p_rd_rsp_ready);
 always @(posedge clk)begin
  if(reset)begin
   read_used<=0;read_sent<=0;read_tail<=0;read_issue<=0;read_sequence<=0;read_owner<=0;
   for(ri=0;ri<4;ri=ri+1)begin read_original[ri]<=0;read_token[ri]<=0;read_address[ri]<=0;end
  end else begin
   if((p_rd_valid&&p_rd_ready)||(l_rd_valid&&l_rd_ready))begin
    read_used[read_tail]<=1;read_sent[read_tail]<=0;read_owner[read_tail]<=choose_load;
    read_original[read_tail]<=choose_load?l_rd_tag:p_rd_tag;
    read_address[read_tail]<=choose_load?l_rd_address:p_rd_address;
    read_token[read_tail]<=read_sequence;read_sequence<=read_sequence+1;read_tail<=read_tail+1;
   end
   if(rd_valid&&rd_ready)begin read_sent[read_issue]<=1;read_issue<=read_issue+1;end
   if(rd_rsp_valid&&rd_rsp_ready)begin read_used[response_slot]<=0;read_sent[response_slot]<=0;end
  end
 end
endmodule
