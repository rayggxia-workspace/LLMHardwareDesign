// Execute RMSNorm over two leased halves of U0's existing 16 KiB private SRAM.
module u_resident_store (
    output wire resident_wr_valid,
    input wire resident_wr_ready,
    output wire [63:0] resident_wr_address, resident_wr_tag,
    output wire [511:0] resident_wr_data,
    input wire resident_wr_done_valid,
    output wire resident_wr_done_ready,
    input wire [63:0] resident_wr_done_tag,
    input wire resident_wr_done_error,
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


 wire counted = descriptor[32+:16]==16'h010b;
 wire valid_fields = descriptor[1023:672]==0 && (counted || descriptor[543:528]==0);
 wire [1023:0] native_descriptor = {
   704'd0,descriptor[608+:64],descriptor[544+:64],32'd0,descriptor[512+:32],
   32'd25001,32'h02500002,16'd1,16'd128,
   (valid_fields ? (counted ? 32'h31435344 : 32'h38535744) : 32'd0)};
 assign s_req_write=0;
 assign s_req_data=0;
 s128_kv_store_scope #(.TOPOLOGY(25001),.ACTIVATION_ROW(1'b1),.COUNTED_STORE(1'b1)) store (
 .clk,.reset,.service_valid(svc_valid),.service_ready(svc_ready),
 .service_owner(128'd0),.service_ticket(32'd0),.service_descriptor(native_descriptor),
 .service_cancel_valid(1'b0),.service_cancel_ready(),
 .service_done_valid(rsp_valid),.service_done_ready(rsp_ready),.service_done_owner(),.service_done_ticket(),
 .service_done_status(status),.service_done_read_bytes(read_bytes),.service_done_write_bytes(write_bytes),
 .s_req_valid,.s_req_ready,.s_req_address,.s_rsp_valid,.s_rsp_ready,.s_rsp_data,.s_rsp_error(1'b0),
 .wr_valid(resident_wr_valid),.wr_ready(resident_wr_ready),
 .wr_address(resident_wr_address),.wr_tag(resident_wr_tag),.wr_data(resident_wr_data),
 .wr_done_valid(resident_wr_done_valid),.wr_done_ready(resident_wr_done_ready),
 .wr_done_tag(resident_wr_done_tag),.wr_done_error(resident_wr_done_error));
endmodule
