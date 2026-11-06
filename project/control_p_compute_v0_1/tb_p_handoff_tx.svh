  wire service_response tx_rsp;
  wire tx_req_ready,tx_rsp_valid,tx_s_req,tx_s_write,tx_s_take,tx_poison;
  wire [9:0] tx_s_address;
  wire [127:0] tx_s_data;
  assign svc_req_ready_i=svc_req_kind_o==0 ? compute_req_ready : tx_req_ready;
  assign svc_rsp_valid_i=compute_rsp_valid || tx_rsp_valid;
  assign selected_rsp=compute_rsp_valid ? compute_rsp : tx_rsp;
  assign host_ready=s_req_ready[1];
  assign host_ack=s_rsp_valid[1];
  assign host_result=s_rsp_data[128+:128];
  wire [3:0] request_valid={tx_s_req,1'b0,host_valid,s_write_valid && write_gate};
  wire [3:0] request_write={tx_s_write,1'b0,host_write,compute_s_write};
  wire [39:0] request_address={tx_s_address,10'b0,host_word,s_write_word};
  wire [511:0] request_data={tx_s_data,128'b0,host_data,s_write_data};
  wire [3:0] response_ready={tx_s_take,1'b0,1'b1,s_ack_ready && ack_gate};
  lc_raw16_s_adapter tx(.clk(clk_i),.reset(!rst_ni),.admit(1'b1),.response_enable(1'b1),
    .req_valid(svc_req_valid_o && svc_req_kind_o==2),.req_ready(tx_req_ready),
    .req_kind(svc_req_kind_o),.req_resource(svc_req_resource_o),.req_token(svc_req_token_o),
    .req_sequence(svc_req_sequence_o),.req_job(svc_req_job_o),.req_epoch(svc_req_epoch_o),
    .req_task(svc_req_task_sequence_o),.req_descriptor(svc_req_descriptor_o),
    .req_base(svc_req_object_base_o),.req_length(svc_req_object_length_o),.req_version(svc_req_object_version_o),
    .rsp_valid(tx_rsp_valid),.rsp_ready(svc_rsp_ready_o && !compute_rsp_valid),.rsp_kind(tx_rsp.kind),
    .rsp_token(tx_rsp.token),.rsp_sequence(tx_rsp.seq),.rsp_job(tx_rsp.job),.rsp_epoch(tx_rsp.epoch),
    .rsp_task(tx_rsp.task_id),.rsp_status(tx_rsp.status),.rsp_read(tx_rsp.bytes_read),
    .rsp_write(tx_rsp.bytes_written),.rsp_saturated(tx_rsp.saturated),
    .link_valid(link_valid_o),.link_ready(link_ready_i),.link_kind(link_kind_o),.link_job(link_job_o),
    .link_epoch(link_epoch_o),.link_task(link_task_o),.link_sequence(link_sequence_o),
    .link_edge(link_edge_o),.link_peer(link_peer_o),.link_data(link_data_o),
    .store_valid(1'b0),.store_ready(),.store_data(128'b0),.done_valid(done_valid_i),
    .done_ready(done_ready_o),.done_status(16'b0),
    .s_req(tx_s_req),.s_write(tx_s_write),.s_address(tx_s_address),.s_data(tx_s_data),
    .s_ready(s_req_ready[3]),.s_valid(s_rsp_valid[3]),.s_result(s_rsp_data[384+:128]),
    .s_take(tx_s_take),.poison(tx_poison),.busy());
  always @(posedge clk_i) if(rst_ni) begin
    if(tx_poison || (compute_rsp_valid && tx_rsp_valid)) $fatal(1,"source service ownership");
    if(s_rsp_valid[3] && tx_s_take)
      $display("CHAIN %0d SOURCE_READ %0d %032h",cycle_i,tx_s_address,s_rsp_data[384+:128]);
    if(trace_retire_o && trace_opcode_o==8'h49)
      $display("CHAIN %0d DROP",cycle_i);
    if(svc_req_valid_o && svc_req_ready_i && svc_req_kind_o==2)
      $display("CHAIN %0d TX_ISSUE %0d %0d %0d %0d",cycle_i,svc_req_job_o,
               svc_req_epoch_o,svc_req_task_sequence_o,svc_req_sequence_o);
  end
