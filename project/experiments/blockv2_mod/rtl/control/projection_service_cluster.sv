// Parent standard cells only. No U/P link or functional macro is instantiated.
module projection_service_cluster #(parameter logic [31:0] TOPOLOGY=0)(
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
 output wire resource_m_lc_valid,
 input wire resource_m_lc_ready,
 output wire resource_m_lc_sop,
 output wire resource_m_lc_eop,
 output wire [127:0] resource_m_lc_data,
 input wire resource_m_lr_valid,
 output wire resource_m_lr_ready,
 input wire resource_m_lr_sop,
 input wire resource_m_lr_eop,
 input wire [127:0] resource_m_lr_data,
 output wire resource_m_a_valid,
 input wire resource_m_a_ready,
 output wire [255:0] resource_m_a_data,
 output wire [31:0] resource_m_a_session,
 output wire [2:0] resource_m_a_beat,
 output wire s_req_valid,
 output wire s_req_write,
 input wire s_req_ready,
 output wire [9:0] s_req_address,
 output wire [127:0] s_req_data,
 input wire s_rsp_valid,
 output wire s_rsp_ready,
 input wire [127:0] s_rsp_data,
 input wire s_rsp_error,
 output wire rd_valid,
 input wire rd_ready,
 output wire [63:0] rd_address,
 output wire [63:0] rd_tag,
 input wire rd_rsp_valid,
 output wire rd_rsp_ready,
 input wire [63:0] rd_rsp_tag,
 input wire [511:0] rd_rsp_data,
 input wire rd_rsp_error,
 output wire source_failed,
 output wire quarantine,
 output wire [31:0] protocol_faults,
 output wire resource_g_in_valid,
 input wire resource_g_in_ready,
 output wire [63:0] resource_g_in_gate,
 output wire [63:0] resource_g_in_up,
 output wire resource_g_in_gated,
 output wire [1:0] resource_g_in_mask,
 input wire resource_g_out_valid,
 output wire resource_g_out_ready,
 input wire [63:0] resource_g_out_data,
 input wire [1:0] resource_g_out_mask,
 input wire resource_g_out_error,
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
 wire [3:0] provider_valid,provider_ready,provider_cancel_valid,provider_cancel_ready;
 wire [3:0] provider_done_valid,provider_done_ready;
 wire [127:0] provider_owner;wire [31:0] provider_ticket;wire [1023:0] provider_descriptor;
 wire [511:0] provider_done_owner;wire [127:0] provider_done_ticket;
 wire [63:0] provider_done_status;wire [127:0] provider_done_read_bytes,provider_done_write_bytes;
 macro_service_dispatch #(.SLOTS(4),.ROUTES(4),.TOPOLOGY(TOPOLOGY),
  .SCHEMAS({32'h314d5347,32'h31535744,32'h314c5244,32'h3152504d}),
  .ABIS({32'h02500002,32'h02500002,32'h02500002,32'h02504d03}),
  .OPCODES({16'd1,16'd1,16'd1,16'd2}),.SLOT_MAP({8'd3,8'd2,8'd1,8'd0})) dispatch(.*);
 wire p_s_req_valid;
 wire p_s_req_write;
 wire p_s_req_ready;
 wire [9:0] p_s_req_address;
 wire [127:0] p_s_req_data;
 wire p_s_rsp_valid;
 wire p_s_rsp_ready;
 wire [127:0] p_s_rsp_data;
 wire p_s_rsp_error;
 wire p_rd_valid;
 wire p_rd_ready;
 wire [63:0] p_rd_address;
 wire [63:0] p_rd_tag;
 wire p_rd_rsp_valid;
 wire p_rd_rsp_ready;
 wire [63:0] p_rd_rsp_tag;
 wire [511:0] p_rd_rsp_data;
 wire p_rd_rsp_error;
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
 wire g_s_req_valid;
 wire g_s_req_write;
 wire g_s_req_ready;
 wire [9:0] g_s_req_address;
 wire [127:0] g_s_req_data;
 wire g_s_rsp_valid;
 wire g_s_rsp_ready;
 wire [127:0] g_s_rsp_data;
 projection_local_service_controller #(.TOPOLOGY(TOPOLOGY)) p(.clk(clk),.reset(reset),.service_valid(provider_valid[0]),.service_ready(provider_ready[0]),.service_owner(provider_owner),.service_ticket(provider_ticket),.service_descriptor(provider_descriptor),.service_cancel_valid(provider_cancel_valid[0]),.service_cancel_ready(provider_cancel_ready[0]),.service_done_valid(provider_done_valid[0]),.service_done_ready(provider_done_ready[0]),.service_done_owner(provider_done_owner[0+:128]),.service_done_ticket(provider_done_ticket[0+:32]),.service_done_status(provider_done_status[0+:16]),.service_done_read_bytes(provider_done_read_bytes[0+:32]),.service_done_write_bytes(provider_done_write_bytes[0+:32]),.resource_m_lc_valid(resource_m_lc_valid),.resource_m_lc_ready(resource_m_lc_ready),.resource_m_lc_sop(resource_m_lc_sop),.resource_m_lc_eop(resource_m_lc_eop),.resource_m_lc_data(resource_m_lc_data),.resource_m_lr_valid(resource_m_lr_valid),.resource_m_lr_ready(resource_m_lr_ready),.resource_m_lr_sop(resource_m_lr_sop),.resource_m_lr_eop(resource_m_lr_eop),.resource_m_lr_data(resource_m_lr_data),.resource_m_a_valid(resource_m_a_valid),.resource_m_a_ready(resource_m_a_ready),.resource_m_a_data(resource_m_a_data),.resource_m_a_session(resource_m_a_session),.resource_m_a_beat(resource_m_a_beat),.s_req_valid(p_s_req_valid),.s_req_write(p_s_req_write),.s_req_ready(p_s_req_ready),.s_req_address(p_s_req_address),.s_req_data(p_s_req_data),.s_rsp_valid(p_s_rsp_valid),.s_rsp_ready(p_s_rsp_ready),.s_rsp_data(p_s_rsp_data),.s_rsp_error(p_s_rsp_error),.rd_valid(p_rd_valid),.rd_ready(p_rd_ready),.rd_address(p_rd_address),.rd_tag(p_rd_tag),.rd_rsp_valid(p_rd_rsp_valid),.rd_rsp_ready(p_rd_rsp_ready),.rd_rsp_tag(p_rd_rsp_tag),.rd_rsp_data(p_rd_rsp_data),.rd_rsp_error(p_rd_rsp_error),.source_failed(source_failed),.quarantine(quarantine),.protocol_faults(protocol_faults));
 ddr_s128_load_scope #(.TOPOLOGY(TOPOLOGY),.PAYLOAD_BYTES(512),.LOCAL_DMA_SEQUENCE(1'b1)) l(.clk(clk),.reset(reset),.service_valid(provider_valid[1]),.service_ready(provider_ready[1]),.service_owner(provider_owner),.service_ticket(provider_ticket),.service_descriptor(provider_descriptor),.service_cancel_valid(provider_cancel_valid[1]),.service_cancel_ready(provider_cancel_ready[1]),.service_done_valid(provider_done_valid[1]),.service_done_ready(provider_done_ready[1]),.service_done_owner(provider_done_owner[128+:128]),.service_done_ticket(provider_done_ticket[32+:32]),.service_done_status(provider_done_status[16+:16]),.service_done_read_bytes(provider_done_read_bytes[32+:32]),.service_done_write_bytes(provider_done_write_bytes[32+:32]),.rd_valid(l_rd_valid),.rd_ready(l_rd_ready),.rd_address(l_rd_address),.rd_tag(l_rd_tag),.rd_rsp_valid(l_rd_rsp_valid),.rd_rsp_ready(l_rd_rsp_ready),.rd_rsp_tag(l_rd_rsp_tag),.rd_rsp_data(l_rd_rsp_data),.rd_rsp_error(l_rd_rsp_error),.s_valid(l_s_valid),.s_ready(l_s_ready),.s_address(l_s_address),.s_data(l_s_data),.s_tag(l_s_tag),.s_rsp_valid(l_s_rsp_valid),.s_rsp_ready(l_s_rsp_ready),.s_rsp_tag(l_s_rsp_tag),.s_rsp_error(l_s_rsp_error));
 s128_kv_store_scope #(.TOPOLOGY(TOPOLOGY),.ACTIVATION_SPAN(1'b1)) w(.clk(clk),.reset(reset),.service_valid(provider_valid[2]),.service_ready(provider_ready[2]),.service_owner(provider_owner),.service_ticket(provider_ticket),.service_descriptor(provider_descriptor),.service_cancel_valid(provider_cancel_valid[2]),.service_cancel_ready(provider_cancel_ready[2]),.service_done_valid(provider_done_valid[2]),.service_done_ready(provider_done_ready[2]),.service_done_owner(provider_done_owner[256+:128]),.service_done_ticket(provider_done_ticket[64+:32]),.service_done_status(provider_done_status[32+:16]),.service_done_read_bytes(provider_done_read_bytes[64+:32]),.service_done_write_bytes(provider_done_write_bytes[64+:32]),.s_req_valid(w_s_req_valid),.s_req_ready(w_s_req_ready),.s_req_address(w_s_req_address),.s_rsp_valid(w_s_rsp_valid),.s_rsp_ready(w_s_rsp_ready),.s_rsp_data(w_s_rsp_data),.s_rsp_error(w_s_rsp_error),.wr_valid(wr_valid),.wr_ready(wr_ready),.wr_address(wr_address),.wr_tag(wr_tag),.wr_data(wr_data),.wr_done_valid(wr_done_valid),.wr_done_ready(wr_done_ready),.wr_done_tag(wr_done_tag),.wr_done_error(wr_done_error));
 gated_s32_service_controller #(.TOPOLOGY(TOPOLOGY)) g(.clk(clk),.reset(reset),.service_valid(provider_valid[3]),.service_ready(provider_ready[3]),.service_owner(provider_owner),.service_ticket(provider_ticket),.service_descriptor(provider_descriptor),.service_cancel_valid(provider_cancel_valid[3]),.service_cancel_ready(provider_cancel_ready[3]),.service_done_valid(provider_done_valid[3]),.service_done_ready(provider_done_ready[3]),.service_done_ticket(provider_done_ticket[96+:32]),.service_done_owner(provider_done_owner[384+:128]),.service_done_status(provider_done_status[48+:16]),.service_done_read_bytes(provider_done_read_bytes[96+:32]),.service_done_write_bytes(provider_done_write_bytes[96+:32]),.s_req_valid(g_s_req_valid),.s_req_write(g_s_req_write),.s_req_ready(g_s_req_ready),.s_req_address(g_s_req_address),.s_req_data(g_s_req_data),.s_rsp_valid(g_s_rsp_valid),.s_rsp_ready(g_s_rsp_ready),.s_rsp_data(g_s_rsp_data),.resource_g_in_valid(resource_g_in_valid),.resource_g_in_ready(resource_g_in_ready),.resource_g_in_gate(resource_g_in_gate),.resource_g_in_up(resource_g_in_up),.resource_g_in_gated(resource_g_in_gated),.resource_g_in_mask(resource_g_in_mask),.resource_g_out_valid(resource_g_out_valid),.resource_g_out_ready(resource_g_out_ready),.resource_g_out_data(resource_g_out_data),.resource_g_out_mask(resource_g_out_mask),.resource_g_out_error(resource_g_out_error));

 wire [3:0] c_ready,c_valid;
 wire [127:0] c_tag,c_data;
 wire [1:0] owners;
 native_s128_mux4 sram_arbiter(.clk,.reset,
  .c_valid({g_s_req_valid,w_s_req_valid,l_s_valid,p_s_req_valid}),
  .c_write({g_s_req_write,1'b0,1'b1,p_s_req_write}),
  .c_address({g_s_req_address,w_s_req_address,l_s_address,p_s_req_address}),
  .c_data({g_s_req_data,128'd0,l_s_data,p_s_req_data}),
  .c_tag({32'd0,32'd0,l_s_tag,32'd0}),.c_ready,
  .c_response_valid(c_valid),.c_response_ready({g_s_rsp_ready,w_s_rsp_ready,l_s_rsp_ready,p_s_rsp_ready}),
  .c_response_data(c_data),.c_response_tag(c_tag),.owners_occupied(owners),
  .req_valid(s_req_valid),.req_write(s_req_write),.req_address(s_req_address),.req_data(s_req_data),
  .req_ready(s_req_ready),.rsp_valid(s_rsp_valid),.rsp_ready(s_rsp_ready),.rsp_data(s_rsp_data));
 assign g_s_req_ready=c_ready[3];assign g_s_rsp_valid=c_valid[3];assign g_s_rsp_data=c_data;
 assign p_s_req_ready=c_ready[0];assign l_s_ready=c_ready[1];assign w_s_req_ready=c_ready[2];
 assign p_s_rsp_valid=c_valid[0];assign l_s_rsp_valid=c_valid[1];assign w_s_rsp_valid=c_valid[2];
 assign p_s_rsp_data=c_data;assign w_s_rsp_data=c_data;assign l_s_rsp_tag=c_tag[63:32];
 assign p_s_rsp_error=s_rsp_error;assign l_s_rsp_error=s_rsp_error;assign w_s_rsp_error=s_rsp_error;
 // Both admitted read services are serial. One held response keeps its owner.
 reg read_busy,read_owner;
 wire choose_load=!p_rd_valid;
 assign rd_valid=!reset&&!read_busy&&(p_rd_valid||l_rd_valid);
 assign rd_address=choose_load?l_rd_address:p_rd_address;
 assign rd_tag=choose_load?l_rd_tag:p_rd_tag;
 assign p_rd_ready=!reset&&!read_busy&&!choose_load&&rd_ready;
 assign l_rd_ready=!reset&&!read_busy&&choose_load&&rd_ready;
 assign p_rd_rsp_valid=rd_rsp_valid&&read_busy&&!read_owner;
 assign l_rd_rsp_valid=rd_rsp_valid&&read_busy&&read_owner;
 assign p_rd_rsp_tag=rd_rsp_tag;assign l_rd_rsp_tag=rd_rsp_tag;
 assign p_rd_rsp_data=rd_rsp_data;assign l_rd_rsp_data=rd_rsp_data;
 assign p_rd_rsp_error=rd_rsp_error;assign l_rd_rsp_error=rd_rsp_error;
 assign rd_rsp_ready=read_busy&&(read_owner?l_rd_rsp_ready:p_rd_rsp_ready);
 always @(posedge clk)begin
  if(reset)begin read_busy<=0;read_owner<=0;end
  else begin
   if(rd_valid&&rd_ready)begin read_busy<=1;read_owner<=choose_load;end
   if(rd_rsp_valid&&rd_rsp_ready)read_busy<=0;
  end
 end
endmodule

