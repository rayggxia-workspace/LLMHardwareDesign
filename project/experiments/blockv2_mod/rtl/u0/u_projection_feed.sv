// One native U command owns the existing SRAM while supplying a selected P.
module u_projection_feed(
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
 input wire clk,reset,svc_valid,output wire svc_ready,
 input wire [1023:0] descriptor,output wire rsp_valid,input wire rsp_ready,
 output wire [15:0] status,output reg [31:0] read_bytes,write_bytes,
 output wire s_req_valid,s_req_write,input wire s_req_ready,
 output wire [9:0] s_req_address,output wire [127:0] s_req_data,
 input wire s_rsp_valid,output wire s_rsp_ready,input wire [127:0] s_rsp_data
);
 reg [1023:0] raw;
 always @* begin
  raw=0;raw[31:0]=32'h44454650;raw[32+:16]=128;raw[48+:16]=descriptor[32+:16]==16'h010c ? 16'd2 : 16'd1;
  raw[64+:32]=32'h02500002;raw[96+:32]=25001;
  raw[128+:64]=descriptor[512+:64];
  raw[192+:128]=descriptor[576+:128];
  raw[320+:32]=descriptor[704+:32];
  if(descriptor[32+:16]==16'h010c)raw[352+:32]=descriptor[736+:32];
 end
 wire q_valid,q_ready,q_write,q_rsp,q_take,u_valid,u_ready,u_rsp,u_take;
 wire [9:0] q_address,u_address;
 wire [31:0] q_tag,u_tag;
 wire [127:0] q_data;
 reg pending,read_owner;
 reg [31:0] response_tag;
 wire select_q=q_valid;
 assign s_req_valid=!pending&&(q_valid||u_valid);
 assign s_req_write=select_q&&q_write;
 assign s_req_address=select_q?q_address:u_address;
 assign s_req_data=q_data;
 assign q_ready=!pending&&s_req_ready;
 assign u_ready=!pending&&!q_valid&&s_req_ready;
 assign q_rsp=pending&&!read_owner&&s_rsp_valid;
 assign u_rsp=pending&&read_owner&&s_rsp_valid;
 assign s_rsp_ready=pending&&(read_owner?u_take:q_take);
 always @(posedge clk)begin
  if(reset)begin pending<=0;read_owner<=0;response_tag<=0;read_bytes<=0;write_bytes<=0;end
  else begin
   if(svc_valid&&svc_ready)begin read_bytes<=0;write_bytes<=0;end
   if(s_req_valid&&s_req_ready)begin
    pending<=1;read_owner<=!select_q;response_tag<=select_q?q_tag:u_tag;
    if(!s_req_write)read_bytes<=read_bytes+16;

   end
   if(!(svc_valid&&svc_ready))
    write_bytes<=write_bytes+
      ((s_req_valid&&s_req_ready&&s_req_write)?32'd16:32'd0)+
      ((feed_cp_ack_valid&&feed_cp_ack_ready&&!feed_cp_ack_error)?32'd16:32'd0);
   if(s_rsp_valid&&s_rsp_ready)pending<=0;
  end
 end
 blockv2_mod_projection_feed feed(
 .clk,.reset,.service_valid(svc_valid),.service_ready(svc_ready),.descriptor(raw),
 .descriptor_crc_ok((descriptor[32+:16]==16'h0109 && descriptor[1023:736]==0)||(descriptor[32+:16]==16'h010c && descriptor[1023:768]==0)),
 .service_owner(descriptor[576+:128]),.done_valid(rsp_valid),.done_ready(rsp_ready),
 .done_owner(),.done_status(status),.busy(),
 .window_need_valid(feed_window_need_valid),.window_need_k(feed_window_need_k),.window_need_key(feed_window_need_key),.lease_valid(feed_lease_valid),.lease_ready(feed_lease_ready),.lease_key(feed_lease_key),.lease_generation(feed_lease_generation),.lease_k(feed_lease_k),.lease_session(feed_lease_session),.lease_ticket(feed_lease_ticket),.release_window(feed_release_window),.release_ready(feed_release_ready),.window_enabled(feed_window_enabled),.header_valid(feed_header_valid),.header_ready(feed_header_ready),.header_tag(feed_header_tag),.header_data(feed_header_data),.header_ack_valid(feed_header_ack_valid),.header_ack_ready(feed_header_ack_ready),.header_ack_tag(feed_header_ack_tag),.header_ack_error(feed_header_ack_error),.cp_valid(feed_cp_valid),.cp_ready(feed_cp_ready),.cp_address(feed_cp_address),.cp_tag(feed_cp_tag),.cp_data(feed_cp_data),.cp_ack_valid(feed_cp_ack_valid),.cp_ack_ready(feed_cp_ack_ready),.cp_ack_tag(feed_cp_ack_tag),.cp_ack_error(feed_cp_ack_error),.copy_drained(feed_copy_drained),.copy_progress_valid(feed_copy_progress_valid),.copy_key(feed_copy_key),.copy_generation(feed_copy_generation),.copy_k(feed_copy_k),.copy_session(feed_copy_session),.copy_ticket(feed_copy_ticket),.copy_committed_prefix(feed_copy_committed_prefix),.proof_valid(feed_proof_valid),.proof_ready(feed_proof_ready),.proof_shift(feed_proof_shift),.source_reads_drained(feed_source_reads_drained),
 .q_valid,.q_ready,.q_write,.q_address,.q_data,.q_tag,
 .q_rsp_valid(q_rsp),.q_rsp_ready(q_take),.q_rsp_tag(response_tag),.q_rsp_data(s_rsp_data),.q_rsp_error(1'b0),
 .u_valid,.u_ready,.u_address,.u_tag,
 .u_rsp_valid(u_rsp),.u_rsp_ready(u_take),.u_rsp_tag(response_tag),.u_rsp_data(s_rsp_data),.u_rsp_error(1'b0));
endmodule
