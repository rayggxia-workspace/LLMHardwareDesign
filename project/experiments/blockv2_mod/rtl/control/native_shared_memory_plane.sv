// Parent standard cells: explicit fixed DMA control links, no functional macros or U/P data wiring.
module native_shared_memory_plane #(parameter logic [30:0] SERVICE_SERIAL_LIMIT=31'h7fffffff,
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

output wire [8:0] service_protocol_fault,
input wire [8:0] write_req_valid,
output wire [8:0] write_req_ready,
input wire [575:0] write_req_address,write_req_tag,
input wire [4607:0] write_req_data,
output wire [8:0] write_done_valid,
input wire [8:0] write_done_ready,
output wire [575:0] write_done_tag,
output wire [8:0] write_done_error,write_idle,write_protocol_fault,
output wire transport_idle,
output reg [3:0] d_req_write,
output reg [2047:0] d_req_data
);
wire [29:0] all_c_req_valid;
wire [29:0] all_c_req_ready;
wire [1919:0] all_c_req_address;
wire [959:0] all_c_req_tag;
wire [29:0] all_c_req_channel;
wire [149:0] all_c_req_record_beats;
wire [29:0] all_c_rsp_valid;
wire [29:0] all_c_rsp_ready;
wire [959:0] all_c_rsp_tag;
wire [15359:0] all_c_rsp_data;
wire [29:0] all_c_close_valid;
wire [29:0] all_c_close_ready;
wire [959:0] all_c_close_tag_base;
wire [29:0] all_c_cancel_valid;
wire [29:0] all_c_cancel_ready;
wire [959:0] all_c_cancel_tag;
wire [29:0] all_c_cancel_ack_valid;
wire [29:0] all_c_cancel_ack_ready;
wire [959:0] all_c_cancel_ack_tag;
wire [29:0] all_c_cancel_ack_rejected;
wire [29:0] all_c_fence_valid;
wire [29:0] all_c_fence_ready;
wire [959:0] all_c_fence_cookie;
wire [269:0] all_c_fence_epoch;
wire [29:0] all_c_fence_done_valid;
wire [29:0] all_c_fence_done_ready;
wire [959:0] all_c_fence_done_cookie;
wire [269:0] all_c_fence_done_epoch;
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
native_shared_memory_dma #(.SERIAL_LIMIT(TRANSPORT_SERIAL_LIMIT)) transport(.clk(clk),.reset(reset),.p_mode_valid(3'b000),.p_mode_native64(3'b000),.p_mode_client_drained(3'b111),.p_mode_ready(),.p_mode_active(),.p_req_rejected(),.c_req_valid(all_c_req_valid),.c_req_ready(all_c_req_ready),.c_req_address(all_c_req_address),.c_req_tag(all_c_req_tag),.c_req_channel(all_c_req_channel),.c_req_record_beats(all_c_req_record_beats),.c_rsp_valid(all_c_rsp_valid),.c_rsp_ready(all_c_rsp_ready),.c_rsp_tag(all_c_rsp_tag),.c_rsp_data(all_c_rsp_data),.c_close_valid(all_c_close_valid),.c_close_ready(all_c_close_ready),.c_close_tag_base(all_c_close_tag_base),.c_cancel_valid(all_c_cancel_valid),.c_cancel_ready(all_c_cancel_ready),.c_cancel_tag(all_c_cancel_tag),.c_cancel_ack_valid(all_c_cancel_ack_valid),.c_cancel_ack_ready(all_c_cancel_ack_ready),.c_cancel_ack_tag(all_c_cancel_ack_tag),.c_cancel_ack_rejected(all_c_cancel_ack_rejected),.c_fence_valid(all_c_fence_valid),.c_fence_ready(all_c_fence_ready),.c_fence_cookie(all_c_fence_cookie),.c_fence_epoch(all_c_fence_epoch),.c_fence_done_valid(all_c_fence_done_valid),.c_fence_done_ready(all_c_fence_done_ready),.c_fence_done_cookie(all_c_fence_done_cookie),.c_fence_done_epoch(all_c_fence_done_epoch),.d_req_valid(d_req_valid),.d_req_ready(d_req_ready),.d_req_address(d_req_address),.d_req_tag(d_req_tag),.d_rsp_valid(d_rsp_valid),.d_rsp_ready(d_rsp_ready),.d_rsp_tag(d_rsp_tag),.d_rsp_data(d_rsp_data),.d_fence_valid(d_fence_valid),.d_fence_ready(d_fence_ready),.d_fence_generation(d_fence_generation),.d_fence_done_valid(d_fence_done_valid),.d_fence_done_ready(d_fence_done_ready),.d_fence_done_generation(d_fence_done_generation),.fault_valid(fault_valid),.fault_ready(fault_ready),.fault_kind(fault_kind),.fault_client(fault_client),.fault_local_tag(fault_local_tag),.fault_global_tag(fault_global_tag),.debug_beats(debug_beats),.debug_descriptors(debug_descriptors),.debug_generation(debug_generation),.transport_idle(transport_idle));
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
// A write owns one 64B payload slot until the matched completion retires.
// Backend returns ACK only after write commit; ACK data bit0 is its error bit.
reg [511:0] write_payload[0:8];
wire [4607:0] write_return_payload;
wire [8:0] write_transport_error;
for(genvar w=0;w<9;w=w+1)begin: write_client
 always @(posedge clk)begin
  if(reset)write_payload[w]<=0;
  else if(write_req_valid[w]&&write_req_ready[w])
   write_payload[w]<=write_req_data[w*512+:512];
 end
 native64_dma_serial_client #(.SERIAL_LIMIT(SERVICE_SERIAL_LIMIT)) serial(
 .clk(clk),.reset(reset),.req_valid(write_req_valid[w]),.req_ready(write_req_ready[w]),
 .req_address(write_req_address[w*64+:64]),.req_tag(write_req_tag[w*64+:64]),
 .rsp_valid(write_done_valid[w]),.rsp_ready(write_done_ready[w]),
 .rsp_tag(write_done_tag[w*64+:64]),.rsp_data(write_return_payload[w*512+:512]),
 .rsp_error(write_transport_error[w]),
 .dma_valid(all_c_req_valid[w+21]),.dma_ready(all_c_req_ready[w+21]),
 .dma_address(all_c_req_address[(w+21)*64+:64]),.dma_tag(all_c_req_tag[(w+21)*32+:32]),
 .dma_rsp_valid(all_c_rsp_valid[w+21]),.dma_rsp_ready(all_c_rsp_ready[w+21]),
 .dma_rsp_tag(all_c_rsp_tag[(w+21)*32+:32]),.dma_rsp_data(all_c_rsp_data[(w+21)*512+:512]),
 .fence_valid(all_c_fence_valid[w+21]),.fence_ready(all_c_fence_ready[w+21]),
 .fence_cookie(all_c_fence_cookie[(w+21)*32+:32]),.fence_epoch(all_c_fence_epoch[(w+21)*9+:9]),
 .fence_done_valid(all_c_fence_done_valid[w+21]),.fence_done_ready(all_c_fence_done_ready[w+21]),
 .fence_done_cookie(all_c_fence_done_cookie[(w+21)*32+:32]),.fence_done_epoch(all_c_fence_done_epoch[(w+21)*9+:9]),
 .idle(write_idle[w]),.protocol_fault(write_protocol_fault[w]));
 assign write_done_error[w]=write_transport_error[w]|write_return_payload[w*512];
 assign all_c_req_channel[w+21]=write_req_address[w*64+11];
 assign all_c_req_record_beats[(w+21)*5+:5]=5'd1;
 assign all_c_close_valid[w+21]=1'b0;
 assign all_c_close_tag_base[(w+21)*32+:32]=32'd0;
 assign all_c_cancel_valid[w+21]=1'b0;
 assign all_c_cancel_tag[(w+21)*32+:32]=32'd0;
 assign all_c_cancel_ack_ready[w+21]=1'b1;
end
always @*begin
 d_req_write=0;d_req_data=0;
 for(integer lane=0;lane<4;lane=lane+1)begin
  for(integer w=0;w<9;w=w+1)begin
   if(d_req_valid[lane]&&d_req_tag[lane*64+5+:5]==5'(w+21))begin
    d_req_write[lane]=1;d_req_data[lane*512+:512]=write_payload[w];
   end
  end
 end
end
endmodule
