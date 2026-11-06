reg clk_i;
reg rst_ni;
reg release_valid_i;
reg [31:0] release_sequence_i;
reg [31:0] release_epoch_i;
reg deploy_valid_i;
reg [31:0] deploy_generation_i;
wire release_ready_o;
wire poison_o;
wire image_valid_o;
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
wire [3:0] life_o;
wire [3:0] seq_o;
wire [31:0] trace_pc_o;
wire trace_retire_o;
wire [7:0] trace_opcode_o;
wire [1:0] trace_pm_owner_o;
wire trace_ireg_valid_o;
reg start_valid_i;
reg start_credit_i;
reg [31:0] start_job_i;
reg [31:0] start_epoch_i;
reg [31:0] start_sequence_i;
reg [31:0] start_generation_i;
reg [255:0] start_args_i;
reg [31:0] local_image_id0_i;
reg [31:0] local_image_id1_i;
reg [1:0] local_enabled_i;
wire start_ready_o;
wire task_valid_o;
reg task_ready_i;
wire [7:0] task_target_o;
wire task_credit_o;
wire [511:0] task_packet_o;
reg return_valid_i;
wire return_ready_o;
reg [511:0] return_packet_i;
wire result_valid_o;
reg result_ready_i;
wire [31:0] result_job_o;
wire [31:0] result_epoch_o;
wire [31:0] result_sequence_o;
wire [15:0] result_status_o;
wire [31:0] result_error_pc_o;
wire [7:0] result_source_o;
wire [31:0] result_child_error_pc_o;
wire [31:0] result_failed_task_sequence_o;
wire [31:0] result_confirmed_read_bytes_o;
wire [31:0] result_confirmed_write_bytes_o;
wire result_counter_overflow_o;
wire result_saturated_o;
wire [7:0] trace_live_tokens_o;
wire [1:0] trace_block_active_o;
wire [1:0] trace_terminal_full_o;
wire [1:0] trace_READY_full_o;
wire trace_aborting_o;
mc_min_controller #(.STALL_LIMIT(4096)
`ifdef TB_J_LEASE
  ,.NATIVE_ABI_ID(32'h00017905)
`elsif TB_U_COMPUTE
  ,.NATIVE_ABI_ID(32'h00017904)
`elsif TB_F_COMPUTE
  ,.NATIVE_ABI_ID(32'h00017903)
`elsif TB_COMPUTE_HANDOFF
  ,.NATIVE_ABI_ID(32'h00017902)
`elsif TB_ENABLE_M_DOT_STORE
  `ifdef TB_P_SILU
  ,.NATIVE_ABI_ID(32'h00017902)
  `else
  ,.NATIVE_ABI_ID(32'h00017901)
  `endif
`endif
) dut(.*);
