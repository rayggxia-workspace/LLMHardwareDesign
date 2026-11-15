// Execute RMSNorm over two leased halves of U0's existing 16 KiB private SRAM.
module u_resident_rms (
    input wire  feed_window_need_valid,
    input wire [15:0] feed_window_need_k,
    input wire [127:0] feed_window_need_key,
    output wire  feed_lease_valid,
    input wire  feed_lease_ready,
    output wire [127:0] feed_lease_key,
    output wire [15:0] feed_lease_generation,
    output wire [15:0] feed_lease_k,
    output wire [31:0] feed_lease_session,
    output wire [31:0] feed_lease_ticket,
    output wire  feed_release_window,
    input wire  feed_release_ready,
    input wire  feed_window_enabled,
    output wire  feed_header_valid,
    input wire  feed_header_ready,
    output wire [31:0] feed_header_tag,
    output wire [127:0] feed_header_data,
    input wire  feed_header_ack_valid,
    output wire  feed_header_ack_ready,
    input wire [31:0] feed_header_ack_tag,
    input wire  feed_header_ack_error,
    output wire  feed_cp_valid,
    input wire  feed_cp_ready,
    output wire [9:0] feed_cp_address,
    output wire [31:0] feed_cp_tag,
    output wire [127:0] feed_cp_data,
    input wire  feed_cp_ack_valid,
    output wire  feed_cp_ack_ready,
    input wire [31:0] feed_cp_ack_tag,
    input wire  feed_cp_ack_error,
    output wire  feed_copy_drained,
    output wire  feed_copy_progress_valid,
    output wire [127:0] feed_copy_key,
    output wire [15:0] feed_copy_generation,
    output wire [15:0] feed_copy_k,
    output wire [31:0] feed_copy_session,
    output wire [31:0] feed_copy_ticket,
    output wire [10:0] feed_copy_committed_prefix,
    input wire  feed_proof_valid,
    output wire  feed_proof_ready,
    input wire [5:0] feed_proof_shift,
    input wire  feed_source_reads_drained,
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

 reg active;
 reg [1:0] use_add;
 wire [1:0] offer_add=(descriptor[32+:16]==16'h0109 || descriptor[32+:16]==16'h010c) ? 2'd3 :
     (descriptor[32+:16]==16'h0108 || descriptor[32+:16]==16'h010b) ? 2'd2 :
     descriptor[32+:16]==16'h0107 ? 2'd1 : 2'd0;
 wire [3:0] ready,done,req,write_req,take;
 wire [3:0][15:0] statuses;
 wire [3:0][31:0] reads,writes;
 wire [3:0][9:0] address;
 wire [3:0][127:0] data;
 assign svc_ready=!active && ready[offer_add];
 assign rsp_valid=active && done[use_add];
 assign status=statuses[use_add];
 assign read_bytes=reads[use_add];
 assign write_bytes=writes[use_add];
 assign s_req_valid=active && req[use_add];
 assign s_req_write=write_req[use_add];
 assign s_req_address=address[use_add];
 assign s_req_data=data[use_add];
 assign s_rsp_ready=active && take[use_add];
 always @(posedge clk) begin
   if(reset)begin active<=0;use_add<=0;end
   else begin
     if(svc_valid && svc_ready)begin active<=1;use_add<=offer_add;end
     if(rsp_valid && rsp_ready)active<=0;
   end
 end

 u_resident_rms_core service_0(
 .clk,.reset,.svc_valid(svc_valid && !active && offer_add==2'd0),.svc_ready(ready[0]),.descriptor,
 .rsp_valid(done[0]),.rsp_ready(rsp_ready && active && use_add==2'd0),
 .status(statuses[0]),.read_bytes(reads[0]),.write_bytes(writes[0]),
 .s_req_valid(req[0]),.s_req_write(write_req[0]),.s_req_ready(active && use_add==2'd0 && s_req_ready),
 .s_req_address(address[0]),.s_req_data(data[0]),
 .s_rsp_valid(active && use_add==2'd0 && s_rsp_valid),.s_rsp_ready(take[0]),.s_rsp_data);

 u_resident_add service_1(
 .clk,.reset,.svc_valid(svc_valid && !active && offer_add==2'd1),.svc_ready(ready[1]),.descriptor,
 .rsp_valid(done[1]),.rsp_ready(rsp_ready && active && use_add==2'd1),
 .status(statuses[1]),.read_bytes(reads[1]),.write_bytes(writes[1]),
 .s_req_valid(req[1]),.s_req_write(write_req[1]),.s_req_ready(active && use_add==2'd1 && s_req_ready),
 .s_req_address(address[1]),.s_req_data(data[1]),
 .s_rsp_valid(active && use_add==2'd1 && s_rsp_valid),.s_rsp_ready(take[1]),.s_rsp_data);

 u_resident_store service_2 (
 .clk,.reset,.svc_valid(svc_valid && !active && offer_add==2),.svc_ready(ready[2]),.descriptor,
 .rsp_valid(done[2]),.rsp_ready(rsp_ready && active && use_add==2),
 .status(statuses[2]),.read_bytes(reads[2]),.write_bytes(writes[2]),
 .s_req_valid(req[2]),.s_req_write(write_req[2]),.s_req_ready(active && use_add==2 && s_req_ready),
 .s_req_address(address[2]),.s_req_data(data[2]),
 .s_rsp_valid(active && use_add==2 && s_rsp_valid),.s_rsp_ready(take[2]),.s_rsp_data,
 .resident_wr_valid,.resident_wr_ready,.resident_wr_address,.resident_wr_tag,.resident_wr_data,.resident_wr_done_valid,.resident_wr_done_ready,.resident_wr_done_tag,.resident_wr_done_error);

 u_projection_feed service_3(
 .clk,.reset,.svc_valid(svc_valid && !active && offer_add==3),.svc_ready(ready[3]),.descriptor,
 .rsp_valid(done[3]),.rsp_ready(rsp_ready && active && use_add==3),
 .status(statuses[3]),.read_bytes(reads[3]),.write_bytes(writes[3]),
 .s_req_valid(req[3]),.s_req_write(write_req[3]),.s_req_ready(active && use_add==3 && s_req_ready),
 .s_req_address(address[3]),.s_req_data(data[3]),
 .s_rsp_valid(active && use_add==3 && s_rsp_valid),.s_rsp_ready(take[3]),.s_rsp_data,
 .feed_window_need_valid,.feed_window_need_k,.feed_window_need_key,.feed_lease_valid,.feed_lease_ready,.feed_lease_key,.feed_lease_generation,.feed_lease_k,.feed_lease_session,.feed_lease_ticket,.feed_release_window,.feed_release_ready,.feed_window_enabled,.feed_header_valid,.feed_header_ready,.feed_header_tag,.feed_header_data,.feed_header_ack_valid,.feed_header_ack_ready,.feed_header_ack_tag,.feed_header_ack_error,.feed_cp_valid,.feed_cp_ready,.feed_cp_address,.feed_cp_tag,.feed_cp_data,.feed_cp_ack_valid,.feed_cp_ack_ready,.feed_cp_ack_tag,.feed_cp_ack_error,.feed_copy_drained,.feed_copy_progress_valid,.feed_copy_key,.feed_copy_generation,.feed_copy_k,.feed_copy_session,.feed_copy_ticket,.feed_copy_committed_prefix,.feed_proof_valid,.feed_proof_ready,.feed_proof_shift,.feed_source_reads_drained);

endmodule
