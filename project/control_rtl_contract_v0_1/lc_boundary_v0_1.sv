// Generated from contract.json. Declarations only; no controller logic.
interface lc_boundary_v0_1;
  logic clk_i;
  logic rst_ni;
  logic release_valid_i;
  logic [31:0] release_sequence_i;
  logic [31:0] release_epoch_i;
  logic deploy_valid_i;
  logic [31:0] deploy_generation_i;
  logic release_ready_o;
  logic poison_o;
  logic image_valid_o;
  logic cfg_req_valid_i;
  logic [2:0] cfg_req_op_i;
  logic [31:0] cfg_req_generation_i;
  logic [13:0] cfg_req_address_i;
  logic [127:0] cfg_req_data_i;
  logic [15:0] cfg_req_total_bytes_i;
  logic [31:0] cfg_req_image_id_i;
  logic [31:0] cfg_req_topology_id_i;
  logic [31:0] cfg_req_abi_id_i;
  logic [31:0] cfg_req_capacity_id_i;
  logic cfg_req_proof_i;
  logic cfg_rsp_ready_i;
  logic cfg_req_ready_o;
  logic cfg_rsp_valid_o;
  logic [15:0] cfg_rsp_status_o;
  logic [127:0] cfg_rsp_data_o;
  logic [31:0] cfg_rsp_generation_o;
  logic pm_req_ready_i;
  logic pm_rsp_valid_i;
  logic [127:0] pm_rsp_data_i;
  logic pm_rsp_error_i;
  logic pm_req_valid_o;
  logic pm_req_write_o;
  logic [13:0] pm_req_address_o;
  logic [127:0] pm_req_data_o;
  logic pm_rsp_ready_o;
  logic task_valid_i;
  logic [511:0] task_packet_i;
  logic task_credit_i;
  logic task_ready_o;
  logic svc_req_ready_i;
  logic svc_rsp_valid_i;
  logic [1:0] svc_rsp_kind_i;
  logic [2:0] svc_rsp_token_i;
  logic [31:0] svc_rsp_sequence_i;
  logic [31:0] svc_rsp_job_i;
  logic [31:0] svc_rsp_epoch_i;
  logic [31:0] svc_rsp_task_sequence_i;
  logic [15:0] svc_rsp_status_i;
  logic [31:0] svc_rsp_read_bytes_i;
  logic [31:0] svc_rsp_write_bytes_i;
  logic svc_rsp_saturated_i;
  logic svc_req_valid_o;
  logic [1:0] svc_req_kind_o;
  logic [2:0] svc_req_resource_o;
  logic [2:0] svc_req_token_o;
  logic [31:0] svc_req_sequence_o;
  logic [31:0] svc_req_job_o;
  logic [31:0] svc_req_epoch_o;
  logic [31:0] svc_req_task_sequence_o;
  logic [1023:0] svc_req_descriptor_o;
  logic [63:0] svc_req_object_base_o;
  logic [31:0] svc_req_object_length_o;
  logic [31:0] svc_req_object_version_o;
  logic svc_rsp_ready_o;
  logic event_ready_i;
  logic event_valid_o;
  logic [511:0] event_packet_o;
  logic close_req_ready_i;
  logic close_rsp_valid_i;
  logic [31:0] close_rsp_sequence_i;
  logic [31:0] close_rsp_job_i;
  logic [31:0] close_rsp_epoch_i;
  logic [31:0] close_rsp_task_sequence_i;
  logic [2:0] close_rsp_token_i;
  logic [15:0] close_rsp_status_i;
  logic close_req_valid_o;
  logic [31:0] close_req_sequence_o;
  logic [31:0] close_req_job_o;
  logic [31:0] close_req_epoch_o;
  logic [31:0] close_req_task_sequence_o;
  logic [2:0] close_req_token_o;
  logic close_rsp_ready_o;
  logic [3:0] life_o;
  logic [3:0] seq_o;
  logic [31:0] trace_pc_o;
  logic trace_retire_o;
  logic [7:0] trace_opcode_o;
  logic [1:0] trace_pm_owner_o;
  logic trace_ireg_valid_o;
  logic trace_cancel_token_retire_o;
  logic trace_cancel_object_drop_o;
  modport controller (
    input clk_i,
    input rst_ni,
    input release_valid_i,
    input release_sequence_i,
    input release_epoch_i,
    input deploy_valid_i,
    input deploy_generation_i,
    output release_ready_o,
    output poison_o,
    output image_valid_o,
    input cfg_req_valid_i,
    input cfg_req_op_i,
    input cfg_req_generation_i,
    input cfg_req_address_i,
    input cfg_req_data_i,
    input cfg_req_total_bytes_i,
    input cfg_req_image_id_i,
    input cfg_req_topology_id_i,
    input cfg_req_abi_id_i,
    input cfg_req_capacity_id_i,
    input cfg_req_proof_i,
    input cfg_rsp_ready_i,
    output cfg_req_ready_o,
    output cfg_rsp_valid_o,
    output cfg_rsp_status_o,
    output cfg_rsp_data_o,
    output cfg_rsp_generation_o,
    input pm_req_ready_i,
    input pm_rsp_valid_i,
    input pm_rsp_data_i,
    input pm_rsp_error_i,
    output pm_req_valid_o,
    output pm_req_write_o,
    output pm_req_address_o,
    output pm_req_data_o,
    output pm_rsp_ready_o,
    input task_valid_i,
    input task_packet_i,
    input task_credit_i,
    output task_ready_o,
    input svc_req_ready_i,
    input svc_rsp_valid_i,
    input svc_rsp_kind_i,
    input svc_rsp_token_i,
    input svc_rsp_sequence_i,
    input svc_rsp_job_i,
    input svc_rsp_epoch_i,
    input svc_rsp_task_sequence_i,
    input svc_rsp_status_i,
    input svc_rsp_read_bytes_i,
    input svc_rsp_write_bytes_i,
    input svc_rsp_saturated_i,
    output svc_req_valid_o,
    output svc_req_kind_o,
    output svc_req_resource_o,
    output svc_req_token_o,
    output svc_req_sequence_o,
    output svc_req_job_o,
    output svc_req_epoch_o,
    output svc_req_task_sequence_o,
    output svc_req_descriptor_o,
    output svc_req_object_base_o,
    output svc_req_object_length_o,
    output svc_req_object_version_o,
    output svc_rsp_ready_o,
    input event_ready_i,
    output event_valid_o,
    output event_packet_o,
    input close_req_ready_i,
    input close_rsp_valid_i,
    input close_rsp_sequence_i,
    input close_rsp_job_i,
    input close_rsp_epoch_i,
    input close_rsp_task_sequence_i,
    input close_rsp_token_i,
    input close_rsp_status_i,
    output close_req_valid_o,
    output close_req_sequence_o,
    output close_req_job_o,
    output close_req_epoch_o,
    output close_req_task_sequence_o,
    output close_req_token_o,
    output close_rsp_ready_o,
    output life_o,
    output seq_o,
    output trace_pc_o,
    output trace_retire_o,
    output trace_opcode_o,
    output trace_pm_owner_o,
    output trace_ireg_valid_o,
    output trace_cancel_token_retire_o,
    output trace_cancel_object_drop_o
  );
  modport peer (
    output clk_i,
    output rst_ni,
    output release_valid_i,
    output release_sequence_i,
    output release_epoch_i,
    output deploy_valid_i,
    output deploy_generation_i,
    input release_ready_o,
    input poison_o,
    input image_valid_o,
    output cfg_req_valid_i,
    output cfg_req_op_i,
    output cfg_req_generation_i,
    output cfg_req_address_i,
    output cfg_req_data_i,
    output cfg_req_total_bytes_i,
    output cfg_req_image_id_i,
    output cfg_req_topology_id_i,
    output cfg_req_abi_id_i,
    output cfg_req_capacity_id_i,
    output cfg_req_proof_i,
    output cfg_rsp_ready_i,
    input cfg_req_ready_o,
    input cfg_rsp_valid_o,
    input cfg_rsp_status_o,
    input cfg_rsp_data_o,
    input cfg_rsp_generation_o,
    output pm_req_ready_i,
    output pm_rsp_valid_i,
    output pm_rsp_data_i,
    output pm_rsp_error_i,
    input pm_req_valid_o,
    input pm_req_write_o,
    input pm_req_address_o,
    input pm_req_data_o,
    input pm_rsp_ready_o,
    output task_valid_i,
    output task_packet_i,
    output task_credit_i,
    input task_ready_o,
    output svc_req_ready_i,
    output svc_rsp_valid_i,
    output svc_rsp_kind_i,
    output svc_rsp_token_i,
    output svc_rsp_sequence_i,
    output svc_rsp_job_i,
    output svc_rsp_epoch_i,
    output svc_rsp_task_sequence_i,
    output svc_rsp_status_i,
    output svc_rsp_read_bytes_i,
    output svc_rsp_write_bytes_i,
    output svc_rsp_saturated_i,
    input svc_req_valid_o,
    input svc_req_kind_o,
    input svc_req_resource_o,
    input svc_req_token_o,
    input svc_req_sequence_o,
    input svc_req_job_o,
    input svc_req_epoch_o,
    input svc_req_task_sequence_o,
    input svc_req_descriptor_o,
    input svc_req_object_base_o,
    input svc_req_object_length_o,
    input svc_req_object_version_o,
    input svc_rsp_ready_o,
    output event_ready_i,
    input event_valid_o,
    input event_packet_o,
    output close_req_ready_i,
    output close_rsp_valid_i,
    output close_rsp_sequence_i,
    output close_rsp_job_i,
    output close_rsp_epoch_i,
    output close_rsp_task_sequence_i,
    output close_rsp_token_i,
    output close_rsp_status_i,
    input close_req_valid_o,
    input close_req_sequence_o,
    input close_req_job_o,
    input close_req_epoch_o,
    input close_req_task_sequence_o,
    input close_req_token_o,
    input close_rsp_ready_o,
    input life_o,
    input seq_o,
    input trace_pc_o,
    input trace_retire_o,
    input trace_opcode_o,
    input trace_pm_owner_o,
    input trace_ireg_valid_o,
    input trace_cancel_token_retire_o,
    input trace_cancel_object_drop_o
  );
endinterface
