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
reg [287:0] local_image_ids_i;
reg [8:0] local_enabled_i;
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
wire [15:0] trace_live_tokens_o;
wire [8:0] trace_block_active_o;
wire [8:0] trace_terminal_full_o;
wire [8:0] trace_READY_full_o;
wire trace_aborting_o;
reg recover_valid_i;
wire recover_ready_o;
wire [31:0] protocol_fault_count_o;
`ifdef MC_TRANSPORT128
wire tx_valid,tx_ready,tx_sop,tx_eop,tx_credit;
wire [127:0] tx_data,rx_data;
wire [7:0] tx_target,rx_source;
wire rx_valid,rx_ready,rx_sop,rx_eop;
wire [31:0] frame_fault_count,peer_frame_faults;
wire transport_drained_i,peer_drained,peer_tx_credit;
mother_control_native64_transport128 dut(.*);
mc_packet128_bridge peer_frame(
  .clk(clk_i),.reset(!rst_ni),.core_task_valid(return_valid_i),.core_task_ready(return_ready_o),
  .core_task_packet(return_packet_i),.core_task_target(return_packet_i[24+:8]),.core_task_credit(1'b0),
  .tx_valid(rx_valid),.tx_ready(rx_ready),.tx_data(rx_data),.tx_target(rx_source),.tx_sop(rx_sop),.tx_eop(rx_eop),.tx_credit(peer_tx_credit),
  .rx_valid(tx_valid),.rx_ready(tx_ready),.rx_data(tx_data),.rx_source(tx_target),.rx_sop(tx_sop),.rx_eop(tx_eop),
  .core_return_valid(task_valid_o),.core_return_ready(task_ready_i),.core_return_packet(task_packet_o),
  .drained(peer_drained),.frame_fault_count(peer_frame_faults));
assign task_target_o=task_packet_o[24+:8];
assign task_credit_o=task_packet_o[16+:8]==0&&task_valid_o;
`else
mother_control_native64 dut(.*);
`endif
