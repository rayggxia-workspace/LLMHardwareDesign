// Parent RTL assembly only: never export as a composite hard block.
module native_nine_control_plane #(parameter logic [31:0] TOPOLOGY=18503, LC_IMAGE_ID=25001,
parameter integer unsigned SERVICE_STALL_LIMIT=100000000)(
input wire clk,
input wire reset,
input wire mc_release_valid_i,
input wire [31:0] mc_release_sequence_i,
input wire [31:0] mc_release_epoch_i,
input wire mc_deploy_valid_i,
input wire [31:0] mc_deploy_generation_i,
output wire mc_release_ready_o,
output wire mc_poison_o,
output wire mc_image_valid_o,
input wire mc_cfg_req_valid_i,
input wire [2:0] mc_cfg_req_op_i,
input wire [31:0] mc_cfg_req_generation_i,
input wire [13:0] mc_cfg_req_address_i,
input wire [127:0] mc_cfg_req_data_i,
input wire [15:0] mc_cfg_req_total_bytes_i,
input wire [31:0] mc_cfg_req_image_id_i,
input wire [31:0] mc_cfg_req_topology_id_i,
input wire [31:0] mc_cfg_req_abi_id_i,
input wire [31:0] mc_cfg_req_capacity_id_i,
input wire mc_cfg_req_proof_i,
input wire mc_cfg_rsp_ready_i,
output wire mc_cfg_req_ready_o,
output wire mc_cfg_rsp_valid_o,
output wire [15:0] mc_cfg_rsp_status_o,
output wire [127:0] mc_cfg_rsp_data_o,
output wire [31:0] mc_cfg_rsp_generation_o,
output wire [3:0] mc_life_o,
output wire [3:0] mc_seq_o,
output wire [31:0] mc_trace_pc_o,
output wire mc_trace_retire_o,
output wire [7:0] mc_trace_opcode_o,
output wire [1:0] mc_trace_pm_owner_o,
output wire mc_trace_ireg_valid_o,
input wire mc_start_valid_i,
input wire mc_start_credit_i,
input wire [31:0] mc_start_job_i,
input wire [31:0] mc_start_epoch_i,
input wire [31:0] mc_start_sequence_i,
input wire [31:0] mc_start_generation_i,
input wire [287:0] mc_local_image_ids_i,
input wire [8:0] mc_local_enabled_i,
output wire mc_start_ready_o,
output wire [31:0] mc_frame_fault_count,
output wire mc_result_valid_o,
input wire mc_result_ready_i,
output wire [31:0] mc_result_job_o,
output wire [31:0] mc_result_epoch_o,
output wire [31:0] mc_result_sequence_o,
output wire [15:0] mc_result_status_o,
output wire [31:0] mc_result_error_pc_o,
output wire [7:0] mc_result_source_o,
output wire [31:0] mc_result_child_error_pc_o,
output wire [31:0] mc_result_failed_task_sequence_o,
output wire [31:0] mc_result_confirmed_read_bytes_o,
output wire [31:0] mc_result_confirmed_write_bytes_o,
output wire mc_result_counter_overflow_o,
output wire mc_result_saturated_o,
output wire [15:0] mc_trace_live_tokens_o,
output wire [8:0] mc_trace_block_active_o,
output wire [8:0] mc_trace_terminal_full_o,
output wire [8:0] mc_trace_READY_full_o,
output wire mc_trace_aborting_o,
input wire mc_recover_valid_i,
output wire mc_recover_ready_o,
output wire [31:0] mc_protocol_fault_count_o,
output wire [3:0] memory_d_req_valid,
input wire [3:0] memory_d_req_ready,
output wire [255:0] memory_d_req_address,
output wire [255:0] memory_d_req_tag,
input wire [3:0] memory_d_rsp_valid,
output wire [3:0] memory_d_rsp_ready,
input wire [255:0] memory_d_rsp_tag,
input wire [2047:0] memory_d_rsp_data,
output wire memory_d_fence_valid,
input wire memory_d_fence_ready,
output wire [31:0] memory_d_fence_generation,
input wire memory_d_fence_done_valid,
output wire memory_d_fence_done_ready,
input wire [31:0] memory_d_fence_done_generation,
output wire memory_fault_valid,
input wire memory_fault_ready,
output wire [7:0] memory_fault_kind,
output wire [4:0] memory_fault_client,
output wire [31:0] memory_fault_local_tag,
output wire [63:0] memory_fault_global_tag,
output wire [11:0] memory_debug_beats,
output wire [11:0] memory_debug_descriptors,
output wire [31:0] memory_debug_generation,
output wire [3:0] memory_d_req_write,
output wire [2047:0] memory_d_req_data,
input wire [8:0] lc_session_valid,
output wire [8:0] lc_session_ready,
input wire [287:0] lc_session_generation,
input wire [287:0] lc_session_topology,
input wire [8:0] lc_cfg_valid,
output wire [8:0] lc_cfg_ready,
input wire [17:0] lc_cfg_op,
input wire [287:0] lc_cfg_generation,
input wire [287:0] lc_cfg_abi,
input wire [287:0] lc_cfg_capacity,
input wire [287:0] lc_cfg_crc,
input wire [143:0] lc_cfg_bytes,
input wire [125:0] lc_cfg_address,
input wire [1151:0] lc_cfg_data,
output wire [8:0] lc_cfg_rsp_valid,
input wire [8:0] lc_cfg_rsp_ready,
output wire [71:0] lc_cfg_status,
output wire [287:0] lc_cfg_actual_crc,
output wire [8:0] lc_certified,
output wire [8:0] lc_prepared,
output wire [7:0] observe_P0_source,
output wire [287:0] lc_protocol_fault_cycles,
output wire [8:0] lc_pm_trace_valid,
output wire [125:0] lc_pm_trace_address,
output wire [287:0] lc_retired_instructions,
output wire P0_service_resource_m_lc_valid,
input wire P0_service_resource_m_lc_ready,
output wire P0_service_resource_m_lc_sop,
output wire P0_service_resource_m_lc_eop,
output wire [127:0] P0_service_resource_m_lc_data,
input wire P0_service_resource_m_lr_valid,
output wire P0_service_resource_m_lr_ready,
input wire P0_service_resource_m_lr_sop,
input wire P0_service_resource_m_lr_eop,
input wire [127:0] P0_service_resource_m_lr_data,
output wire P0_service_resource_m_a_valid,
input wire P0_service_resource_m_a_ready,
output wire [255:0] P0_service_resource_m_a_data,
output wire [31:0] P0_service_resource_m_a_session,
output wire [2:0] P0_service_resource_m_a_beat,
output wire P0_service_s_req_valid,
output wire P0_service_s_req_write,
input wire P0_service_s_req_ready,
output wire [9:0] P0_service_s_req_address,
output wire [127:0] P0_service_s_req_data,
input wire P0_service_s_rsp_valid,
output wire P0_service_s_rsp_ready,
input wire [127:0] P0_service_s_rsp_data,
input wire P0_service_s_rsp_error,
output wire P0_service_source_failed,
output wire P0_service_quarantine,
output wire [31:0] P0_service_protocol_faults,
output wire P0_service_resource_g_in_valid,
input wire P0_service_resource_g_in_ready,
output wire [63:0] P0_service_resource_g_in_gate,
output wire [63:0] P0_service_resource_g_in_up,
output wire P0_service_resource_g_in_gated,
output wire [1:0] P0_service_resource_g_in_mask,
input wire P0_service_resource_g_out_valid,
output wire P0_service_resource_g_out_ready,
input wire [63:0] P0_service_resource_g_out_data,
input wire [1:0] P0_service_resource_g_out_mask,
input wire P0_service_resource_g_out_error,
output wire [7:0] observe_P1_source,
output wire P1_service_resource_m_lc_valid,
input wire P1_service_resource_m_lc_ready,
output wire P1_service_resource_m_lc_sop,
output wire P1_service_resource_m_lc_eop,
output wire [127:0] P1_service_resource_m_lc_data,
input wire P1_service_resource_m_lr_valid,
output wire P1_service_resource_m_lr_ready,
input wire P1_service_resource_m_lr_sop,
input wire P1_service_resource_m_lr_eop,
input wire [127:0] P1_service_resource_m_lr_data,
output wire P1_service_resource_m_a_valid,
input wire P1_service_resource_m_a_ready,
output wire [255:0] P1_service_resource_m_a_data,
output wire [31:0] P1_service_resource_m_a_session,
output wire [2:0] P1_service_resource_m_a_beat,
output wire P1_service_s_req_valid,
output wire P1_service_s_req_write,
input wire P1_service_s_req_ready,
output wire [9:0] P1_service_s_req_address,
output wire [127:0] P1_service_s_req_data,
input wire P1_service_s_rsp_valid,
output wire P1_service_s_rsp_ready,
input wire [127:0] P1_service_s_rsp_data,
input wire P1_service_s_rsp_error,
output wire P1_service_source_failed,
output wire P1_service_quarantine,
output wire [31:0] P1_service_protocol_faults,
output wire P1_service_resource_g_in_valid,
input wire P1_service_resource_g_in_ready,
output wire [63:0] P1_service_resource_g_in_gate,
output wire [63:0] P1_service_resource_g_in_up,
output wire P1_service_resource_g_in_gated,
output wire [1:0] P1_service_resource_g_in_mask,
input wire P1_service_resource_g_out_valid,
output wire P1_service_resource_g_out_ready,
input wire [63:0] P1_service_resource_g_out_data,
input wire [1:0] P1_service_resource_g_out_mask,
input wire P1_service_resource_g_out_error,
output wire [7:0] observe_P2_source,
output wire P2_service_resource_m_lc_valid,
input wire P2_service_resource_m_lc_ready,
output wire P2_service_resource_m_lc_sop,
output wire P2_service_resource_m_lc_eop,
output wire [127:0] P2_service_resource_m_lc_data,
input wire P2_service_resource_m_lr_valid,
output wire P2_service_resource_m_lr_ready,
input wire P2_service_resource_m_lr_sop,
input wire P2_service_resource_m_lr_eop,
input wire [127:0] P2_service_resource_m_lr_data,
output wire P2_service_resource_m_a_valid,
input wire P2_service_resource_m_a_ready,
output wire [255:0] P2_service_resource_m_a_data,
output wire [31:0] P2_service_resource_m_a_session,
output wire [2:0] P2_service_resource_m_a_beat,
output wire P2_service_s_req_valid,
output wire P2_service_s_req_write,
input wire P2_service_s_req_ready,
output wire [9:0] P2_service_s_req_address,
output wire [127:0] P2_service_s_req_data,
input wire P2_service_s_rsp_valid,
output wire P2_service_s_rsp_ready,
input wire [127:0] P2_service_s_rsp_data,
input wire P2_service_s_rsp_error,
output wire P2_service_source_failed,
output wire P2_service_quarantine,
output wire [31:0] P2_service_protocol_faults,
output wire P2_service_resource_g_in_valid,
input wire P2_service_resource_g_in_ready,
output wire [63:0] P2_service_resource_g_in_gate,
output wire [63:0] P2_service_resource_g_in_up,
output wire P2_service_resource_g_in_gated,
output wire [1:0] P2_service_resource_g_in_mask,
input wire P2_service_resource_g_out_valid,
output wire P2_service_resource_g_out_ready,
input wire [63:0] P2_service_resource_g_out_data,
input wire [1:0] P2_service_resource_g_out_mask,
input wire P2_service_resource_g_out_error,
output wire [7:0] observe_C0_source,
output wire C0_service_s_req_valid,
output wire C0_service_s_req_write,
input wire C0_service_s_req_ready,
output wire [9:0] C0_service_s_req_address,
output wire [127:0] C0_service_s_req_data,
input wire C0_service_s_rsp_valid,
output wire C0_service_s_rsp_ready,
input wire [127:0] C0_service_s_rsp_data,
input wire C0_service_s_rsp_error,
output wire C0_service_resource_e_in_valid,
input wire C0_service_resource_e_in_ready,
output wire [63:0] C0_service_resource_e_in_data,
output wire [3:0] C0_service_resource_e_in_op,
output wire [3:0] C0_service_resource_e_in_mask,
output wire [7:0] C0_service_resource_e_in_shift,
output wire [2:0] C0_service_resource_e_in_minus,
input wire C0_service_resource_e_out_valid,
output wire C0_service_resource_e_out_ready,
input wire [63:0] C0_service_resource_e_out_data,
input wire [3:0] C0_service_resource_e_out_clipped,
input wire C0_service_resource_e_out_error,
output wire [7:0] observe_U0_source,
output wire U0_service_s_req_valid,
output wire U0_service_s_req_write,
input wire U0_service_s_req_ready,
output wire [9:0] U0_service_s_req_address,
output wire [127:0] U0_service_s_req_data,
input wire U0_service_s_rsp_valid,
output wire U0_service_s_rsp_ready,
input wire [127:0] U0_service_s_rsp_data,
input wire U0_service_s_rsp_error,
output wire U0_service_resource_n_cmd_valid,
input wire U0_service_resource_n_cmd_ready,
output wire [31:0] U0_service_resource_n_cmd_tag,
output wire [1:0] U0_service_resource_n_cmd_mode,
output wire [9:0] U0_service_resource_n_cmd_base,
output wire [12:0] U0_service_resource_n_cmd_count,
output wire U0_service_resource_n_cmd_committed,
output wire U0_service_resource_n_abort_valid,
input wire U0_service_resource_n_abort_ready,
output wire [31:0] U0_service_resource_n_abort_tag,
input wire U0_service_resource_n_rsp_valid,
output wire U0_service_resource_n_rsp_ready,
input wire [31:0] U0_service_resource_n_rsp_tag,
input wire U0_service_resource_n_rsp_error,
input wire U0_service_resource_n_rsp_aborted,
input wire [11:0] U0_service_resource_n_rsp_writes,
input wire U0_service_resource_n_s_req_valid,
input wire U0_service_resource_n_s_req_write,
output wire U0_service_resource_n_s_req_ready,
input wire [9:0] U0_service_resource_n_s_req_address,
input wire [127:0] U0_service_resource_n_s_req_data,
output wire U0_service_resource_n_s_rsp_valid,
input wire U0_service_resource_n_s_rsp_ready,
output wire [127:0] U0_service_resource_n_s_rsp_data,
output wire U0_service_resource_n_s_rsp_error,
output wire [7:0] observe_J0_source,
output wire J0_service_s_req_valid,
output wire J0_service_s_req_write,
input wire J0_service_s_req_ready,
output wire [9:0] J0_service_s_req_address,
output wire [127:0] J0_service_s_req_data,
input wire J0_service_s_rsp_valid,
output wire J0_service_s_rsp_ready,
input wire [127:0] J0_service_s_rsp_data,
input wire J0_service_s_rsp_error,
output wire J0_service_resource_e_in_valid,
input wire J0_service_resource_e_in_ready,
output wire [63:0] J0_service_resource_e_in_data,
output wire [3:0] J0_service_resource_e_in_op,
output wire [3:0] J0_service_resource_e_in_mask,
output wire [7:0] J0_service_resource_e_in_shift,
output wire [2:0] J0_service_resource_e_in_minus,
input wire J0_service_resource_e_out_valid,
output wire J0_service_resource_e_out_ready,
input wire [63:0] J0_service_resource_e_out_data,
input wire [3:0] J0_service_resource_e_out_clipped,
input wire J0_service_resource_e_out_error,
output wire [7:0] observe_F0_source,
output wire F0_service_s_req_valid,
output wire F0_service_s_req_write,
input wire F0_service_s_req_ready,
output wire [9:0] F0_service_s_req_address,
output wire [127:0] F0_service_s_req_data,
input wire F0_service_s_rsp_valid,
output wire F0_service_s_rsp_ready,
input wire [127:0] F0_service_s_rsp_data,
input wire F0_service_s_rsp_error,
output wire F0_service_resource_e_in_valid,
input wire F0_service_resource_e_in_ready,
output wire [63:0] F0_service_resource_e_in_data,
output wire [3:0] F0_service_resource_e_in_op,
output wire [3:0] F0_service_resource_e_in_mask,
output wire [7:0] F0_service_resource_e_in_shift,
output wire [2:0] F0_service_resource_e_in_minus,
input wire F0_service_resource_e_out_valid,
output wire F0_service_resource_e_out_ready,
input wire [63:0] F0_service_resource_e_out_data,
input wire [3:0] F0_service_resource_e_out_clipped,
input wire F0_service_resource_e_out_error,
output wire [7:0] observe_U1_source,
output wire U1_service_s_req_valid,
output wire U1_service_s_req_write,
input wire U1_service_s_req_ready,
output wire [9:0] U1_service_s_req_address,
output wire [127:0] U1_service_s_req_data,
input wire U1_service_s_rsp_valid,
output wire U1_service_s_rsp_ready,
input wire [127:0] U1_service_s_rsp_data,
input wire U1_service_s_rsp_error,
output wire U1_service_resource_n_cmd_valid,
input wire U1_service_resource_n_cmd_ready,
output wire [31:0] U1_service_resource_n_cmd_tag,
output wire [1:0] U1_service_resource_n_cmd_mode,
output wire [9:0] U1_service_resource_n_cmd_base,
output wire [12:0] U1_service_resource_n_cmd_count,
output wire U1_service_resource_n_cmd_committed,
output wire U1_service_resource_n_abort_valid,
input wire U1_service_resource_n_abort_ready,
output wire [31:0] U1_service_resource_n_abort_tag,
input wire U1_service_resource_n_rsp_valid,
output wire U1_service_resource_n_rsp_ready,
input wire [31:0] U1_service_resource_n_rsp_tag,
input wire U1_service_resource_n_rsp_error,
input wire U1_service_resource_n_rsp_aborted,
input wire [11:0] U1_service_resource_n_rsp_writes,
input wire U1_service_resource_n_s_req_valid,
input wire U1_service_resource_n_s_req_write,
output wire U1_service_resource_n_s_req_ready,
input wire [9:0] U1_service_resource_n_s_req_address,
input wire [127:0] U1_service_resource_n_s_req_data,
output wire U1_service_resource_n_s_rsp_valid,
input wire U1_service_resource_n_s_rsp_ready,
output wire [127:0] U1_service_resource_n_s_rsp_data,
output wire U1_service_resource_n_s_rsp_error,
output wire [7:0] observe_J1_source,
output wire J1_service_s_req_valid,
output wire J1_service_s_req_write,
input wire J1_service_s_req_ready,
output wire [9:0] J1_service_s_req_address,
output wire [127:0] J1_service_s_req_data,
input wire J1_service_s_rsp_valid,
output wire J1_service_s_rsp_ready,
input wire [127:0] J1_service_s_rsp_data,
input wire J1_service_s_rsp_error,
output wire J1_service_resource_e_in_valid,
input wire J1_service_resource_e_in_ready,
output wire [63:0] J1_service_resource_e_in_data,
output wire [3:0] J1_service_resource_e_in_op,
output wire [3:0] J1_service_resource_e_in_mask,
output wire [7:0] J1_service_resource_e_in_shift,
output wire [2:0] J1_service_resource_e_in_minus,
input wire J1_service_resource_e_out_valid,
output wire J1_service_resource_e_out_ready,
input wire [63:0] J1_service_resource_e_out_data,
input wire [3:0] J1_service_resource_e_out_clipped,
input wire J1_service_resource_e_out_error,
input wire P0_M_mc_req_valid,
output wire P0_M_mc_req_ready,
input wire [63:0] P0_M_mc_req_address,
input wire [31:0] P0_M_mc_req_tag,
input wire P0_M_mc_req_channel,
input wire [4:0] P0_M_mc_req_record_beats,
output wire P0_M_mc_rsp_valid,
input wire P0_M_mc_rsp_ready,
output wire [31:0] P0_M_mc_rsp_tag,
output wire [511:0] P0_M_mc_rsp_data,
input wire P0_M_mc_close_valid,
output wire P0_M_mc_close_ready,
input wire [31:0] P0_M_mc_close_tag_base,
input wire P0_M_mc_fence_req_valid,
output wire P0_M_mc_fence_req_ready,
input wire [31:0] P0_M_mc_fence_req_cookie,
input wire [8:0] P0_M_mc_fence_req_epoch,
output wire P0_M_mc_fence_done_valid,
input wire P0_M_mc_fence_done_ready,
output wire [31:0] P0_M_mc_fence_done_cookie,
output wire [8:0] P0_M_mc_fence_done_epoch,
input wire P1_M_mc_req_valid,
output wire P1_M_mc_req_ready,
input wire [63:0] P1_M_mc_req_address,
input wire [31:0] P1_M_mc_req_tag,
input wire P1_M_mc_req_channel,
input wire [4:0] P1_M_mc_req_record_beats,
output wire P1_M_mc_rsp_valid,
input wire P1_M_mc_rsp_ready,
output wire [31:0] P1_M_mc_rsp_tag,
output wire [511:0] P1_M_mc_rsp_data,
input wire P1_M_mc_close_valid,
output wire P1_M_mc_close_ready,
input wire [31:0] P1_M_mc_close_tag_base,
input wire P1_M_mc_fence_req_valid,
output wire P1_M_mc_fence_req_ready,
input wire [31:0] P1_M_mc_fence_req_cookie,
input wire [8:0] P1_M_mc_fence_req_epoch,
output wire P1_M_mc_fence_done_valid,
input wire P1_M_mc_fence_done_ready,
output wire [31:0] P1_M_mc_fence_done_cookie,
output wire [8:0] P1_M_mc_fence_done_epoch,
input wire P2_M_mc_req_valid,
output wire P2_M_mc_req_ready,
input wire [63:0] P2_M_mc_req_address,
input wire [31:0] P2_M_mc_req_tag,
input wire P2_M_mc_req_channel,
input wire [4:0] P2_M_mc_req_record_beats,
output wire P2_M_mc_rsp_valid,
input wire P2_M_mc_rsp_ready,
output wire [31:0] P2_M_mc_rsp_tag,
output wire [511:0] P2_M_mc_rsp_data,
input wire P2_M_mc_close_valid,
output wire P2_M_mc_close_ready,
input wire [31:0] P2_M_mc_close_tag_base,
input wire P2_M_mc_fence_req_valid,
output wire P2_M_mc_fence_req_ready,
input wire [31:0] P2_M_mc_fence_req_cookie,
input wire [8:0] P2_M_mc_fence_req_epoch,
output wire P2_M_mc_fence_done_valid,
input wire P2_M_mc_fence_done_ready,
output wire [31:0] P2_M_mc_fence_done_cookie,
output wire [8:0] P2_M_mc_fence_done_epoch
);
wire mc_tx_valid;
wire mc_tx_ready;
wire [127:0] mc_tx_data;
wire [7:0] mc_tx_target;
wire mc_tx_sop;
wire mc_tx_eop;
wire mc_tx_credit;
wire mc_rx_valid;
wire mc_rx_ready;
wire [127:0] mc_rx_data;
wire [7:0] mc_rx_source;
wire mc_rx_sop;
wire mc_rx_eop;
wire [8:0] switch_lc_rx_valid;
wire [8:0] switch_lc_rx_ready;
wire [71:0] switch_lc_rx_target;
wire [71:0] switch_lc_rx_header_target;
wire [8:0] switch_lc_tx_valid;
wire [8:0] switch_lc_tx_ready;
wire [1151:0] switch_lc_tx_data;
wire [8:0] switch_lc_tx_sop;
wire [8:0] switch_lc_tx_eop;
wire switch_idle;
wire [8:0] owner_idle;
wire all_drained;
wire [11:0] mem_c_req_valid;
wire [11:0] mem_c_req_ready;
wire [767:0] mem_c_req_address;
wire [383:0] mem_c_req_tag;
wire [11:0] mem_c_req_channel;
wire [59:0] mem_c_req_record_beats;
wire [11:0] mem_c_rsp_valid;
wire [11:0] mem_c_rsp_ready;
wire [383:0] mem_c_rsp_tag;
wire [6143:0] mem_c_rsp_data;
wire [11:0] mem_c_close_valid;
wire [11:0] mem_c_close_ready;
wire [383:0] mem_c_close_tag_base;
wire [11:0] mem_c_cancel_valid;
wire [11:0] mem_c_cancel_ready;
wire [383:0] mem_c_cancel_tag;
wire [11:0] mem_c_cancel_ack_valid;
wire [11:0] mem_c_cancel_ack_ready;
wire [383:0] mem_c_cancel_ack_tag;
wire [11:0] mem_c_cancel_ack_rejected;
wire [11:0] mem_c_fence_valid;
wire [11:0] mem_c_fence_ready;
wire [383:0] mem_c_fence_cookie;
wire [107:0] mem_c_fence_epoch;
wire [11:0] mem_c_fence_done_valid;
wire [11:0] mem_c_fence_done_ready;
wire [383:0] mem_c_fence_done_cookie;
wire [107:0] mem_c_fence_done_epoch;
wire [8:0] mem_service_req_valid;
wire [8:0] mem_service_req_ready;
wire [575:0] mem_service_req_address;
wire [575:0] mem_service_req_tag;
wire [8:0] mem_service_rsp_valid;
wire [8:0] mem_service_rsp_ready;
wire [575:0] mem_service_rsp_tag;
wire [4607:0] mem_service_rsp_data;
wire [8:0] mem_service_rsp_error;
wire [8:0] mem_service_idle;
wire [8:0] mem_service_protocol_fault;
wire [8:0] mem_write_req_valid;
wire [8:0] mem_write_req_ready;
wire [575:0] mem_write_req_address;
wire [575:0] mem_write_req_tag;
wire [4607:0] mem_write_req_data;
wire [8:0] mem_write_done_valid;
wire [8:0] mem_write_done_ready;
wire [575:0] mem_write_done_tag;
wire [8:0] mem_write_done_error;
wire [8:0] mem_write_idle;
wire [8:0] mem_write_protocol_fault;
wire mem_transport_idle;
wire P0_service_rd_valid;
wire P0_service_rd_ready;
wire [63:0] P0_service_rd_address;
wire [63:0] P0_service_rd_tag;
wire P0_service_rd_rsp_valid;
wire P0_service_rd_rsp_ready;
wire [63:0] P0_service_rd_rsp_tag;
wire [511:0] P0_service_rd_rsp_data;
wire P0_service_rd_rsp_error;
wire P0_service_wr_valid;
wire P0_service_wr_ready;
wire [63:0] P0_service_wr_address;
wire [63:0] P0_service_wr_tag;
wire [511:0] P0_service_wr_data;
wire P0_service_wr_done_valid;
wire P0_service_wr_done_ready;
wire [63:0] P0_service_wr_done_tag;
wire P0_service_wr_done_error;
wire P1_service_rd_valid;
wire P1_service_rd_ready;
wire [63:0] P1_service_rd_address;
wire [63:0] P1_service_rd_tag;
wire P1_service_rd_rsp_valid;
wire P1_service_rd_rsp_ready;
wire [63:0] P1_service_rd_rsp_tag;
wire [511:0] P1_service_rd_rsp_data;
wire P1_service_rd_rsp_error;
wire P1_service_wr_valid;
wire P1_service_wr_ready;
wire [63:0] P1_service_wr_address;
wire [63:0] P1_service_wr_tag;
wire [511:0] P1_service_wr_data;
wire P1_service_wr_done_valid;
wire P1_service_wr_done_ready;
wire [63:0] P1_service_wr_done_tag;
wire P1_service_wr_done_error;
wire P2_service_rd_valid;
wire P2_service_rd_ready;
wire [63:0] P2_service_rd_address;
wire [63:0] P2_service_rd_tag;
wire P2_service_rd_rsp_valid;
wire P2_service_rd_rsp_ready;
wire [63:0] P2_service_rd_rsp_tag;
wire [511:0] P2_service_rd_rsp_data;
wire P2_service_rd_rsp_error;
wire P2_service_wr_valid;
wire P2_service_wr_ready;
wire [63:0] P2_service_wr_address;
wire [63:0] P2_service_wr_tag;
wire [511:0] P2_service_wr_data;
wire P2_service_wr_done_valid;
wire P2_service_wr_done_ready;
wire [63:0] P2_service_wr_done_tag;
wire P2_service_wr_done_error;
wire C0_service_rd_valid;
wire C0_service_rd_ready;
wire [63:0] C0_service_rd_address;
wire [63:0] C0_service_rd_tag;
wire C0_service_rd_rsp_valid;
wire C0_service_rd_rsp_ready;
wire [63:0] C0_service_rd_rsp_tag;
wire [511:0] C0_service_rd_rsp_data;
wire C0_service_rd_rsp_error;
wire C0_service_wr_valid;
wire C0_service_wr_ready;
wire [63:0] C0_service_wr_address;
wire [63:0] C0_service_wr_tag;
wire [511:0] C0_service_wr_data;
wire C0_service_wr_done_valid;
wire C0_service_wr_done_ready;
wire [63:0] C0_service_wr_done_tag;
wire C0_service_wr_done_error;
wire U0_service_rd_valid;
wire U0_service_rd_ready;
wire [63:0] U0_service_rd_address;
wire [63:0] U0_service_rd_tag;
wire U0_service_rd_rsp_valid;
wire U0_service_rd_rsp_ready;
wire [63:0] U0_service_rd_rsp_tag;
wire [511:0] U0_service_rd_rsp_data;
wire U0_service_rd_rsp_error;
wire U0_service_wr_valid;
wire U0_service_wr_ready;
wire [63:0] U0_service_wr_address;
wire [63:0] U0_service_wr_tag;
wire [511:0] U0_service_wr_data;
wire U0_service_wr_done_valid;
wire U0_service_wr_done_ready;
wire [63:0] U0_service_wr_done_tag;
wire U0_service_wr_done_error;
wire J0_service_rd_valid;
wire J0_service_rd_ready;
wire [63:0] J0_service_rd_address;
wire [63:0] J0_service_rd_tag;
wire J0_service_rd_rsp_valid;
wire J0_service_rd_rsp_ready;
wire [63:0] J0_service_rd_rsp_tag;
wire [511:0] J0_service_rd_rsp_data;
wire J0_service_rd_rsp_error;
wire J0_service_wr_valid;
wire J0_service_wr_ready;
wire [63:0] J0_service_wr_address;
wire [63:0] J0_service_wr_tag;
wire [511:0] J0_service_wr_data;
wire J0_service_wr_done_valid;
wire J0_service_wr_done_ready;
wire [63:0] J0_service_wr_done_tag;
wire J0_service_wr_done_error;
wire F0_service_rd_valid;
wire F0_service_rd_ready;
wire [63:0] F0_service_rd_address;
wire [63:0] F0_service_rd_tag;
wire F0_service_rd_rsp_valid;
wire F0_service_rd_rsp_ready;
wire [63:0] F0_service_rd_rsp_tag;
wire [511:0] F0_service_rd_rsp_data;
wire F0_service_rd_rsp_error;
wire F0_service_wr_valid;
wire F0_service_wr_ready;
wire [63:0] F0_service_wr_address;
wire [63:0] F0_service_wr_tag;
wire [511:0] F0_service_wr_data;
wire F0_service_wr_done_valid;
wire F0_service_wr_done_ready;
wire [63:0] F0_service_wr_done_tag;
wire F0_service_wr_done_error;
wire U1_service_rd_valid;
wire U1_service_rd_ready;
wire [63:0] U1_service_rd_address;
wire [63:0] U1_service_rd_tag;
wire U1_service_rd_rsp_valid;
wire U1_service_rd_rsp_ready;
wire [63:0] U1_service_rd_rsp_tag;
wire [511:0] U1_service_rd_rsp_data;
wire U1_service_rd_rsp_error;
wire U1_service_wr_valid;
wire U1_service_wr_ready;
wire [63:0] U1_service_wr_address;
wire [63:0] U1_service_wr_tag;
wire [511:0] U1_service_wr_data;
wire U1_service_wr_done_valid;
wire U1_service_wr_done_ready;
wire [63:0] U1_service_wr_done_tag;
wire U1_service_wr_done_error;
wire J1_service_rd_valid;
wire J1_service_rd_ready;
wire [63:0] J1_service_rd_address;
wire [63:0] J1_service_rd_tag;
wire J1_service_rd_rsp_valid;
wire J1_service_rd_rsp_ready;
wire [63:0] J1_service_rd_rsp_tag;
wire [511:0] J1_service_rd_rsp_data;
wire J1_service_rd_rsp_error;
wire J1_service_wr_valid;
wire J1_service_wr_ready;
wire [63:0] J1_service_wr_address;
wire [63:0] J1_service_wr_tag;
wire [511:0] J1_service_wr_data;
wire J1_service_wr_done_valid;
wire J1_service_wr_done_ready;
wire [63:0] J1_service_wr_done_tag;
wire J1_service_wr_done_error;
assign all_drained=switch_idle&&(&owner_idle)&&mem_transport_idle&&(&mem_service_idle)&&(&mem_write_idle);
assign mem_service_req_valid[0+:1]=P0_service_rd_valid;
assign P0_service_rd_ready=mem_service_req_ready[0+:1];
assign mem_service_req_address[0+:64]=P0_service_rd_address;
assign mem_service_req_tag[0+:64]=P0_service_rd_tag;
assign P0_service_rd_rsp_valid=mem_service_rsp_valid[0+:1];
assign mem_service_rsp_ready[0+:1]=P0_service_rd_rsp_ready;
assign P0_service_rd_rsp_tag=mem_service_rsp_tag[0+:64];
assign P0_service_rd_rsp_data=mem_service_rsp_data[0+:512];
assign P0_service_rd_rsp_error=mem_service_rsp_error[0+:1];
assign mem_write_req_valid[0+:1]=P0_service_wr_valid;
assign P0_service_wr_ready=mem_write_req_ready[0+:1];
assign mem_write_req_address[0+:64]=P0_service_wr_address;
assign mem_write_req_tag[0+:64]=P0_service_wr_tag;
assign mem_write_req_data[0+:512]=P0_service_wr_data;
assign P0_service_wr_done_valid=mem_write_done_valid[0+:1];
assign mem_write_done_ready[0+:1]=P0_service_wr_done_ready;
assign P0_service_wr_done_tag=mem_write_done_tag[0+:64];
assign P0_service_wr_done_error=mem_write_done_error[0+:1];
assign mem_c_cancel_valid[0+:1]='0;
assign mem_c_cancel_tag[0+:32]='0;
assign mem_c_cancel_ack_ready[0+:1]='1;
assign mem_c_fence_valid[0+:1]='0;
assign mem_c_fence_cookie[0+:32]='0;
assign mem_c_fence_epoch[0+:9]='0;
assign mem_c_fence_done_ready[0+:1]='1;
assign mem_service_req_valid[1+:1]=P1_service_rd_valid;
assign P1_service_rd_ready=mem_service_req_ready[1+:1];
assign mem_service_req_address[64+:64]=P1_service_rd_address;
assign mem_service_req_tag[64+:64]=P1_service_rd_tag;
assign P1_service_rd_rsp_valid=mem_service_rsp_valid[1+:1];
assign mem_service_rsp_ready[1+:1]=P1_service_rd_rsp_ready;
assign P1_service_rd_rsp_tag=mem_service_rsp_tag[64+:64];
assign P1_service_rd_rsp_data=mem_service_rsp_data[512+:512];
assign P1_service_rd_rsp_error=mem_service_rsp_error[1+:1];
assign mem_write_req_valid[1+:1]=P1_service_wr_valid;
assign P1_service_wr_ready=mem_write_req_ready[1+:1];
assign mem_write_req_address[64+:64]=P1_service_wr_address;
assign mem_write_req_tag[64+:64]=P1_service_wr_tag;
assign mem_write_req_data[512+:512]=P1_service_wr_data;
assign P1_service_wr_done_valid=mem_write_done_valid[1+:1];
assign mem_write_done_ready[1+:1]=P1_service_wr_done_ready;
assign P1_service_wr_done_tag=mem_write_done_tag[64+:64];
assign P1_service_wr_done_error=mem_write_done_error[1+:1];
assign mem_c_cancel_valid[1+:1]='0;
assign mem_c_cancel_tag[32+:32]='0;
assign mem_c_cancel_ack_ready[1+:1]='1;
assign mem_c_fence_valid[1+:1]='0;
assign mem_c_fence_cookie[32+:32]='0;
assign mem_c_fence_epoch[9+:9]='0;
assign mem_c_fence_done_ready[1+:1]='1;
assign mem_service_req_valid[2+:1]=P2_service_rd_valid;
assign P2_service_rd_ready=mem_service_req_ready[2+:1];
assign mem_service_req_address[128+:64]=P2_service_rd_address;
assign mem_service_req_tag[128+:64]=P2_service_rd_tag;
assign P2_service_rd_rsp_valid=mem_service_rsp_valid[2+:1];
assign mem_service_rsp_ready[2+:1]=P2_service_rd_rsp_ready;
assign P2_service_rd_rsp_tag=mem_service_rsp_tag[128+:64];
assign P2_service_rd_rsp_data=mem_service_rsp_data[1024+:512];
assign P2_service_rd_rsp_error=mem_service_rsp_error[2+:1];
assign mem_write_req_valid[2+:1]=P2_service_wr_valid;
assign P2_service_wr_ready=mem_write_req_ready[2+:1];
assign mem_write_req_address[128+:64]=P2_service_wr_address;
assign mem_write_req_tag[128+:64]=P2_service_wr_tag;
assign mem_write_req_data[1024+:512]=P2_service_wr_data;
assign P2_service_wr_done_valid=mem_write_done_valid[2+:1];
assign mem_write_done_ready[2+:1]=P2_service_wr_done_ready;
assign P2_service_wr_done_tag=mem_write_done_tag[128+:64];
assign P2_service_wr_done_error=mem_write_done_error[2+:1];
assign mem_c_cancel_valid[2+:1]='0;
assign mem_c_cancel_tag[64+:32]='0;
assign mem_c_cancel_ack_ready[2+:1]='1;
assign mem_c_fence_valid[2+:1]='0;
assign mem_c_fence_cookie[64+:32]='0;
assign mem_c_fence_epoch[18+:9]='0;
assign mem_c_fence_done_ready[2+:1]='1;
assign mem_service_req_valid[3+:1]=C0_service_rd_valid;
assign C0_service_rd_ready=mem_service_req_ready[3+:1];
assign mem_service_req_address[192+:64]=C0_service_rd_address;
assign mem_service_req_tag[192+:64]=C0_service_rd_tag;
assign C0_service_rd_rsp_valid=mem_service_rsp_valid[3+:1];
assign mem_service_rsp_ready[3+:1]=C0_service_rd_rsp_ready;
assign C0_service_rd_rsp_tag=mem_service_rsp_tag[192+:64];
assign C0_service_rd_rsp_data=mem_service_rsp_data[1536+:512];
assign C0_service_rd_rsp_error=mem_service_rsp_error[3+:1];
assign mem_write_req_valid[3+:1]=C0_service_wr_valid;
assign C0_service_wr_ready=mem_write_req_ready[3+:1];
assign mem_write_req_address[192+:64]=C0_service_wr_address;
assign mem_write_req_tag[192+:64]=C0_service_wr_tag;
assign mem_write_req_data[1536+:512]=C0_service_wr_data;
assign C0_service_wr_done_valid=mem_write_done_valid[3+:1];
assign mem_write_done_ready[3+:1]=C0_service_wr_done_ready;
assign C0_service_wr_done_tag=mem_write_done_tag[192+:64];
assign C0_service_wr_done_error=mem_write_done_error[3+:1];
assign mem_c_cancel_valid[3+:1]='0;
assign mem_c_cancel_tag[96+:32]='0;
assign mem_c_cancel_ack_ready[3+:1]='1;
assign mem_c_fence_valid[3+:1]='0;
assign mem_c_fence_cookie[96+:32]='0;
assign mem_c_fence_epoch[27+:9]='0;
assign mem_c_fence_done_ready[3+:1]='1;
assign mem_service_req_valid[4+:1]=U0_service_rd_valid;
assign U0_service_rd_ready=mem_service_req_ready[4+:1];
assign mem_service_req_address[256+:64]=U0_service_rd_address;
assign mem_service_req_tag[256+:64]=U0_service_rd_tag;
assign U0_service_rd_rsp_valid=mem_service_rsp_valid[4+:1];
assign mem_service_rsp_ready[4+:1]=U0_service_rd_rsp_ready;
assign U0_service_rd_rsp_tag=mem_service_rsp_tag[256+:64];
assign U0_service_rd_rsp_data=mem_service_rsp_data[2048+:512];
assign U0_service_rd_rsp_error=mem_service_rsp_error[4+:1];
assign mem_write_req_valid[4+:1]=U0_service_wr_valid;
assign U0_service_wr_ready=mem_write_req_ready[4+:1];
assign mem_write_req_address[256+:64]=U0_service_wr_address;
assign mem_write_req_tag[256+:64]=U0_service_wr_tag;
assign mem_write_req_data[2048+:512]=U0_service_wr_data;
assign U0_service_wr_done_valid=mem_write_done_valid[4+:1];
assign mem_write_done_ready[4+:1]=U0_service_wr_done_ready;
assign U0_service_wr_done_tag=mem_write_done_tag[256+:64];
assign U0_service_wr_done_error=mem_write_done_error[4+:1];
assign mem_c_cancel_valid[4+:1]='0;
assign mem_c_cancel_tag[128+:32]='0;
assign mem_c_cancel_ack_ready[4+:1]='1;
assign mem_c_fence_valid[4+:1]='0;
assign mem_c_fence_cookie[128+:32]='0;
assign mem_c_fence_epoch[36+:9]='0;
assign mem_c_fence_done_ready[4+:1]='1;
assign mem_service_req_valid[5+:1]=J0_service_rd_valid;
assign J0_service_rd_ready=mem_service_req_ready[5+:1];
assign mem_service_req_address[320+:64]=J0_service_rd_address;
assign mem_service_req_tag[320+:64]=J0_service_rd_tag;
assign J0_service_rd_rsp_valid=mem_service_rsp_valid[5+:1];
assign mem_service_rsp_ready[5+:1]=J0_service_rd_rsp_ready;
assign J0_service_rd_rsp_tag=mem_service_rsp_tag[320+:64];
assign J0_service_rd_rsp_data=mem_service_rsp_data[2560+:512];
assign J0_service_rd_rsp_error=mem_service_rsp_error[5+:1];
assign mem_write_req_valid[5+:1]=J0_service_wr_valid;
assign J0_service_wr_ready=mem_write_req_ready[5+:1];
assign mem_write_req_address[320+:64]=J0_service_wr_address;
assign mem_write_req_tag[320+:64]=J0_service_wr_tag;
assign mem_write_req_data[2560+:512]=J0_service_wr_data;
assign J0_service_wr_done_valid=mem_write_done_valid[5+:1];
assign mem_write_done_ready[5+:1]=J0_service_wr_done_ready;
assign J0_service_wr_done_tag=mem_write_done_tag[320+:64];
assign J0_service_wr_done_error=mem_write_done_error[5+:1];
assign mem_c_cancel_valid[5+:1]='0;
assign mem_c_cancel_tag[160+:32]='0;
assign mem_c_cancel_ack_ready[5+:1]='1;
assign mem_c_fence_valid[5+:1]='0;
assign mem_c_fence_cookie[160+:32]='0;
assign mem_c_fence_epoch[45+:9]='0;
assign mem_c_fence_done_ready[5+:1]='1;
assign mem_service_req_valid[6+:1]=F0_service_rd_valid;
assign F0_service_rd_ready=mem_service_req_ready[6+:1];
assign mem_service_req_address[384+:64]=F0_service_rd_address;
assign mem_service_req_tag[384+:64]=F0_service_rd_tag;
assign F0_service_rd_rsp_valid=mem_service_rsp_valid[6+:1];
assign mem_service_rsp_ready[6+:1]=F0_service_rd_rsp_ready;
assign F0_service_rd_rsp_tag=mem_service_rsp_tag[384+:64];
assign F0_service_rd_rsp_data=mem_service_rsp_data[3072+:512];
assign F0_service_rd_rsp_error=mem_service_rsp_error[6+:1];
assign mem_write_req_valid[6+:1]=F0_service_wr_valid;
assign F0_service_wr_ready=mem_write_req_ready[6+:1];
assign mem_write_req_address[384+:64]=F0_service_wr_address;
assign mem_write_req_tag[384+:64]=F0_service_wr_tag;
assign mem_write_req_data[3072+:512]=F0_service_wr_data;
assign F0_service_wr_done_valid=mem_write_done_valid[6+:1];
assign mem_write_done_ready[6+:1]=F0_service_wr_done_ready;
assign F0_service_wr_done_tag=mem_write_done_tag[384+:64];
assign F0_service_wr_done_error=mem_write_done_error[6+:1];
assign mem_c_cancel_valid[6+:1]='0;
assign mem_c_cancel_tag[192+:32]='0;
assign mem_c_cancel_ack_ready[6+:1]='1;
assign mem_c_fence_valid[6+:1]='0;
assign mem_c_fence_cookie[192+:32]='0;
assign mem_c_fence_epoch[54+:9]='0;
assign mem_c_fence_done_ready[6+:1]='1;
assign mem_service_req_valid[7+:1]='0;
assign U1_service_rd_ready='0;
assign mem_service_req_address[448+:64]='0;
assign mem_service_req_tag[448+:64]='0;
assign U1_service_rd_rsp_valid='0;
assign mem_service_rsp_ready[7+:1]='0;
assign U1_service_rd_rsp_tag='0;
assign U1_service_rd_rsp_data='0;
assign U1_service_rd_rsp_error='0;
assign mem_write_req_valid[7+:1]='0;
assign U1_service_wr_ready='0;
assign mem_write_req_address[448+:64]='0;
assign mem_write_req_tag[448+:64]='0;
assign mem_write_req_data[3584+:512]='0;
assign U1_service_wr_done_valid='0;
assign mem_write_done_ready[7+:1]='0;
assign U1_service_wr_done_tag='0;
assign U1_service_wr_done_error='0;
assign mem_c_cancel_valid[7+:1]='0;
assign mem_c_cancel_tag[224+:32]='0;
assign mem_c_cancel_ack_ready[7+:1]='1;
assign mem_c_fence_valid[7+:1]='0;
assign mem_c_fence_cookie[224+:32]='0;
assign mem_c_fence_epoch[63+:9]='0;
assign mem_c_fence_done_ready[7+:1]='1;
assign mem_service_req_valid[8+:1]='0;
assign J1_service_rd_ready='0;
assign mem_service_req_address[512+:64]='0;
assign mem_service_req_tag[512+:64]='0;
assign J1_service_rd_rsp_valid='0;
assign mem_service_rsp_ready[8+:1]='0;
assign J1_service_rd_rsp_tag='0;
assign J1_service_rd_rsp_data='0;
assign J1_service_rd_rsp_error='0;
assign mem_write_req_valid[8+:1]='0;
assign J1_service_wr_ready='0;
assign mem_write_req_address[512+:64]='0;
assign mem_write_req_tag[512+:64]='0;
assign mem_write_req_data[4096+:512]='0;
assign J1_service_wr_done_valid='0;
assign mem_write_done_ready[8+:1]='0;
assign J1_service_wr_done_tag='0;
assign J1_service_wr_done_error='0;
assign mem_c_cancel_valid[8+:1]='0;
assign mem_c_cancel_tag[256+:32]='0;
assign mem_c_cancel_ack_ready[8+:1]='1;
assign mem_c_fence_valid[8+:1]='0;
assign mem_c_fence_cookie[256+:32]='0;
assign mem_c_fence_epoch[72+:9]='0;
assign mem_c_fence_done_ready[8+:1]='1;
assign mem_c_req_valid[9+:1]=P0_M_mc_req_valid;
assign P0_M_mc_req_ready=mem_c_req_ready[9+:1];
assign mem_c_req_address[576+:64]=P0_M_mc_req_address;
assign mem_c_req_tag[288+:32]=P0_M_mc_req_tag;
assign mem_c_req_channel[9+:1]=P0_M_mc_req_channel;
assign mem_c_req_record_beats[45+:5]=P0_M_mc_req_record_beats;
assign P0_M_mc_rsp_valid=mem_c_rsp_valid[9+:1];
assign mem_c_rsp_ready[9+:1]=P0_M_mc_rsp_ready;
assign P0_M_mc_rsp_tag=mem_c_rsp_tag[288+:32];
assign P0_M_mc_rsp_data=mem_c_rsp_data[4608+:512];
assign mem_c_close_valid[9+:1]=P0_M_mc_close_valid;
assign P0_M_mc_close_ready=mem_c_close_ready[9+:1];
assign mem_c_close_tag_base[288+:32]=P0_M_mc_close_tag_base;
assign mem_c_cancel_valid[9+:1]='0;
assign mem_c_cancel_tag[288+:32]='0;
assign mem_c_cancel_ack_ready[9+:1]='1;
assign mem_c_fence_valid[9+:1]=P0_M_mc_fence_req_valid;
assign P0_M_mc_fence_req_ready=mem_c_fence_ready[9+:1];
assign mem_c_fence_cookie[288+:32]=P0_M_mc_fence_req_cookie;
assign mem_c_fence_epoch[81+:9]=P0_M_mc_fence_req_epoch;
assign P0_M_mc_fence_done_valid=mem_c_fence_done_valid[9+:1];
assign mem_c_fence_done_ready[9+:1]=P0_M_mc_fence_done_ready;
assign P0_M_mc_fence_done_cookie=mem_c_fence_done_cookie[288+:32];
assign P0_M_mc_fence_done_epoch=mem_c_fence_done_epoch[81+:9];
assign mem_c_req_valid[10+:1]=P1_M_mc_req_valid;
assign P1_M_mc_req_ready=mem_c_req_ready[10+:1];
assign mem_c_req_address[640+:64]=P1_M_mc_req_address;
assign mem_c_req_tag[320+:32]=P1_M_mc_req_tag;
assign mem_c_req_channel[10+:1]=P1_M_mc_req_channel;
assign mem_c_req_record_beats[50+:5]=P1_M_mc_req_record_beats;
assign P1_M_mc_rsp_valid=mem_c_rsp_valid[10+:1];
assign mem_c_rsp_ready[10+:1]=P1_M_mc_rsp_ready;
assign P1_M_mc_rsp_tag=mem_c_rsp_tag[320+:32];
assign P1_M_mc_rsp_data=mem_c_rsp_data[5120+:512];
assign mem_c_close_valid[10+:1]=P1_M_mc_close_valid;
assign P1_M_mc_close_ready=mem_c_close_ready[10+:1];
assign mem_c_close_tag_base[320+:32]=P1_M_mc_close_tag_base;
assign mem_c_cancel_valid[10+:1]='0;
assign mem_c_cancel_tag[320+:32]='0;
assign mem_c_cancel_ack_ready[10+:1]='1;
assign mem_c_fence_valid[10+:1]=P1_M_mc_fence_req_valid;
assign P1_M_mc_fence_req_ready=mem_c_fence_ready[10+:1];
assign mem_c_fence_cookie[320+:32]=P1_M_mc_fence_req_cookie;
assign mem_c_fence_epoch[90+:9]=P1_M_mc_fence_req_epoch;
assign P1_M_mc_fence_done_valid=mem_c_fence_done_valid[10+:1];
assign mem_c_fence_done_ready[10+:1]=P1_M_mc_fence_done_ready;
assign P1_M_mc_fence_done_cookie=mem_c_fence_done_cookie[320+:32];
assign P1_M_mc_fence_done_epoch=mem_c_fence_done_epoch[90+:9];
assign mem_c_req_valid[11+:1]=P2_M_mc_req_valid;
assign P2_M_mc_req_ready=mem_c_req_ready[11+:1];
assign mem_c_req_address[704+:64]=P2_M_mc_req_address;
assign mem_c_req_tag[352+:32]=P2_M_mc_req_tag;
assign mem_c_req_channel[11+:1]=P2_M_mc_req_channel;
assign mem_c_req_record_beats[55+:5]=P2_M_mc_req_record_beats;
assign P2_M_mc_rsp_valid=mem_c_rsp_valid[11+:1];
assign mem_c_rsp_ready[11+:1]=P2_M_mc_rsp_ready;
assign P2_M_mc_rsp_tag=mem_c_rsp_tag[352+:32];
assign P2_M_mc_rsp_data=mem_c_rsp_data[5632+:512];
assign mem_c_close_valid[11+:1]=P2_M_mc_close_valid;
assign P2_M_mc_close_ready=mem_c_close_ready[11+:1];
assign mem_c_close_tag_base[352+:32]=P2_M_mc_close_tag_base;
assign mem_c_cancel_valid[11+:1]='0;
assign mem_c_cancel_tag[352+:32]='0;
assign mem_c_cancel_ack_ready[11+:1]='1;
assign mem_c_fence_valid[11+:1]=P2_M_mc_fence_req_valid;
assign P2_M_mc_fence_req_ready=mem_c_fence_ready[11+:1];
assign mem_c_fence_cookie[352+:32]=P2_M_mc_fence_req_cookie;
assign mem_c_fence_epoch[99+:9]=P2_M_mc_fence_req_epoch;
assign P2_M_mc_fence_done_valid=mem_c_fence_done_valid[11+:1];
assign mem_c_fence_done_ready[11+:1]=P2_M_mc_fence_done_ready;
assign P2_M_mc_fence_done_cookie=mem_c_fence_done_cookie[352+:32];
assign P2_M_mc_fence_done_epoch=mem_c_fence_done_epoch[99+:9];
mother_control_native64_transport128 #(.SERVICE_STALL_LIMIT(SERVICE_STALL_LIMIT)) mother(.clk_i(clk),.rst_ni(!reset),.release_valid_i(mc_release_valid_i),.release_sequence_i(mc_release_sequence_i),.release_epoch_i(mc_release_epoch_i),.deploy_valid_i(mc_deploy_valid_i),.deploy_generation_i(mc_deploy_generation_i),.release_ready_o(mc_release_ready_o),.poison_o(mc_poison_o),.image_valid_o(mc_image_valid_o),.cfg_req_valid_i(mc_cfg_req_valid_i),.cfg_req_op_i(mc_cfg_req_op_i),.cfg_req_generation_i(mc_cfg_req_generation_i),.cfg_req_address_i(mc_cfg_req_address_i),.cfg_req_data_i(mc_cfg_req_data_i),.cfg_req_total_bytes_i(mc_cfg_req_total_bytes_i),.cfg_req_image_id_i(mc_cfg_req_image_id_i),.cfg_req_topology_id_i(mc_cfg_req_topology_id_i),.cfg_req_abi_id_i(mc_cfg_req_abi_id_i),.cfg_req_capacity_id_i(mc_cfg_req_capacity_id_i),.cfg_req_proof_i(mc_cfg_req_proof_i),.cfg_rsp_ready_i(mc_cfg_rsp_ready_i),.cfg_req_ready_o(mc_cfg_req_ready_o),.cfg_rsp_valid_o(mc_cfg_rsp_valid_o),.cfg_rsp_status_o(mc_cfg_rsp_status_o),.cfg_rsp_data_o(mc_cfg_rsp_data_o),.cfg_rsp_generation_o(mc_cfg_rsp_generation_o),.life_o(mc_life_o),.seq_o(mc_seq_o),.trace_pc_o(mc_trace_pc_o),.trace_retire_o(mc_trace_retire_o),.trace_opcode_o(mc_trace_opcode_o),.trace_pm_owner_o(mc_trace_pm_owner_o),.trace_ireg_valid_o(mc_trace_ireg_valid_o),.start_valid_i(mc_start_valid_i),.start_credit_i(mc_start_credit_i),.start_job_i(mc_start_job_i),.start_epoch_i(mc_start_epoch_i),.start_sequence_i(mc_start_sequence_i),.start_generation_i(mc_start_generation_i),.local_image_ids_i(mc_local_image_ids_i),.local_enabled_i(mc_local_enabled_i),.start_ready_o(mc_start_ready_o),.tx_valid(mc_tx_valid),.tx_ready(mc_tx_ready),.tx_data(mc_tx_data),.tx_target(mc_tx_target),.tx_sop(mc_tx_sop),.tx_eop(mc_tx_eop),.tx_credit(mc_tx_credit),.rx_valid(mc_rx_valid),.rx_ready(mc_rx_ready),.rx_data(mc_rx_data),.rx_source(mc_rx_source),.rx_sop(mc_rx_sop),.rx_eop(mc_rx_eop),.transport_drained_i(all_drained),.frame_fault_count(mc_frame_fault_count),.result_valid_o(mc_result_valid_o),.result_ready_i(mc_result_ready_i),.result_job_o(mc_result_job_o),.result_epoch_o(mc_result_epoch_o),.result_sequence_o(mc_result_sequence_o),.result_status_o(mc_result_status_o),.result_error_pc_o(mc_result_error_pc_o),.result_source_o(mc_result_source_o),.result_child_error_pc_o(mc_result_child_error_pc_o),.result_failed_task_sequence_o(mc_result_failed_task_sequence_o),.result_confirmed_read_bytes_o(mc_result_confirmed_read_bytes_o),.result_confirmed_write_bytes_o(mc_result_confirmed_write_bytes_o),.result_counter_overflow_o(mc_result_counter_overflow_o),.result_saturated_o(mc_result_saturated_o),.trace_live_tokens_o(mc_trace_live_tokens_o),.trace_block_active_o(mc_trace_block_active_o),.trace_terminal_full_o(mc_trace_terminal_full_o),.trace_READY_full_o(mc_trace_READY_full_o),.trace_aborting_o(mc_trace_aborting_o),.recover_valid_i(mc_recover_valid_i),.recover_ready_o(mc_recover_ready_o),.protocol_fault_count_o(mc_protocol_fault_count_o));
mc_lc_packet128_switch #(.ENDPOINTS(9)) control_switch(.clk(clk),.reset(reset),.tx_valid(mc_tx_valid),.tx_sop(mc_tx_sop),.tx_ready(mc_tx_ready),.tx_target(mc_tx_target),.tx_header_target(mc_tx_data[31:24]),.lc_rx_valid(switch_lc_rx_valid),.lc_rx_ready(switch_lc_rx_ready),.lc_rx_target(switch_lc_rx_target),.lc_rx_header_target(switch_lc_rx_header_target),.lc_tx_valid(switch_lc_tx_valid),.lc_tx_ready(switch_lc_tx_ready),.lc_tx_data(switch_lc_tx_data),.lc_tx_sop(switch_lc_tx_sop),.lc_tx_eop(switch_lc_tx_eop),.rx_valid(mc_rx_valid),.rx_ready(mc_rx_ready),.rx_data(mc_rx_data),.rx_source(mc_rx_source),.rx_sop(mc_rx_sop),.rx_eop(mc_rx_eop),.transport_idle(switch_idle));
native_shared_memory_plane memory(.clk(clk),.reset(reset),.c_req_valid(mem_c_req_valid),.c_req_ready(mem_c_req_ready),.c_req_address(mem_c_req_address),.c_req_tag(mem_c_req_tag),.c_req_channel(mem_c_req_channel),.c_req_record_beats(mem_c_req_record_beats),.c_rsp_valid(mem_c_rsp_valid),.c_rsp_ready(mem_c_rsp_ready),.c_rsp_tag(mem_c_rsp_tag),.c_rsp_data(mem_c_rsp_data),.c_close_valid(mem_c_close_valid),.c_close_ready(mem_c_close_ready),.c_close_tag_base(mem_c_close_tag_base),.c_cancel_valid(mem_c_cancel_valid),.c_cancel_ready(mem_c_cancel_ready),.c_cancel_tag(mem_c_cancel_tag),.c_cancel_ack_valid(mem_c_cancel_ack_valid),.c_cancel_ack_ready(mem_c_cancel_ack_ready),.c_cancel_ack_tag(mem_c_cancel_ack_tag),.c_cancel_ack_rejected(mem_c_cancel_ack_rejected),.c_fence_valid(mem_c_fence_valid),.c_fence_ready(mem_c_fence_ready),.c_fence_cookie(mem_c_fence_cookie),.c_fence_epoch(mem_c_fence_epoch),.c_fence_done_valid(mem_c_fence_done_valid),.c_fence_done_ready(mem_c_fence_done_ready),.c_fence_done_cookie(mem_c_fence_done_cookie),.c_fence_done_epoch(mem_c_fence_done_epoch),.d_req_valid(memory_d_req_valid),.d_req_ready(memory_d_req_ready),.d_req_address(memory_d_req_address),.d_req_tag(memory_d_req_tag),.d_rsp_valid(memory_d_rsp_valid),.d_rsp_ready(memory_d_rsp_ready),.d_rsp_tag(memory_d_rsp_tag),.d_rsp_data(memory_d_rsp_data),.d_fence_valid(memory_d_fence_valid),.d_fence_ready(memory_d_fence_ready),.d_fence_generation(memory_d_fence_generation),.d_fence_done_valid(memory_d_fence_done_valid),.d_fence_done_ready(memory_d_fence_done_ready),.d_fence_done_generation(memory_d_fence_done_generation),.fault_valid(memory_fault_valid),.fault_ready(memory_fault_ready),.fault_kind(memory_fault_kind),.fault_client(memory_fault_client),.fault_local_tag(memory_fault_local_tag),.fault_global_tag(memory_fault_global_tag),.debug_beats(memory_debug_beats),.debug_descriptors(memory_debug_descriptors),.debug_generation(memory_debug_generation),.service_req_valid(mem_service_req_valid),.service_req_ready(mem_service_req_ready),.service_req_address(mem_service_req_address),.service_req_tag(mem_service_req_tag),.service_rsp_valid(mem_service_rsp_valid),.service_rsp_ready(mem_service_rsp_ready),.service_rsp_tag(mem_service_rsp_tag),.service_rsp_data(mem_service_rsp_data),.service_rsp_error(mem_service_rsp_error),.service_idle(mem_service_idle),.service_protocol_fault(mem_service_protocol_fault),.write_req_valid(mem_write_req_valid),.write_req_ready(mem_write_req_ready),.write_req_address(mem_write_req_address),.write_req_tag(mem_write_req_tag),.write_req_data(mem_write_req_data),.write_done_valid(mem_write_done_valid),.write_done_ready(mem_write_done_ready),.write_done_tag(mem_write_done_tag),.write_done_error(mem_write_done_error),.write_idle(mem_write_idle),.write_protocol_fault(mem_write_protocol_fault),.transport_idle(mem_transport_idle),.d_req_write(memory_d_req_write),.d_req_data(memory_d_req_data));
if(1)begin:P0
 native_p_owner_control #(.TARGET(8'd0),.TOPOLOGY(TOPOLOGY),.IMAGE_ID(LC_IMAGE_ID)) control(.clk(clk),.reset(reset),.lc_session_valid(lc_session_valid[0+:1]),.lc_session_ready(lc_session_ready[0+:1]),.lc_session_generation(lc_session_generation[0+:32]),.lc_session_topology(lc_session_topology[0+:32]),.lc_transport_drained(all_drained),.lc_cfg_valid(lc_cfg_valid[0+:1]),.lc_cfg_ready(lc_cfg_ready[0+:1]),.lc_cfg_op(lc_cfg_op[0+:2]),.lc_cfg_generation(lc_cfg_generation[0+:32]),.lc_cfg_abi(lc_cfg_abi[0+:32]),.lc_cfg_capacity(lc_cfg_capacity[0+:32]),.lc_cfg_crc(lc_cfg_crc[0+:32]),.lc_cfg_bytes(lc_cfg_bytes[0+:16]),.lc_cfg_address(lc_cfg_address[0+:14]),.lc_cfg_data(lc_cfg_data[0+:128]),.lc_cfg_rsp_valid(lc_cfg_rsp_valid[0+:1]),.lc_cfg_rsp_ready(lc_cfg_rsp_ready[0+:1]),.lc_cfg_status(lc_cfg_status[0+:8]),.lc_cfg_actual_crc(lc_cfg_actual_crc[0+:32]),.lc_certified(lc_certified[0+:1]),.lc_prepared(lc_prepared[0+:1]),.lc_rx_valid(switch_lc_rx_valid[0]),.lc_rx_ready(switch_lc_rx_ready[0]),.lc_rx_data(mc_tx_data),.lc_rx_sop(mc_tx_sop),.lc_rx_eop(mc_tx_eop),.lc_rx_target(switch_lc_rx_target[0+:8]),.lc_tx_valid(switch_lc_tx_valid[0]),.lc_tx_ready(switch_lc_tx_ready[0]),.lc_tx_data(switch_lc_tx_data[0+:128]),.lc_tx_sop(switch_lc_tx_sop[0]),.lc_tx_eop(switch_lc_tx_eop[0]),.lc_tx_source(observe_P0_source),.lc_mc_req_valid(mem_c_req_valid[0+:1]),.lc_mc_req_ready(mem_c_req_ready[0+:1]),.lc_mc_req_address(mem_c_req_address[0+:64]),.lc_mc_req_tag(mem_c_req_tag[0+:32]),.lc_mc_req_channel(mem_c_req_channel[0+:1]),.lc_mc_req_record_beats(mem_c_req_record_beats[0+:5]),.lc_mc_close_valid(mem_c_close_valid[0+:1]),.lc_mc_close_ready(mem_c_close_ready[0+:1]),.lc_mc_close_tag_base(mem_c_close_tag_base[0+:32]),.lc_mc_rsp_valid(mem_c_rsp_valid[0+:1]),.lc_mc_rsp_ready(mem_c_rsp_ready[0+:1]),.lc_mc_rsp_tag(mem_c_rsp_tag[0+:32]),.lc_mc_rsp_data(mem_c_rsp_data[0+:512]),.lc_idle(owner_idle[0]),.lc_protocol_fault_cycles(lc_protocol_fault_cycles[0+:32]),.lc_pm_trace_valid(lc_pm_trace_valid[0+:1]),.lc_pm_trace_address(lc_pm_trace_address[0+:14]),.lc_retired_instructions(lc_retired_instructions[0+:32]),.service_resource_m_lc_valid(P0_service_resource_m_lc_valid),.service_resource_m_lc_ready(P0_service_resource_m_lc_ready),.service_resource_m_lc_sop(P0_service_resource_m_lc_sop),.service_resource_m_lc_eop(P0_service_resource_m_lc_eop),.service_resource_m_lc_data(P0_service_resource_m_lc_data),.service_resource_m_lr_valid(P0_service_resource_m_lr_valid),.service_resource_m_lr_ready(P0_service_resource_m_lr_ready),.service_resource_m_lr_sop(P0_service_resource_m_lr_sop),.service_resource_m_lr_eop(P0_service_resource_m_lr_eop),.service_resource_m_lr_data(P0_service_resource_m_lr_data),.service_resource_m_a_valid(P0_service_resource_m_a_valid),.service_resource_m_a_ready(P0_service_resource_m_a_ready),.service_resource_m_a_data(P0_service_resource_m_a_data),.service_resource_m_a_session(P0_service_resource_m_a_session),.service_resource_m_a_beat(P0_service_resource_m_a_beat),.service_s_req_valid(P0_service_s_req_valid),.service_s_req_write(P0_service_s_req_write),.service_s_req_ready(P0_service_s_req_ready),.service_s_req_address(P0_service_s_req_address),.service_s_req_data(P0_service_s_req_data),.service_s_rsp_valid(P0_service_s_rsp_valid),.service_s_rsp_ready(P0_service_s_rsp_ready),.service_s_rsp_data(P0_service_s_rsp_data),.service_s_rsp_error(P0_service_s_rsp_error),.service_rd_valid(P0_service_rd_valid),.service_rd_ready(P0_service_rd_ready),.service_rd_address(P0_service_rd_address),.service_rd_tag(P0_service_rd_tag),.service_rd_rsp_valid(P0_service_rd_rsp_valid),.service_rd_rsp_ready(P0_service_rd_rsp_ready),.service_rd_rsp_tag(P0_service_rd_rsp_tag),.service_rd_rsp_data(P0_service_rd_rsp_data),.service_rd_rsp_error(P0_service_rd_rsp_error),.service_source_failed(P0_service_source_failed),.service_quarantine(P0_service_quarantine),.service_protocol_faults(P0_service_protocol_faults),.service_resource_g_in_valid(P0_service_resource_g_in_valid),.service_resource_g_in_ready(P0_service_resource_g_in_ready),.service_resource_g_in_gate(P0_service_resource_g_in_gate),.service_resource_g_in_up(P0_service_resource_g_in_up),.service_resource_g_in_gated(P0_service_resource_g_in_gated),.service_resource_g_in_mask(P0_service_resource_g_in_mask),.service_resource_g_out_valid(P0_service_resource_g_out_valid),.service_resource_g_out_ready(P0_service_resource_g_out_ready),.service_resource_g_out_data(P0_service_resource_g_out_data),.service_resource_g_out_mask(P0_service_resource_g_out_mask),.service_resource_g_out_error(P0_service_resource_g_out_error),.service_wr_valid(P0_service_wr_valid),.service_wr_ready(P0_service_wr_ready),.service_wr_address(P0_service_wr_address),.service_wr_tag(P0_service_wr_tag),.service_wr_data(P0_service_wr_data),.service_wr_done_valid(P0_service_wr_done_valid),.service_wr_done_ready(P0_service_wr_done_ready),.service_wr_done_tag(P0_service_wr_done_tag),.service_wr_done_error(P0_service_wr_done_error));
end
if(1)begin:P1
 native_p_owner_control #(.TARGET(8'd1),.TOPOLOGY(TOPOLOGY),.IMAGE_ID(LC_IMAGE_ID)) control(.clk(clk),.reset(reset),.lc_session_valid(lc_session_valid[1+:1]),.lc_session_ready(lc_session_ready[1+:1]),.lc_session_generation(lc_session_generation[32+:32]),.lc_session_topology(lc_session_topology[32+:32]),.lc_transport_drained(all_drained),.lc_cfg_valid(lc_cfg_valid[1+:1]),.lc_cfg_ready(lc_cfg_ready[1+:1]),.lc_cfg_op(lc_cfg_op[2+:2]),.lc_cfg_generation(lc_cfg_generation[32+:32]),.lc_cfg_abi(lc_cfg_abi[32+:32]),.lc_cfg_capacity(lc_cfg_capacity[32+:32]),.lc_cfg_crc(lc_cfg_crc[32+:32]),.lc_cfg_bytes(lc_cfg_bytes[16+:16]),.lc_cfg_address(lc_cfg_address[14+:14]),.lc_cfg_data(lc_cfg_data[128+:128]),.lc_cfg_rsp_valid(lc_cfg_rsp_valid[1+:1]),.lc_cfg_rsp_ready(lc_cfg_rsp_ready[1+:1]),.lc_cfg_status(lc_cfg_status[8+:8]),.lc_cfg_actual_crc(lc_cfg_actual_crc[32+:32]),.lc_certified(lc_certified[1+:1]),.lc_prepared(lc_prepared[1+:1]),.lc_rx_valid(switch_lc_rx_valid[1]),.lc_rx_ready(switch_lc_rx_ready[1]),.lc_rx_data(mc_tx_data),.lc_rx_sop(mc_tx_sop),.lc_rx_eop(mc_tx_eop),.lc_rx_target(switch_lc_rx_target[8+:8]),.lc_tx_valid(switch_lc_tx_valid[1]),.lc_tx_ready(switch_lc_tx_ready[1]),.lc_tx_data(switch_lc_tx_data[128+:128]),.lc_tx_sop(switch_lc_tx_sop[1]),.lc_tx_eop(switch_lc_tx_eop[1]),.lc_tx_source(observe_P1_source),.lc_mc_req_valid(mem_c_req_valid[1+:1]),.lc_mc_req_ready(mem_c_req_ready[1+:1]),.lc_mc_req_address(mem_c_req_address[64+:64]),.lc_mc_req_tag(mem_c_req_tag[32+:32]),.lc_mc_req_channel(mem_c_req_channel[1+:1]),.lc_mc_req_record_beats(mem_c_req_record_beats[5+:5]),.lc_mc_close_valid(mem_c_close_valid[1+:1]),.lc_mc_close_ready(mem_c_close_ready[1+:1]),.lc_mc_close_tag_base(mem_c_close_tag_base[32+:32]),.lc_mc_rsp_valid(mem_c_rsp_valid[1+:1]),.lc_mc_rsp_ready(mem_c_rsp_ready[1+:1]),.lc_mc_rsp_tag(mem_c_rsp_tag[32+:32]),.lc_mc_rsp_data(mem_c_rsp_data[512+:512]),.lc_idle(owner_idle[1]),.lc_protocol_fault_cycles(lc_protocol_fault_cycles[32+:32]),.lc_pm_trace_valid(lc_pm_trace_valid[1+:1]),.lc_pm_trace_address(lc_pm_trace_address[14+:14]),.lc_retired_instructions(lc_retired_instructions[32+:32]),.service_resource_m_lc_valid(P1_service_resource_m_lc_valid),.service_resource_m_lc_ready(P1_service_resource_m_lc_ready),.service_resource_m_lc_sop(P1_service_resource_m_lc_sop),.service_resource_m_lc_eop(P1_service_resource_m_lc_eop),.service_resource_m_lc_data(P1_service_resource_m_lc_data),.service_resource_m_lr_valid(P1_service_resource_m_lr_valid),.service_resource_m_lr_ready(P1_service_resource_m_lr_ready),.service_resource_m_lr_sop(P1_service_resource_m_lr_sop),.service_resource_m_lr_eop(P1_service_resource_m_lr_eop),.service_resource_m_lr_data(P1_service_resource_m_lr_data),.service_resource_m_a_valid(P1_service_resource_m_a_valid),.service_resource_m_a_ready(P1_service_resource_m_a_ready),.service_resource_m_a_data(P1_service_resource_m_a_data),.service_resource_m_a_session(P1_service_resource_m_a_session),.service_resource_m_a_beat(P1_service_resource_m_a_beat),.service_s_req_valid(P1_service_s_req_valid),.service_s_req_write(P1_service_s_req_write),.service_s_req_ready(P1_service_s_req_ready),.service_s_req_address(P1_service_s_req_address),.service_s_req_data(P1_service_s_req_data),.service_s_rsp_valid(P1_service_s_rsp_valid),.service_s_rsp_ready(P1_service_s_rsp_ready),.service_s_rsp_data(P1_service_s_rsp_data),.service_s_rsp_error(P1_service_s_rsp_error),.service_rd_valid(P1_service_rd_valid),.service_rd_ready(P1_service_rd_ready),.service_rd_address(P1_service_rd_address),.service_rd_tag(P1_service_rd_tag),.service_rd_rsp_valid(P1_service_rd_rsp_valid),.service_rd_rsp_ready(P1_service_rd_rsp_ready),.service_rd_rsp_tag(P1_service_rd_rsp_tag),.service_rd_rsp_data(P1_service_rd_rsp_data),.service_rd_rsp_error(P1_service_rd_rsp_error),.service_source_failed(P1_service_source_failed),.service_quarantine(P1_service_quarantine),.service_protocol_faults(P1_service_protocol_faults),.service_resource_g_in_valid(P1_service_resource_g_in_valid),.service_resource_g_in_ready(P1_service_resource_g_in_ready),.service_resource_g_in_gate(P1_service_resource_g_in_gate),.service_resource_g_in_up(P1_service_resource_g_in_up),.service_resource_g_in_gated(P1_service_resource_g_in_gated),.service_resource_g_in_mask(P1_service_resource_g_in_mask),.service_resource_g_out_valid(P1_service_resource_g_out_valid),.service_resource_g_out_ready(P1_service_resource_g_out_ready),.service_resource_g_out_data(P1_service_resource_g_out_data),.service_resource_g_out_mask(P1_service_resource_g_out_mask),.service_resource_g_out_error(P1_service_resource_g_out_error),.service_wr_valid(P1_service_wr_valid),.service_wr_ready(P1_service_wr_ready),.service_wr_address(P1_service_wr_address),.service_wr_tag(P1_service_wr_tag),.service_wr_data(P1_service_wr_data),.service_wr_done_valid(P1_service_wr_done_valid),.service_wr_done_ready(P1_service_wr_done_ready),.service_wr_done_tag(P1_service_wr_done_tag),.service_wr_done_error(P1_service_wr_done_error));
end
if(1)begin:P2
 native_p_owner_control #(.TARGET(8'd2),.TOPOLOGY(TOPOLOGY),.IMAGE_ID(LC_IMAGE_ID)) control(.clk(clk),.reset(reset),.lc_session_valid(lc_session_valid[2+:1]),.lc_session_ready(lc_session_ready[2+:1]),.lc_session_generation(lc_session_generation[64+:32]),.lc_session_topology(lc_session_topology[64+:32]),.lc_transport_drained(all_drained),.lc_cfg_valid(lc_cfg_valid[2+:1]),.lc_cfg_ready(lc_cfg_ready[2+:1]),.lc_cfg_op(lc_cfg_op[4+:2]),.lc_cfg_generation(lc_cfg_generation[64+:32]),.lc_cfg_abi(lc_cfg_abi[64+:32]),.lc_cfg_capacity(lc_cfg_capacity[64+:32]),.lc_cfg_crc(lc_cfg_crc[64+:32]),.lc_cfg_bytes(lc_cfg_bytes[32+:16]),.lc_cfg_address(lc_cfg_address[28+:14]),.lc_cfg_data(lc_cfg_data[256+:128]),.lc_cfg_rsp_valid(lc_cfg_rsp_valid[2+:1]),.lc_cfg_rsp_ready(lc_cfg_rsp_ready[2+:1]),.lc_cfg_status(lc_cfg_status[16+:8]),.lc_cfg_actual_crc(lc_cfg_actual_crc[64+:32]),.lc_certified(lc_certified[2+:1]),.lc_prepared(lc_prepared[2+:1]),.lc_rx_valid(switch_lc_rx_valid[2]),.lc_rx_ready(switch_lc_rx_ready[2]),.lc_rx_data(mc_tx_data),.lc_rx_sop(mc_tx_sop),.lc_rx_eop(mc_tx_eop),.lc_rx_target(switch_lc_rx_target[16+:8]),.lc_tx_valid(switch_lc_tx_valid[2]),.lc_tx_ready(switch_lc_tx_ready[2]),.lc_tx_data(switch_lc_tx_data[256+:128]),.lc_tx_sop(switch_lc_tx_sop[2]),.lc_tx_eop(switch_lc_tx_eop[2]),.lc_tx_source(observe_P2_source),.lc_mc_req_valid(mem_c_req_valid[2+:1]),.lc_mc_req_ready(mem_c_req_ready[2+:1]),.lc_mc_req_address(mem_c_req_address[128+:64]),.lc_mc_req_tag(mem_c_req_tag[64+:32]),.lc_mc_req_channel(mem_c_req_channel[2+:1]),.lc_mc_req_record_beats(mem_c_req_record_beats[10+:5]),.lc_mc_close_valid(mem_c_close_valid[2+:1]),.lc_mc_close_ready(mem_c_close_ready[2+:1]),.lc_mc_close_tag_base(mem_c_close_tag_base[64+:32]),.lc_mc_rsp_valid(mem_c_rsp_valid[2+:1]),.lc_mc_rsp_ready(mem_c_rsp_ready[2+:1]),.lc_mc_rsp_tag(mem_c_rsp_tag[64+:32]),.lc_mc_rsp_data(mem_c_rsp_data[1024+:512]),.lc_idle(owner_idle[2]),.lc_protocol_fault_cycles(lc_protocol_fault_cycles[64+:32]),.lc_pm_trace_valid(lc_pm_trace_valid[2+:1]),.lc_pm_trace_address(lc_pm_trace_address[28+:14]),.lc_retired_instructions(lc_retired_instructions[64+:32]),.service_resource_m_lc_valid(P2_service_resource_m_lc_valid),.service_resource_m_lc_ready(P2_service_resource_m_lc_ready),.service_resource_m_lc_sop(P2_service_resource_m_lc_sop),.service_resource_m_lc_eop(P2_service_resource_m_lc_eop),.service_resource_m_lc_data(P2_service_resource_m_lc_data),.service_resource_m_lr_valid(P2_service_resource_m_lr_valid),.service_resource_m_lr_ready(P2_service_resource_m_lr_ready),.service_resource_m_lr_sop(P2_service_resource_m_lr_sop),.service_resource_m_lr_eop(P2_service_resource_m_lr_eop),.service_resource_m_lr_data(P2_service_resource_m_lr_data),.service_resource_m_a_valid(P2_service_resource_m_a_valid),.service_resource_m_a_ready(P2_service_resource_m_a_ready),.service_resource_m_a_data(P2_service_resource_m_a_data),.service_resource_m_a_session(P2_service_resource_m_a_session),.service_resource_m_a_beat(P2_service_resource_m_a_beat),.service_s_req_valid(P2_service_s_req_valid),.service_s_req_write(P2_service_s_req_write),.service_s_req_ready(P2_service_s_req_ready),.service_s_req_address(P2_service_s_req_address),.service_s_req_data(P2_service_s_req_data),.service_s_rsp_valid(P2_service_s_rsp_valid),.service_s_rsp_ready(P2_service_s_rsp_ready),.service_s_rsp_data(P2_service_s_rsp_data),.service_s_rsp_error(P2_service_s_rsp_error),.service_rd_valid(P2_service_rd_valid),.service_rd_ready(P2_service_rd_ready),.service_rd_address(P2_service_rd_address),.service_rd_tag(P2_service_rd_tag),.service_rd_rsp_valid(P2_service_rd_rsp_valid),.service_rd_rsp_ready(P2_service_rd_rsp_ready),.service_rd_rsp_tag(P2_service_rd_rsp_tag),.service_rd_rsp_data(P2_service_rd_rsp_data),.service_rd_rsp_error(P2_service_rd_rsp_error),.service_source_failed(P2_service_source_failed),.service_quarantine(P2_service_quarantine),.service_protocol_faults(P2_service_protocol_faults),.service_resource_g_in_valid(P2_service_resource_g_in_valid),.service_resource_g_in_ready(P2_service_resource_g_in_ready),.service_resource_g_in_gate(P2_service_resource_g_in_gate),.service_resource_g_in_up(P2_service_resource_g_in_up),.service_resource_g_in_gated(P2_service_resource_g_in_gated),.service_resource_g_in_mask(P2_service_resource_g_in_mask),.service_resource_g_out_valid(P2_service_resource_g_out_valid),.service_resource_g_out_ready(P2_service_resource_g_out_ready),.service_resource_g_out_data(P2_service_resource_g_out_data),.service_resource_g_out_mask(P2_service_resource_g_out_mask),.service_resource_g_out_error(P2_service_resource_g_out_error),.service_wr_valid(P2_service_wr_valid),.service_wr_ready(P2_service_wr_ready),.service_wr_address(P2_service_wr_address),.service_wr_tag(P2_service_wr_tag),.service_wr_data(P2_service_wr_data),.service_wr_done_valid(P2_service_wr_done_valid),.service_wr_done_ready(P2_service_wr_done_ready),.service_wr_done_tag(P2_service_wr_done_tag),.service_wr_done_error(P2_service_wr_done_error));
end
if(1)begin:C0
 native_e_owner_control #(.TARGET(8'd3),.TOPOLOGY(TOPOLOGY),.IMAGE_ID(LC_IMAGE_ID)) control(.clk(clk),.reset(reset),.lc_session_valid(lc_session_valid[3+:1]),.lc_session_ready(lc_session_ready[3+:1]),.lc_session_generation(lc_session_generation[96+:32]),.lc_session_topology(lc_session_topology[96+:32]),.lc_transport_drained(all_drained),.lc_cfg_valid(lc_cfg_valid[3+:1]),.lc_cfg_ready(lc_cfg_ready[3+:1]),.lc_cfg_op(lc_cfg_op[6+:2]),.lc_cfg_generation(lc_cfg_generation[96+:32]),.lc_cfg_abi(lc_cfg_abi[96+:32]),.lc_cfg_capacity(lc_cfg_capacity[96+:32]),.lc_cfg_crc(lc_cfg_crc[96+:32]),.lc_cfg_bytes(lc_cfg_bytes[48+:16]),.lc_cfg_address(lc_cfg_address[42+:14]),.lc_cfg_data(lc_cfg_data[384+:128]),.lc_cfg_rsp_valid(lc_cfg_rsp_valid[3+:1]),.lc_cfg_rsp_ready(lc_cfg_rsp_ready[3+:1]),.lc_cfg_status(lc_cfg_status[24+:8]),.lc_cfg_actual_crc(lc_cfg_actual_crc[96+:32]),.lc_certified(lc_certified[3+:1]),.lc_prepared(lc_prepared[3+:1]),.lc_rx_valid(switch_lc_rx_valid[3]),.lc_rx_ready(switch_lc_rx_ready[3]),.lc_rx_data(mc_tx_data),.lc_rx_sop(mc_tx_sop),.lc_rx_eop(mc_tx_eop),.lc_rx_target(switch_lc_rx_target[24+:8]),.lc_tx_valid(switch_lc_tx_valid[3]),.lc_tx_ready(switch_lc_tx_ready[3]),.lc_tx_data(switch_lc_tx_data[384+:128]),.lc_tx_sop(switch_lc_tx_sop[3]),.lc_tx_eop(switch_lc_tx_eop[3]),.lc_tx_source(observe_C0_source),.lc_mc_req_valid(mem_c_req_valid[3+:1]),.lc_mc_req_ready(mem_c_req_ready[3+:1]),.lc_mc_req_address(mem_c_req_address[192+:64]),.lc_mc_req_tag(mem_c_req_tag[96+:32]),.lc_mc_req_channel(mem_c_req_channel[3+:1]),.lc_mc_req_record_beats(mem_c_req_record_beats[15+:5]),.lc_mc_close_valid(mem_c_close_valid[3+:1]),.lc_mc_close_ready(mem_c_close_ready[3+:1]),.lc_mc_close_tag_base(mem_c_close_tag_base[96+:32]),.lc_mc_rsp_valid(mem_c_rsp_valid[3+:1]),.lc_mc_rsp_ready(mem_c_rsp_ready[3+:1]),.lc_mc_rsp_tag(mem_c_rsp_tag[96+:32]),.lc_mc_rsp_data(mem_c_rsp_data[1536+:512]),.lc_idle(owner_idle[3]),.lc_protocol_fault_cycles(lc_protocol_fault_cycles[96+:32]),.lc_pm_trace_valid(lc_pm_trace_valid[3+:1]),.lc_pm_trace_address(lc_pm_trace_address[42+:14]),.lc_retired_instructions(lc_retired_instructions[96+:32]),.service_rd_valid(C0_service_rd_valid),.service_rd_ready(C0_service_rd_ready),.service_rd_address(C0_service_rd_address),.service_rd_tag(C0_service_rd_tag),.service_rd_rsp_valid(C0_service_rd_rsp_valid),.service_rd_rsp_ready(C0_service_rd_rsp_ready),.service_rd_rsp_tag(C0_service_rd_rsp_tag),.service_rd_rsp_data(C0_service_rd_rsp_data),.service_rd_rsp_error(C0_service_rd_rsp_error),.service_s_req_valid(C0_service_s_req_valid),.service_s_req_write(C0_service_s_req_write),.service_s_req_ready(C0_service_s_req_ready),.service_s_req_address(C0_service_s_req_address),.service_s_req_data(C0_service_s_req_data),.service_s_rsp_valid(C0_service_s_rsp_valid),.service_s_rsp_ready(C0_service_s_rsp_ready),.service_s_rsp_data(C0_service_s_rsp_data),.service_s_rsp_error(C0_service_s_rsp_error),.service_resource_e_in_valid(C0_service_resource_e_in_valid),.service_resource_e_in_ready(C0_service_resource_e_in_ready),.service_resource_e_in_data(C0_service_resource_e_in_data),.service_resource_e_in_op(C0_service_resource_e_in_op),.service_resource_e_in_mask(C0_service_resource_e_in_mask),.service_resource_e_in_shift(C0_service_resource_e_in_shift),.service_resource_e_in_minus(C0_service_resource_e_in_minus),.service_resource_e_out_valid(C0_service_resource_e_out_valid),.service_resource_e_out_ready(C0_service_resource_e_out_ready),.service_resource_e_out_data(C0_service_resource_e_out_data),.service_resource_e_out_clipped(C0_service_resource_e_out_clipped),.service_resource_e_out_error(C0_service_resource_e_out_error),.service_wr_valid(C0_service_wr_valid),.service_wr_ready(C0_service_wr_ready),.service_wr_address(C0_service_wr_address),.service_wr_tag(C0_service_wr_tag),.service_wr_data(C0_service_wr_data),.service_wr_done_valid(C0_service_wr_done_valid),.service_wr_done_ready(C0_service_wr_done_ready),.service_wr_done_tag(C0_service_wr_done_tag),.service_wr_done_error(C0_service_wr_done_error));
end
if(1)begin:U0
 native_n_owner_control #(.TARGET(8'd4),.TOPOLOGY(TOPOLOGY),.IMAGE_ID(LC_IMAGE_ID)) control(.clk(clk),.reset(reset),.lc_session_valid(lc_session_valid[4+:1]),.lc_session_ready(lc_session_ready[4+:1]),.lc_session_generation(lc_session_generation[128+:32]),.lc_session_topology(lc_session_topology[128+:32]),.lc_transport_drained(all_drained),.lc_cfg_valid(lc_cfg_valid[4+:1]),.lc_cfg_ready(lc_cfg_ready[4+:1]),.lc_cfg_op(lc_cfg_op[8+:2]),.lc_cfg_generation(lc_cfg_generation[128+:32]),.lc_cfg_abi(lc_cfg_abi[128+:32]),.lc_cfg_capacity(lc_cfg_capacity[128+:32]),.lc_cfg_crc(lc_cfg_crc[128+:32]),.lc_cfg_bytes(lc_cfg_bytes[64+:16]),.lc_cfg_address(lc_cfg_address[56+:14]),.lc_cfg_data(lc_cfg_data[512+:128]),.lc_cfg_rsp_valid(lc_cfg_rsp_valid[4+:1]),.lc_cfg_rsp_ready(lc_cfg_rsp_ready[4+:1]),.lc_cfg_status(lc_cfg_status[32+:8]),.lc_cfg_actual_crc(lc_cfg_actual_crc[128+:32]),.lc_certified(lc_certified[4+:1]),.lc_prepared(lc_prepared[4+:1]),.lc_rx_valid(switch_lc_rx_valid[4]),.lc_rx_ready(switch_lc_rx_ready[4]),.lc_rx_data(mc_tx_data),.lc_rx_sop(mc_tx_sop),.lc_rx_eop(mc_tx_eop),.lc_rx_target(switch_lc_rx_target[32+:8]),.lc_tx_valid(switch_lc_tx_valid[4]),.lc_tx_ready(switch_lc_tx_ready[4]),.lc_tx_data(switch_lc_tx_data[512+:128]),.lc_tx_sop(switch_lc_tx_sop[4]),.lc_tx_eop(switch_lc_tx_eop[4]),.lc_tx_source(observe_U0_source),.lc_mc_req_valid(mem_c_req_valid[4+:1]),.lc_mc_req_ready(mem_c_req_ready[4+:1]),.lc_mc_req_address(mem_c_req_address[256+:64]),.lc_mc_req_tag(mem_c_req_tag[128+:32]),.lc_mc_req_channel(mem_c_req_channel[4+:1]),.lc_mc_req_record_beats(mem_c_req_record_beats[20+:5]),.lc_mc_close_valid(mem_c_close_valid[4+:1]),.lc_mc_close_ready(mem_c_close_ready[4+:1]),.lc_mc_close_tag_base(mem_c_close_tag_base[128+:32]),.lc_mc_rsp_valid(mem_c_rsp_valid[4+:1]),.lc_mc_rsp_ready(mem_c_rsp_ready[4+:1]),.lc_mc_rsp_tag(mem_c_rsp_tag[128+:32]),.lc_mc_rsp_data(mem_c_rsp_data[2048+:512]),.lc_idle(owner_idle[4]),.lc_protocol_fault_cycles(lc_protocol_fault_cycles[128+:32]),.lc_pm_trace_valid(lc_pm_trace_valid[4+:1]),.lc_pm_trace_address(lc_pm_trace_address[56+:14]),.lc_retired_instructions(lc_retired_instructions[128+:32]),.service_s_req_valid(U0_service_s_req_valid),.service_s_req_write(U0_service_s_req_write),.service_s_req_ready(U0_service_s_req_ready),.service_s_req_address(U0_service_s_req_address),.service_s_req_data(U0_service_s_req_data),.service_s_rsp_valid(U0_service_s_rsp_valid),.service_s_rsp_ready(U0_service_s_rsp_ready),.service_s_rsp_data(U0_service_s_rsp_data),.service_s_rsp_error(U0_service_s_rsp_error),.service_resource_n_cmd_valid(U0_service_resource_n_cmd_valid),.service_resource_n_cmd_ready(U0_service_resource_n_cmd_ready),.service_resource_n_cmd_tag(U0_service_resource_n_cmd_tag),.service_resource_n_cmd_mode(U0_service_resource_n_cmd_mode),.service_resource_n_cmd_base(U0_service_resource_n_cmd_base),.service_resource_n_cmd_count(U0_service_resource_n_cmd_count),.service_resource_n_cmd_committed(U0_service_resource_n_cmd_committed),.service_resource_n_abort_valid(U0_service_resource_n_abort_valid),.service_resource_n_abort_ready(U0_service_resource_n_abort_ready),.service_resource_n_abort_tag(U0_service_resource_n_abort_tag),.service_resource_n_rsp_valid(U0_service_resource_n_rsp_valid),.service_resource_n_rsp_ready(U0_service_resource_n_rsp_ready),.service_resource_n_rsp_tag(U0_service_resource_n_rsp_tag),.service_resource_n_rsp_error(U0_service_resource_n_rsp_error),.service_resource_n_rsp_aborted(U0_service_resource_n_rsp_aborted),.service_resource_n_rsp_writes(U0_service_resource_n_rsp_writes),.service_resource_n_s_req_valid(U0_service_resource_n_s_req_valid),.service_resource_n_s_req_write(U0_service_resource_n_s_req_write),.service_resource_n_s_req_ready(U0_service_resource_n_s_req_ready),.service_resource_n_s_req_address(U0_service_resource_n_s_req_address),.service_resource_n_s_req_data(U0_service_resource_n_s_req_data),.service_resource_n_s_rsp_valid(U0_service_resource_n_s_rsp_valid),.service_resource_n_s_rsp_ready(U0_service_resource_n_s_rsp_ready),.service_resource_n_s_rsp_data(U0_service_resource_n_s_rsp_data),.service_resource_n_s_rsp_error(U0_service_resource_n_s_rsp_error),.service_rd_valid(U0_service_rd_valid),.service_rd_ready(U0_service_rd_ready),.service_rd_address(U0_service_rd_address),.service_rd_tag(U0_service_rd_tag),.service_rd_rsp_valid(U0_service_rd_rsp_valid),.service_rd_rsp_ready(U0_service_rd_rsp_ready),.service_rd_rsp_tag(U0_service_rd_rsp_tag),.service_rd_rsp_data(U0_service_rd_rsp_data),.service_rd_rsp_error(U0_service_rd_rsp_error),.service_wr_valid(U0_service_wr_valid),.service_wr_ready(U0_service_wr_ready),.service_wr_address(U0_service_wr_address),.service_wr_tag(U0_service_wr_tag),.service_wr_data(U0_service_wr_data),.service_wr_done_valid(U0_service_wr_done_valid),.service_wr_done_ready(U0_service_wr_done_ready),.service_wr_done_tag(U0_service_wr_done_tag),.service_wr_done_error(U0_service_wr_done_error));
end
if(1)begin:J0
 native_e_owner_control #(.TARGET(8'd5),.TOPOLOGY(TOPOLOGY),.IMAGE_ID(LC_IMAGE_ID)) control(.clk(clk),.reset(reset),.lc_session_valid(lc_session_valid[5+:1]),.lc_session_ready(lc_session_ready[5+:1]),.lc_session_generation(lc_session_generation[160+:32]),.lc_session_topology(lc_session_topology[160+:32]),.lc_transport_drained(all_drained),.lc_cfg_valid(lc_cfg_valid[5+:1]),.lc_cfg_ready(lc_cfg_ready[5+:1]),.lc_cfg_op(lc_cfg_op[10+:2]),.lc_cfg_generation(lc_cfg_generation[160+:32]),.lc_cfg_abi(lc_cfg_abi[160+:32]),.lc_cfg_capacity(lc_cfg_capacity[160+:32]),.lc_cfg_crc(lc_cfg_crc[160+:32]),.lc_cfg_bytes(lc_cfg_bytes[80+:16]),.lc_cfg_address(lc_cfg_address[70+:14]),.lc_cfg_data(lc_cfg_data[640+:128]),.lc_cfg_rsp_valid(lc_cfg_rsp_valid[5+:1]),.lc_cfg_rsp_ready(lc_cfg_rsp_ready[5+:1]),.lc_cfg_status(lc_cfg_status[40+:8]),.lc_cfg_actual_crc(lc_cfg_actual_crc[160+:32]),.lc_certified(lc_certified[5+:1]),.lc_prepared(lc_prepared[5+:1]),.lc_rx_valid(switch_lc_rx_valid[5]),.lc_rx_ready(switch_lc_rx_ready[5]),.lc_rx_data(mc_tx_data),.lc_rx_sop(mc_tx_sop),.lc_rx_eop(mc_tx_eop),.lc_rx_target(switch_lc_rx_target[40+:8]),.lc_tx_valid(switch_lc_tx_valid[5]),.lc_tx_ready(switch_lc_tx_ready[5]),.lc_tx_data(switch_lc_tx_data[640+:128]),.lc_tx_sop(switch_lc_tx_sop[5]),.lc_tx_eop(switch_lc_tx_eop[5]),.lc_tx_source(observe_J0_source),.lc_mc_req_valid(mem_c_req_valid[5+:1]),.lc_mc_req_ready(mem_c_req_ready[5+:1]),.lc_mc_req_address(mem_c_req_address[320+:64]),.lc_mc_req_tag(mem_c_req_tag[160+:32]),.lc_mc_req_channel(mem_c_req_channel[5+:1]),.lc_mc_req_record_beats(mem_c_req_record_beats[25+:5]),.lc_mc_close_valid(mem_c_close_valid[5+:1]),.lc_mc_close_ready(mem_c_close_ready[5+:1]),.lc_mc_close_tag_base(mem_c_close_tag_base[160+:32]),.lc_mc_rsp_valid(mem_c_rsp_valid[5+:1]),.lc_mc_rsp_ready(mem_c_rsp_ready[5+:1]),.lc_mc_rsp_tag(mem_c_rsp_tag[160+:32]),.lc_mc_rsp_data(mem_c_rsp_data[2560+:512]),.lc_idle(owner_idle[5]),.lc_protocol_fault_cycles(lc_protocol_fault_cycles[160+:32]),.lc_pm_trace_valid(lc_pm_trace_valid[5+:1]),.lc_pm_trace_address(lc_pm_trace_address[70+:14]),.lc_retired_instructions(lc_retired_instructions[160+:32]),.service_rd_valid(J0_service_rd_valid),.service_rd_ready(J0_service_rd_ready),.service_rd_address(J0_service_rd_address),.service_rd_tag(J0_service_rd_tag),.service_rd_rsp_valid(J0_service_rd_rsp_valid),.service_rd_rsp_ready(J0_service_rd_rsp_ready),.service_rd_rsp_tag(J0_service_rd_rsp_tag),.service_rd_rsp_data(J0_service_rd_rsp_data),.service_rd_rsp_error(J0_service_rd_rsp_error),.service_s_req_valid(J0_service_s_req_valid),.service_s_req_write(J0_service_s_req_write),.service_s_req_ready(J0_service_s_req_ready),.service_s_req_address(J0_service_s_req_address),.service_s_req_data(J0_service_s_req_data),.service_s_rsp_valid(J0_service_s_rsp_valid),.service_s_rsp_ready(J0_service_s_rsp_ready),.service_s_rsp_data(J0_service_s_rsp_data),.service_s_rsp_error(J0_service_s_rsp_error),.service_resource_e_in_valid(J0_service_resource_e_in_valid),.service_resource_e_in_ready(J0_service_resource_e_in_ready),.service_resource_e_in_data(J0_service_resource_e_in_data),.service_resource_e_in_op(J0_service_resource_e_in_op),.service_resource_e_in_mask(J0_service_resource_e_in_mask),.service_resource_e_in_shift(J0_service_resource_e_in_shift),.service_resource_e_in_minus(J0_service_resource_e_in_minus),.service_resource_e_out_valid(J0_service_resource_e_out_valid),.service_resource_e_out_ready(J0_service_resource_e_out_ready),.service_resource_e_out_data(J0_service_resource_e_out_data),.service_resource_e_out_clipped(J0_service_resource_e_out_clipped),.service_resource_e_out_error(J0_service_resource_e_out_error),.service_wr_valid(J0_service_wr_valid),.service_wr_ready(J0_service_wr_ready),.service_wr_address(J0_service_wr_address),.service_wr_tag(J0_service_wr_tag),.service_wr_data(J0_service_wr_data),.service_wr_done_valid(J0_service_wr_done_valid),.service_wr_done_ready(J0_service_wr_done_ready),.service_wr_done_tag(J0_service_wr_done_tag),.service_wr_done_error(J0_service_wr_done_error));
end
if(1)begin:F0
 native_e_owner_control #(.TARGET(8'd6),.TOPOLOGY(TOPOLOGY),.IMAGE_ID(LC_IMAGE_ID)) control(.clk(clk),.reset(reset),.lc_session_valid(lc_session_valid[6+:1]),.lc_session_ready(lc_session_ready[6+:1]),.lc_session_generation(lc_session_generation[192+:32]),.lc_session_topology(lc_session_topology[192+:32]),.lc_transport_drained(all_drained),.lc_cfg_valid(lc_cfg_valid[6+:1]),.lc_cfg_ready(lc_cfg_ready[6+:1]),.lc_cfg_op(lc_cfg_op[12+:2]),.lc_cfg_generation(lc_cfg_generation[192+:32]),.lc_cfg_abi(lc_cfg_abi[192+:32]),.lc_cfg_capacity(lc_cfg_capacity[192+:32]),.lc_cfg_crc(lc_cfg_crc[192+:32]),.lc_cfg_bytes(lc_cfg_bytes[96+:16]),.lc_cfg_address(lc_cfg_address[84+:14]),.lc_cfg_data(lc_cfg_data[768+:128]),.lc_cfg_rsp_valid(lc_cfg_rsp_valid[6+:1]),.lc_cfg_rsp_ready(lc_cfg_rsp_ready[6+:1]),.lc_cfg_status(lc_cfg_status[48+:8]),.lc_cfg_actual_crc(lc_cfg_actual_crc[192+:32]),.lc_certified(lc_certified[6+:1]),.lc_prepared(lc_prepared[6+:1]),.lc_rx_valid(switch_lc_rx_valid[6]),.lc_rx_ready(switch_lc_rx_ready[6]),.lc_rx_data(mc_tx_data),.lc_rx_sop(mc_tx_sop),.lc_rx_eop(mc_tx_eop),.lc_rx_target(switch_lc_rx_target[48+:8]),.lc_tx_valid(switch_lc_tx_valid[6]),.lc_tx_ready(switch_lc_tx_ready[6]),.lc_tx_data(switch_lc_tx_data[768+:128]),.lc_tx_sop(switch_lc_tx_sop[6]),.lc_tx_eop(switch_lc_tx_eop[6]),.lc_tx_source(observe_F0_source),.lc_mc_req_valid(mem_c_req_valid[6+:1]),.lc_mc_req_ready(mem_c_req_ready[6+:1]),.lc_mc_req_address(mem_c_req_address[384+:64]),.lc_mc_req_tag(mem_c_req_tag[192+:32]),.lc_mc_req_channel(mem_c_req_channel[6+:1]),.lc_mc_req_record_beats(mem_c_req_record_beats[30+:5]),.lc_mc_close_valid(mem_c_close_valid[6+:1]),.lc_mc_close_ready(mem_c_close_ready[6+:1]),.lc_mc_close_tag_base(mem_c_close_tag_base[192+:32]),.lc_mc_rsp_valid(mem_c_rsp_valid[6+:1]),.lc_mc_rsp_ready(mem_c_rsp_ready[6+:1]),.lc_mc_rsp_tag(mem_c_rsp_tag[192+:32]),.lc_mc_rsp_data(mem_c_rsp_data[3072+:512]),.lc_idle(owner_idle[6]),.lc_protocol_fault_cycles(lc_protocol_fault_cycles[192+:32]),.lc_pm_trace_valid(lc_pm_trace_valid[6+:1]),.lc_pm_trace_address(lc_pm_trace_address[84+:14]),.lc_retired_instructions(lc_retired_instructions[192+:32]),.service_rd_valid(F0_service_rd_valid),.service_rd_ready(F0_service_rd_ready),.service_rd_address(F0_service_rd_address),.service_rd_tag(F0_service_rd_tag),.service_rd_rsp_valid(F0_service_rd_rsp_valid),.service_rd_rsp_ready(F0_service_rd_rsp_ready),.service_rd_rsp_tag(F0_service_rd_rsp_tag),.service_rd_rsp_data(F0_service_rd_rsp_data),.service_rd_rsp_error(F0_service_rd_rsp_error),.service_s_req_valid(F0_service_s_req_valid),.service_s_req_write(F0_service_s_req_write),.service_s_req_ready(F0_service_s_req_ready),.service_s_req_address(F0_service_s_req_address),.service_s_req_data(F0_service_s_req_data),.service_s_rsp_valid(F0_service_s_rsp_valid),.service_s_rsp_ready(F0_service_s_rsp_ready),.service_s_rsp_data(F0_service_s_rsp_data),.service_s_rsp_error(F0_service_s_rsp_error),.service_resource_e_in_valid(F0_service_resource_e_in_valid),.service_resource_e_in_ready(F0_service_resource_e_in_ready),.service_resource_e_in_data(F0_service_resource_e_in_data),.service_resource_e_in_op(F0_service_resource_e_in_op),.service_resource_e_in_mask(F0_service_resource_e_in_mask),.service_resource_e_in_shift(F0_service_resource_e_in_shift),.service_resource_e_in_minus(F0_service_resource_e_in_minus),.service_resource_e_out_valid(F0_service_resource_e_out_valid),.service_resource_e_out_ready(F0_service_resource_e_out_ready),.service_resource_e_out_data(F0_service_resource_e_out_data),.service_resource_e_out_clipped(F0_service_resource_e_out_clipped),.service_resource_e_out_error(F0_service_resource_e_out_error),.service_wr_valid(F0_service_wr_valid),.service_wr_ready(F0_service_wr_ready),.service_wr_address(F0_service_wr_address),.service_wr_tag(F0_service_wr_tag),.service_wr_data(F0_service_wr_data),.service_wr_done_valid(F0_service_wr_done_valid),.service_wr_done_ready(F0_service_wr_done_ready),.service_wr_done_tag(F0_service_wr_done_tag),.service_wr_done_error(F0_service_wr_done_error));
end
if(1)begin:U1
 native_n_owner_control #(.TARGET(8'd7),.TOPOLOGY(TOPOLOGY),.IMAGE_ID(LC_IMAGE_ID)) control(.clk(clk),.reset(reset),.lc_session_valid(lc_session_valid[7+:1]),.lc_session_ready(lc_session_ready[7+:1]),.lc_session_generation(lc_session_generation[224+:32]),.lc_session_topology(lc_session_topology[224+:32]),.lc_transport_drained(all_drained),.lc_cfg_valid(lc_cfg_valid[7+:1]),.lc_cfg_ready(lc_cfg_ready[7+:1]),.lc_cfg_op(lc_cfg_op[14+:2]),.lc_cfg_generation(lc_cfg_generation[224+:32]),.lc_cfg_abi(lc_cfg_abi[224+:32]),.lc_cfg_capacity(lc_cfg_capacity[224+:32]),.lc_cfg_crc(lc_cfg_crc[224+:32]),.lc_cfg_bytes(lc_cfg_bytes[112+:16]),.lc_cfg_address(lc_cfg_address[98+:14]),.lc_cfg_data(lc_cfg_data[896+:128]),.lc_cfg_rsp_valid(lc_cfg_rsp_valid[7+:1]),.lc_cfg_rsp_ready(lc_cfg_rsp_ready[7+:1]),.lc_cfg_status(lc_cfg_status[56+:8]),.lc_cfg_actual_crc(lc_cfg_actual_crc[224+:32]),.lc_certified(lc_certified[7+:1]),.lc_prepared(lc_prepared[7+:1]),.lc_rx_valid(switch_lc_rx_valid[7]),.lc_rx_ready(switch_lc_rx_ready[7]),.lc_rx_data(mc_tx_data),.lc_rx_sop(mc_tx_sop),.lc_rx_eop(mc_tx_eop),.lc_rx_target(switch_lc_rx_target[56+:8]),.lc_tx_valid(switch_lc_tx_valid[7]),.lc_tx_ready(switch_lc_tx_ready[7]),.lc_tx_data(switch_lc_tx_data[896+:128]),.lc_tx_sop(switch_lc_tx_sop[7]),.lc_tx_eop(switch_lc_tx_eop[7]),.lc_tx_source(observe_U1_source),.lc_mc_req_valid(mem_c_req_valid[7+:1]),.lc_mc_req_ready(mem_c_req_ready[7+:1]),.lc_mc_req_address(mem_c_req_address[448+:64]),.lc_mc_req_tag(mem_c_req_tag[224+:32]),.lc_mc_req_channel(mem_c_req_channel[7+:1]),.lc_mc_req_record_beats(mem_c_req_record_beats[35+:5]),.lc_mc_close_valid(mem_c_close_valid[7+:1]),.lc_mc_close_ready(mem_c_close_ready[7+:1]),.lc_mc_close_tag_base(mem_c_close_tag_base[224+:32]),.lc_mc_rsp_valid(mem_c_rsp_valid[7+:1]),.lc_mc_rsp_ready(mem_c_rsp_ready[7+:1]),.lc_mc_rsp_tag(mem_c_rsp_tag[224+:32]),.lc_mc_rsp_data(mem_c_rsp_data[3584+:512]),.lc_idle(owner_idle[7]),.lc_protocol_fault_cycles(lc_protocol_fault_cycles[224+:32]),.lc_pm_trace_valid(lc_pm_trace_valid[7+:1]),.lc_pm_trace_address(lc_pm_trace_address[98+:14]),.lc_retired_instructions(lc_retired_instructions[224+:32]),.service_s_req_valid(U1_service_s_req_valid),.service_s_req_write(U1_service_s_req_write),.service_s_req_ready(U1_service_s_req_ready),.service_s_req_address(U1_service_s_req_address),.service_s_req_data(U1_service_s_req_data),.service_s_rsp_valid(U1_service_s_rsp_valid),.service_s_rsp_ready(U1_service_s_rsp_ready),.service_s_rsp_data(U1_service_s_rsp_data),.service_s_rsp_error(U1_service_s_rsp_error),.service_resource_n_cmd_valid(U1_service_resource_n_cmd_valid),.service_resource_n_cmd_ready(U1_service_resource_n_cmd_ready),.service_resource_n_cmd_tag(U1_service_resource_n_cmd_tag),.service_resource_n_cmd_mode(U1_service_resource_n_cmd_mode),.service_resource_n_cmd_base(U1_service_resource_n_cmd_base),.service_resource_n_cmd_count(U1_service_resource_n_cmd_count),.service_resource_n_cmd_committed(U1_service_resource_n_cmd_committed),.service_resource_n_abort_valid(U1_service_resource_n_abort_valid),.service_resource_n_abort_ready(U1_service_resource_n_abort_ready),.service_resource_n_abort_tag(U1_service_resource_n_abort_tag),.service_resource_n_rsp_valid(U1_service_resource_n_rsp_valid),.service_resource_n_rsp_ready(U1_service_resource_n_rsp_ready),.service_resource_n_rsp_tag(U1_service_resource_n_rsp_tag),.service_resource_n_rsp_error(U1_service_resource_n_rsp_error),.service_resource_n_rsp_aborted(U1_service_resource_n_rsp_aborted),.service_resource_n_rsp_writes(U1_service_resource_n_rsp_writes),.service_resource_n_s_req_valid(U1_service_resource_n_s_req_valid),.service_resource_n_s_req_write(U1_service_resource_n_s_req_write),.service_resource_n_s_req_ready(U1_service_resource_n_s_req_ready),.service_resource_n_s_req_address(U1_service_resource_n_s_req_address),.service_resource_n_s_req_data(U1_service_resource_n_s_req_data),.service_resource_n_s_rsp_valid(U1_service_resource_n_s_rsp_valid),.service_resource_n_s_rsp_ready(U1_service_resource_n_s_rsp_ready),.service_resource_n_s_rsp_data(U1_service_resource_n_s_rsp_data),.service_resource_n_s_rsp_error(U1_service_resource_n_s_rsp_error),.service_rd_valid(U1_service_rd_valid),.service_rd_ready(U1_service_rd_ready),.service_rd_address(U1_service_rd_address),.service_rd_tag(U1_service_rd_tag),.service_rd_rsp_valid(U1_service_rd_rsp_valid),.service_rd_rsp_ready(U1_service_rd_rsp_ready),.service_rd_rsp_tag(U1_service_rd_rsp_tag),.service_rd_rsp_data(U1_service_rd_rsp_data),.service_rd_rsp_error(U1_service_rd_rsp_error),.service_wr_valid(U1_service_wr_valid),.service_wr_ready(U1_service_wr_ready),.service_wr_address(U1_service_wr_address),.service_wr_tag(U1_service_wr_tag),.service_wr_data(U1_service_wr_data),.service_wr_done_valid(U1_service_wr_done_valid),.service_wr_done_ready(U1_service_wr_done_ready),.service_wr_done_tag(U1_service_wr_done_tag),.service_wr_done_error(U1_service_wr_done_error));
end
if(1)begin:J1
 native_e_owner_control #(.TARGET(8'd8),.TOPOLOGY(TOPOLOGY),.IMAGE_ID(LC_IMAGE_ID)) control(.clk(clk),.reset(reset),.lc_session_valid(lc_session_valid[8+:1]),.lc_session_ready(lc_session_ready[8+:1]),.lc_session_generation(lc_session_generation[256+:32]),.lc_session_topology(lc_session_topology[256+:32]),.lc_transport_drained(all_drained),.lc_cfg_valid(lc_cfg_valid[8+:1]),.lc_cfg_ready(lc_cfg_ready[8+:1]),.lc_cfg_op(lc_cfg_op[16+:2]),.lc_cfg_generation(lc_cfg_generation[256+:32]),.lc_cfg_abi(lc_cfg_abi[256+:32]),.lc_cfg_capacity(lc_cfg_capacity[256+:32]),.lc_cfg_crc(lc_cfg_crc[256+:32]),.lc_cfg_bytes(lc_cfg_bytes[128+:16]),.lc_cfg_address(lc_cfg_address[112+:14]),.lc_cfg_data(lc_cfg_data[1024+:128]),.lc_cfg_rsp_valid(lc_cfg_rsp_valid[8+:1]),.lc_cfg_rsp_ready(lc_cfg_rsp_ready[8+:1]),.lc_cfg_status(lc_cfg_status[64+:8]),.lc_cfg_actual_crc(lc_cfg_actual_crc[256+:32]),.lc_certified(lc_certified[8+:1]),.lc_prepared(lc_prepared[8+:1]),.lc_rx_valid(switch_lc_rx_valid[8]),.lc_rx_ready(switch_lc_rx_ready[8]),.lc_rx_data(mc_tx_data),.lc_rx_sop(mc_tx_sop),.lc_rx_eop(mc_tx_eop),.lc_rx_target(switch_lc_rx_target[64+:8]),.lc_tx_valid(switch_lc_tx_valid[8]),.lc_tx_ready(switch_lc_tx_ready[8]),.lc_tx_data(switch_lc_tx_data[1024+:128]),.lc_tx_sop(switch_lc_tx_sop[8]),.lc_tx_eop(switch_lc_tx_eop[8]),.lc_tx_source(observe_J1_source),.lc_mc_req_valid(mem_c_req_valid[8+:1]),.lc_mc_req_ready(mem_c_req_ready[8+:1]),.lc_mc_req_address(mem_c_req_address[512+:64]),.lc_mc_req_tag(mem_c_req_tag[256+:32]),.lc_mc_req_channel(mem_c_req_channel[8+:1]),.lc_mc_req_record_beats(mem_c_req_record_beats[40+:5]),.lc_mc_close_valid(mem_c_close_valid[8+:1]),.lc_mc_close_ready(mem_c_close_ready[8+:1]),.lc_mc_close_tag_base(mem_c_close_tag_base[256+:32]),.lc_mc_rsp_valid(mem_c_rsp_valid[8+:1]),.lc_mc_rsp_ready(mem_c_rsp_ready[8+:1]),.lc_mc_rsp_tag(mem_c_rsp_tag[256+:32]),.lc_mc_rsp_data(mem_c_rsp_data[4096+:512]),.lc_idle(owner_idle[8]),.lc_protocol_fault_cycles(lc_protocol_fault_cycles[256+:32]),.lc_pm_trace_valid(lc_pm_trace_valid[8+:1]),.lc_pm_trace_address(lc_pm_trace_address[112+:14]),.lc_retired_instructions(lc_retired_instructions[256+:32]),.service_rd_valid(J1_service_rd_valid),.service_rd_ready(J1_service_rd_ready),.service_rd_address(J1_service_rd_address),.service_rd_tag(J1_service_rd_tag),.service_rd_rsp_valid(J1_service_rd_rsp_valid),.service_rd_rsp_ready(J1_service_rd_rsp_ready),.service_rd_rsp_tag(J1_service_rd_rsp_tag),.service_rd_rsp_data(J1_service_rd_rsp_data),.service_rd_rsp_error(J1_service_rd_rsp_error),.service_s_req_valid(J1_service_s_req_valid),.service_s_req_write(J1_service_s_req_write),.service_s_req_ready(J1_service_s_req_ready),.service_s_req_address(J1_service_s_req_address),.service_s_req_data(J1_service_s_req_data),.service_s_rsp_valid(J1_service_s_rsp_valid),.service_s_rsp_ready(J1_service_s_rsp_ready),.service_s_rsp_data(J1_service_s_rsp_data),.service_s_rsp_error(J1_service_s_rsp_error),.service_resource_e_in_valid(J1_service_resource_e_in_valid),.service_resource_e_in_ready(J1_service_resource_e_in_ready),.service_resource_e_in_data(J1_service_resource_e_in_data),.service_resource_e_in_op(J1_service_resource_e_in_op),.service_resource_e_in_mask(J1_service_resource_e_in_mask),.service_resource_e_in_shift(J1_service_resource_e_in_shift),.service_resource_e_in_minus(J1_service_resource_e_in_minus),.service_resource_e_out_valid(J1_service_resource_e_out_valid),.service_resource_e_out_ready(J1_service_resource_e_out_ready),.service_resource_e_out_data(J1_service_resource_e_out_data),.service_resource_e_out_clipped(J1_service_resource_e_out_clipped),.service_resource_e_out_error(J1_service_resource_e_out_error),.service_wr_valid(J1_service_wr_valid),.service_wr_ready(J1_service_wr_ready),.service_wr_address(J1_service_wr_address),.service_wr_tag(J1_service_wr_tag),.service_wr_data(J1_service_wr_data),.service_wr_done_valid(J1_service_wr_done_valid),.service_wr_done_ready(J1_service_wr_done_ready),.service_wr_done_tag(J1_service_wr_done_tag),.service_wr_done_error(J1_service_wr_done_error));
end
endmodule
