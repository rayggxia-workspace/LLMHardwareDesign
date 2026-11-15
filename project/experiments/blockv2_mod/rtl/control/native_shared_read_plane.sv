// Parent standard cells: explicit fixed DMA control links, no functional macros or U/P data wiring.
module native_shared_read_plane #(parameter logic [30:0] SERVICE_SERIAL_LIMIT=31'h7fffffff,
 parameter logic [15:0] TRANSPORT_SERIAL_LIMIT=16'hffff)(
input wire clk,
input wire reset,
input wire [11:0] c_req_valid,
output wire [11:0] c_req_ready,
input wire [767:0] c_req_address,
input wire [383:0] c_req_tag,
input wire [11:0] c_req_channel,
input wire [59:0] c_req_record_beats,
output wire [11:0] c_rsp_valid,
input wire [11:0] c_rsp_ready,
output wire [383:0] c_rsp_tag,
output wire [6143:0] c_rsp_data,
input wire [11:0] c_close_valid,
output wire [11:0] c_close_ready,
input wire [383:0] c_close_tag_base,
input wire [11:0] c_cancel_valid,
output wire [11:0] c_cancel_ready,
input wire [383:0] c_cancel_tag,
output wire [11:0] c_cancel_ack_valid,
input wire [11:0] c_cancel_ack_ready,
output wire [383:0] c_cancel_ack_tag,
output wire [11:0] c_cancel_ack_rejected,
input wire [11:0] c_fence_valid,
output wire [11:0] c_fence_ready,
input wire [383:0] c_fence_cookie,
input wire [107:0] c_fence_epoch,
output wire [11:0] c_fence_done_valid,
input wire [11:0] c_fence_done_ready,
output wire [383:0] c_fence_done_cookie,
output wire [107:0] c_fence_done_epoch,
output wire [3:0] d_req_valid,
input wire [3:0] d_req_ready,
output wire [255:0] d_req_address,
output wire [255:0] d_req_tag,
input wire [3:0] d_rsp_valid,
output wire [3:0] d_rsp_ready,
input wire [255:0] d_rsp_tag,
input wire [2047:0] d_rsp_data,
output wire d_fence_valid,
input wire d_fence_ready,
output wire [31:0] d_fence_generation,
input wire d_fence_done_valid,
output wire d_fence_done_ready,
input wire [31:0] d_fence_done_generation,
output wire fault_valid,
input wire fault_ready,
output wire [7:0] fault_kind,
output wire [4:0] fault_client,
output wire [31:0] fault_local_tag,
output wire [63:0] fault_global_tag,
output wire [11:0] debug_beats,
output wire [11:0] debug_descriptors,
output wire [31:0] debug_generation,
input wire [8:0] service_req_valid,
output wire [8:0] service_req_ready,
input wire [575:0] service_req_address,
input wire [575:0] service_req_tag,
output wire [8:0] service_rsp_valid,
input wire [8:0] service_rsp_ready,
output wire [575:0] service_rsp_tag,
output wire [4607:0] service_rsp_data,
output wire [8:0] service_rsp_error,
output wire [8:0] service_idle,
output wire [8:0] service_protocol_fault);
wire [20:0] all_c_req_valid;
wire [20:0] all_c_req_ready;
wire [1343:0] all_c_req_address;
wire [671:0] all_c_req_tag;
wire [20:0] all_c_req_channel;
wire [104:0] all_c_req_record_beats;
wire [20:0] all_c_rsp_valid;
wire [20:0] all_c_rsp_ready;
wire [671:0] all_c_rsp_tag;
wire [10751:0] all_c_rsp_data;
wire [20:0] all_c_close_valid;
wire [20:0] all_c_close_ready;
wire [671:0] all_c_close_tag_base;
wire [20:0] all_c_cancel_valid;
wire [20:0] all_c_cancel_ready;
wire [671:0] all_c_cancel_tag;
wire [20:0] all_c_cancel_ack_valid;
wire [20:0] all_c_cancel_ack_ready;
wire [671:0] all_c_cancel_ack_tag;
wire [20:0] all_c_cancel_ack_rejected;
wire [20:0] all_c_fence_valid;
wire [20:0] all_c_fence_ready;
wire [671:0] all_c_fence_cookie;
wire [188:0] all_c_fence_epoch;
wire [20:0] all_c_fence_done_valid;
wire [20:0] all_c_fence_done_ready;
wire [671:0] all_c_fence_done_cookie;
wire [188:0] all_c_fence_done_epoch;
assign all_c_req_valid[11:0]=c_req_valid;
assign c_req_ready=all_c_req_ready[11:0];
assign all_c_req_address[767:0]=c_req_address;
assign all_c_req_tag[383:0]=c_req_tag;
assign all_c_req_channel[11:0]=c_req_channel;
assign all_c_req_record_beats[59:0]=c_req_record_beats;
assign c_rsp_valid=all_c_rsp_valid[11:0];
assign all_c_rsp_ready[11:0]=c_rsp_ready;
assign c_rsp_tag=all_c_rsp_tag[383:0];
assign c_rsp_data=all_c_rsp_data[6143:0];
assign all_c_close_valid[11:0]=c_close_valid;
assign c_close_ready=all_c_close_ready[11:0];
assign all_c_close_tag_base[383:0]=c_close_tag_base;
assign all_c_cancel_valid[11:0]=c_cancel_valid;
assign c_cancel_ready=all_c_cancel_ready[11:0];
assign all_c_cancel_tag[383:0]=c_cancel_tag;
assign c_cancel_ack_valid=all_c_cancel_ack_valid[11:0];
assign all_c_cancel_ack_ready[11:0]=c_cancel_ack_ready;
assign c_cancel_ack_tag=all_c_cancel_ack_tag[383:0];
assign c_cancel_ack_rejected=all_c_cancel_ack_rejected[11:0];
assign all_c_fence_valid[11:0]=c_fence_valid;
assign c_fence_ready=all_c_fence_ready[11:0];
assign all_c_fence_cookie[383:0]=c_fence_cookie;
assign all_c_fence_epoch[107:0]=c_fence_epoch;
assign c_fence_done_valid=all_c_fence_done_valid[11:0];
assign all_c_fence_done_ready[11:0]=c_fence_done_ready;
assign c_fence_done_cookie=all_c_fence_done_cookie[383:0];
assign c_fence_done_epoch=all_c_fence_done_epoch[107:0];
native_shared_read_dma #(.SERIAL_LIMIT(TRANSPORT_SERIAL_LIMIT)) transport(.clk(clk),.reset(reset),.p_mode_valid(3'b000),.p_mode_native64(3'b000),.p_mode_client_drained(3'b111),.p_mode_ready(),.p_mode_active(),.p_req_rejected(),.c_req_valid(all_c_req_valid),.c_req_ready(all_c_req_ready),.c_req_address(all_c_req_address),.c_req_tag(all_c_req_tag),.c_req_channel(all_c_req_channel),.c_req_record_beats(all_c_req_record_beats),.c_rsp_valid(all_c_rsp_valid),.c_rsp_ready(all_c_rsp_ready),.c_rsp_tag(all_c_rsp_tag),.c_rsp_data(all_c_rsp_data),.c_close_valid(all_c_close_valid),.c_close_ready(all_c_close_ready),.c_close_tag_base(all_c_close_tag_base),.c_cancel_valid(all_c_cancel_valid),.c_cancel_ready(all_c_cancel_ready),.c_cancel_tag(all_c_cancel_tag),.c_cancel_ack_valid(all_c_cancel_ack_valid),.c_cancel_ack_ready(all_c_cancel_ack_ready),.c_cancel_ack_tag(all_c_cancel_ack_tag),.c_cancel_ack_rejected(all_c_cancel_ack_rejected),.c_fence_valid(all_c_fence_valid),.c_fence_ready(all_c_fence_ready),.c_fence_cookie(all_c_fence_cookie),.c_fence_epoch(all_c_fence_epoch),.c_fence_done_valid(all_c_fence_done_valid),.c_fence_done_ready(all_c_fence_done_ready),.c_fence_done_cookie(all_c_fence_done_cookie),.c_fence_done_epoch(all_c_fence_done_epoch),.d_req_valid(d_req_valid),.d_req_ready(d_req_ready),.d_req_address(d_req_address),.d_req_tag(d_req_tag),.d_rsp_valid(d_rsp_valid),.d_rsp_ready(d_rsp_ready),.d_rsp_tag(d_rsp_tag),.d_rsp_data(d_rsp_data),.d_fence_valid(d_fence_valid),.d_fence_ready(d_fence_ready),.d_fence_generation(d_fence_generation),.d_fence_done_valid(d_fence_done_valid),.d_fence_done_ready(d_fence_done_ready),.d_fence_done_generation(d_fence_done_generation),.fault_valid(fault_valid),.fault_ready(fault_ready),.fault_kind(fault_kind),.fault_client(fault_client),.fault_local_tag(fault_local_tag),.fault_global_tag(fault_global_tag),.debug_beats(debug_beats),.debug_descriptors(debug_descriptors),.debug_generation(debug_generation));
for(genvar k=0;k<9;k=k+1)begin: service_client
native64_dma_serial_client #(.SERIAL_LIMIT(SERVICE_SERIAL_LIMIT)) serial(.clk(clk),.reset(reset),.req_valid(service_req_valid[k]),.req_ready(service_req_ready[k]),.req_address(service_req_address[k*64+:64]),.req_tag(service_req_tag[k*64+:64]),.rsp_valid(service_rsp_valid[k]),.rsp_ready(service_rsp_ready[k]),.rsp_tag(service_rsp_tag[k*64+:64]),.rsp_data(service_rsp_data[k*512+:512]),.rsp_error(service_rsp_error[k]),.dma_valid(all_c_req_valid[k+12]),.dma_ready(all_c_req_ready[k+12]),.dma_address(all_c_req_address[(k+12)*64+:64]),.dma_tag(all_c_req_tag[(k+12)*32+:32]),.dma_rsp_valid(all_c_rsp_valid[k+12]),.dma_rsp_ready(all_c_rsp_ready[k+12]),.dma_rsp_tag(all_c_rsp_tag[(k+12)*32+:32]),.dma_rsp_data(all_c_rsp_data[(k+12)*512+:512]),.fence_valid(all_c_fence_valid[k+12]),.fence_ready(all_c_fence_ready[k+12]),.fence_cookie(all_c_fence_cookie[(k+12)*32+:32]),.fence_epoch(all_c_fence_epoch[(k+12)*9+:9]),.fence_done_valid(all_c_fence_done_valid[k+12]),.fence_done_ready(all_c_fence_done_ready[k+12]),.fence_done_cookie(all_c_fence_done_cookie[(k+12)*32+:32]),.fence_done_epoch(all_c_fence_done_epoch[(k+12)*9+:9]),.idle(service_idle[k]),.protocol_fault(service_protocol_fault[k]));
assign all_c_req_channel[k+12]=service_req_address[k*64+11];
assign all_c_req_record_beats[(k+12)*5+:5]=5'd1;
assign all_c_close_valid[k+12]=1'b0;
assign all_c_close_tag_base[(k+12)*32+:32]=32'd0;
assign all_c_cancel_valid[k+12]=1'b0;
assign all_c_cancel_tag[(k+12)*32+:32]=32'd0;
assign all_c_cancel_ack_ready[k+12]=1'b1;
end
endmodule
