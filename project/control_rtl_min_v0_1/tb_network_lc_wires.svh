reg release_valid_i;
reg [31:0] release_sequence_i;
wire release_ready_o;
reg cfg_req_valid_i;
reg [2:0] cfg_req_op_i;
reg [31:0] cfg_req_generation_i;
reg [13:0] cfg_req_address_i;
reg [127:0] cfg_req_data_i;
reg [15:0] cfg_req_total_bytes_i;
reg [31:0] cfg_req_image_id_i;
reg [31:0] cfg_req_topology_id_i;
reg [31:0] cfg_req_abi_id_i;
reg [31:0] cfg_req_capacity_id_i;
reg cfg_req_proof_i;
reg cfg_rsp_ready_i;
wire cfg_req_ready_o;
wire cfg_rsp_valid_o;
wire [15:0] cfg_rsp_status_o;
wire [127:0] cfg_rsp_data_o;
wire [31:0] cfg_rsp_generation_o;
reg pm_req_ready_i;
reg pm_rsp_valid_i;
reg [127:0] pm_rsp_data_i;
reg pm_rsp_error_i;
wire pm_req_valid_o;
wire pm_req_write_o;
wire [13:0] pm_req_address_o;
wire [127:0] pm_req_data_o;
wire pm_rsp_ready_o;
reg svc_req_ready_i;
reg svc_rsp_valid_i;
reg [1:0] svc_rsp_kind_i;
reg [2:0] svc_rsp_token_i;
reg [31:0] svc_rsp_sequence_i;
reg [31:0] svc_rsp_job_i;
reg [31:0] svc_rsp_epoch_i;
reg [31:0] svc_rsp_task_sequence_i;
reg [15:0] svc_rsp_status_i;
reg [31:0] svc_rsp_read_bytes_i;
reg [31:0] svc_rsp_write_bytes_i;
reg svc_rsp_saturated_i;
wire svc_req_valid_o;
wire [1:0] svc_req_kind_o;
wire [2:0] svc_req_resource_o;
wire [2:0] svc_req_token_o;
wire [31:0] svc_req_sequence_o;
wire [31:0] svc_req_job_o;
wire [31:0] svc_req_epoch_o;
wire [31:0] svc_req_task_sequence_o;
wire [1023:0] svc_req_descriptor_o;
wire [63:0] svc_req_object_base_o;
wire [31:0] svc_req_object_length_o;
wire [31:0] svc_req_object_version_o;
wire svc_rsp_ready_o;
reg close_req_ready_i;
reg close_rsp_valid_i;
reg [31:0] close_rsp_sequence_i;
reg [31:0] close_rsp_job_i;
reg [31:0] close_rsp_epoch_i;
reg [31:0] close_rsp_task_sequence_i;
reg [2:0] close_rsp_token_i;
reg [15:0] close_rsp_status_i;
wire close_req_valid_o;
wire [31:0] close_req_sequence_o;
wire [31:0] close_req_job_o;
wire [31:0] close_req_epoch_o;
wire [31:0] close_req_task_sequence_o;
wire [2:0] close_req_token_o;
wire close_rsp_ready_o;
wire [3:0] seq_o;
wire [31:0] trace_pc_o;
wire trace_retire_o;
wire [7:0] trace_opcode_o;
wire [1:0] trace_pm_owner_o;
wire trace_ireg_valid_o;
wire trace_cancel_token_retire_o;
wire trace_cancel_object_drop_o;
lc_min_controller #(.BLOCK_ID(BLOCK),.STALL_LIMIT(4096)
`ifdef TB_ENABLE_M_DOT_STORE
  ,.ENABLE_M_DOT_STORE(1'b1)
  `ifdef TB_P_SILU
  ,.M_DOT_STORE_SILU(1'b1)
  `endif
`endif
) controller(
.clk_i(clk_i),
.rst_ni(rst_ni),
.release_valid_i(release_valid_i),
.release_sequence_i(release_sequence_i),
.release_epoch_i(release_epoch_i),
.deploy_valid_i(deploy_valid_i),
.deploy_generation_i(deploy_generation_i),
.release_ready_o(release_ready_o),
.poison_o(poison_o),
.image_valid_o(image_valid_o),
.cfg_req_valid_i(cfg_req_valid_i),
.cfg_req_op_i(cfg_req_op_i),
.cfg_req_generation_i(cfg_req_generation_i),
.cfg_req_address_i(cfg_req_address_i),
.cfg_req_data_i(cfg_req_data_i),
.cfg_req_total_bytes_i(cfg_req_total_bytes_i),
.cfg_req_image_id_i(cfg_req_image_id_i),
.cfg_req_topology_id_i(cfg_req_topology_id_i),
.cfg_req_abi_id_i(cfg_req_abi_id_i),
.cfg_req_capacity_id_i(cfg_req_capacity_id_i),
.cfg_req_proof_i(cfg_req_proof_i),
.cfg_rsp_ready_i(cfg_rsp_ready_i),
.cfg_req_ready_o(cfg_req_ready_o),
.cfg_rsp_valid_o(cfg_rsp_valid_o),
.cfg_rsp_status_o(cfg_rsp_status_o),
.cfg_rsp_data_o(cfg_rsp_data_o),
.cfg_rsp_generation_o(cfg_rsp_generation_o),
.pm_req_ready_i(pm_req_ready_i),
.pm_rsp_valid_i(pm_rsp_valid_i),
.pm_rsp_data_i(pm_rsp_data_i),
.pm_rsp_error_i(pm_rsp_error_i),
.pm_req_valid_o(pm_req_valid_o),
.pm_req_write_o(pm_req_write_o),
.pm_req_address_o(pm_req_address_o),
.pm_req_data_o(pm_req_data_o),
.pm_rsp_ready_o(pm_rsp_ready_o),
.task_valid_i(task_valid_i),
.task_packet_i(task_packet_i),
.task_credit_i(task_credit_i),
.task_ready_o(task_ready_o),
.svc_req_ready_i(svc_req_ready_i),
.svc_rsp_valid_i(svc_rsp_valid_i),
.svc_rsp_kind_i(svc_rsp_kind_i),
.svc_rsp_token_i(svc_rsp_token_i),
.svc_rsp_sequence_i(svc_rsp_sequence_i),
.svc_rsp_job_i(svc_rsp_job_i),
.svc_rsp_epoch_i(svc_rsp_epoch_i),
.svc_rsp_task_sequence_i(svc_rsp_task_sequence_i),
.svc_rsp_status_i(svc_rsp_status_i),
.svc_rsp_read_bytes_i(svc_rsp_read_bytes_i),
.svc_rsp_write_bytes_i(svc_rsp_write_bytes_i),
.svc_rsp_saturated_i(svc_rsp_saturated_i),
.svc_req_valid_o(svc_req_valid_o),
.svc_req_kind_o(svc_req_kind_o),
.svc_req_resource_o(svc_req_resource_o),
.svc_req_token_o(svc_req_token_o),
.svc_req_sequence_o(svc_req_sequence_o),
.svc_req_job_o(svc_req_job_o),
.svc_req_epoch_o(svc_req_epoch_o),
.svc_req_task_sequence_o(svc_req_task_sequence_o),
.svc_req_descriptor_o(svc_req_descriptor_o),
.svc_req_object_base_o(svc_req_object_base_o),
.svc_req_object_length_o(svc_req_object_length_o),
.svc_req_object_version_o(svc_req_object_version_o),
.svc_rsp_ready_o(svc_rsp_ready_o),
.event_ready_i(event_ready_i),
.event_valid_o(event_valid_o),
.event_packet_o(event_packet_o),
.close_req_ready_i(close_req_ready_i),
.close_rsp_valid_i(close_rsp_valid_i),
.close_rsp_sequence_i(close_rsp_sequence_i),
.close_rsp_job_i(close_rsp_job_i),
.close_rsp_epoch_i(close_rsp_epoch_i),
.close_rsp_task_sequence_i(close_rsp_task_sequence_i),
.close_rsp_token_i(close_rsp_token_i),
.close_rsp_status_i(close_rsp_status_i),
.close_req_valid_o(close_req_valid_o),
.close_req_sequence_o(close_req_sequence_o),
.close_req_job_o(close_req_job_o),
.close_req_epoch_o(close_req_epoch_o),
.close_req_task_sequence_o(close_req_task_sequence_o),
.close_req_token_o(close_req_token_o),
.close_rsp_ready_o(close_rsp_ready_o),
.life_o(life_o),
.seq_o(seq_o),
.trace_pc_o(trace_pc_o),
.trace_retire_o(trace_retire_o),
.trace_opcode_o(trace_opcode_o),
.trace_pm_owner_o(trace_pm_owner_o),
.trace_ireg_valid_o(trace_ireg_valid_o),
.trace_cancel_token_retire_o(trace_cancel_token_retire_o),
.trace_cancel_object_drop_o(trace_cancel_object_drop_o)
);
