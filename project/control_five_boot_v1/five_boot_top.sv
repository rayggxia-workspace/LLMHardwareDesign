`timescale 1ns/1ps
module five_boot_top #(parameter integer KIND=0,parameter bit PM_USE_SRAM=1)(
    input wire clk_i,
    input wire rst_ni,
    input wire cmd_valid_i,
    output wire cmd_ready_o,
    input wire [3:0] cmd_op_i,
    input wire [1:0] cmd_target_i,
    input wire [13:0] cmd_address_i,
    input wire [255:0] cmd_data_i,
    output wire reply_valid_o,
    input wire reply_ready_i,
    output wire [15:0] reply_status_o,
    output wire [511:0] reply_data_o,
    output wire [2:0] poison_o,
    output wire [2:0] image_valid_o,
    output wire reset_ready_o,
    output wire deployment_ready_o,
    output wire run_active_o,
    output wire link_pending_o,
    output wire [31:0] commit_count_o,
    output wire [31:0] ack_count_o
);
     wire deploy_valid_i;
     wire [31:0] deploy_generation_i;
     wire [2:0] release_valid_i;
     wire [95:0] release_sequence_i;
     wire [95:0] release_epoch_i;
     wire [2:0] release_ready_o;
     wire [2:0] cfg_req_valid_i;
     wire [8:0] cfg_req_op_i;
     wire [95:0] cfg_req_generation_i;
     wire [41:0] cfg_req_address_i;
     wire [383:0] cfg_req_data_i;
     wire [47:0] cfg_req_total_bytes_i;
     wire [95:0] cfg_req_image_id_i;
     wire [95:0] cfg_req_topology_id_i;
     wire [95:0] cfg_req_abi_id_i;
     wire [95:0] cfg_req_capacity_id_i;
     wire [2:0] cfg_req_proof_i;
     wire [2:0] cfg_rsp_ready_i;
     wire [2:0] cfg_req_ready_o;
     wire [2:0] cfg_rsp_valid_o;
     wire [47:0] cfg_rsp_status_o;
     wire [383:0] cfg_rsp_data_o;
     wire [95:0] cfg_rsp_generation_o;
     wire [2:0] pm_req_ready_i;
     wire [2:0] pm_rsp_valid_i;
     wire [383:0] pm_rsp_data_i;
     wire [2:0] pm_rsp_error_i;
     wire [2:0] pm_req_valid_o;
     wire [2:0] pm_req_write_o;
     wire [41:0] pm_req_address_o;
     wire [383:0] pm_req_data_o;
     wire [2:0] pm_rsp_ready_o;
     wire [11:0] life_o;
     wire [11:0] seq_o;
     wire start_valid_i;
     wire start_credit_i;
     wire [31:0] start_job_i;
     wire [31:0] start_epoch_i;
     wire [31:0] start_sequence_i;
     wire [31:0] start_generation_i;
     wire [255:0] start_args_i;
     wire start_ready_o;
     wire result_valid_o;
     wire result_ready_i;
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
     wire [1:0] host_req_valid_i;
     wire [1:0] host_req_write_i;
     wire [19:0] host_req_address_i;
     wire [255:0] host_req_data_i;
     wire [1:0] host_req_ready_o;
     wire [1:0] host_rsp_valid_o;
     wire [1:0] host_rsp_ready_i;
     wire [255:0] host_rsp_data_o;
     wire ack_rejected_o;
     wire [1:0] fragment_valid_i;
     wire [1:0] fragment_ready_o;
     wire [19:0] fragment_address_i;
     wire [255:0] fragment_data_i;
     wire [63:0] fragment_tag_i;
     wire [3:0] fragment_slot_i;
     wire [1:0] fragment_last_i;
     wire [1:0] fragment_rsp_valid_o;
     wire [1:0] fragment_rsp_ready_i;
     wire [1:0] fragment_error_o;
     wire [1:0] native_result_valid_o;
     wire [1:0] native_result_ready_i;
     wire [1023:0] native_result_packet_o;
     wire [1:0] native_pending_o;
    five_control_top #(.KIND(KIND)) control(.*);
     wire manager_cmd_valid_i;
     wire manager_cmd_ready_o;
     wire [3:0] manager_cmd_op_i;
     wire [1:0] manager_cmd_target_i;
     wire [13:0] manager_cmd_address_i;
     wire [255:0] manager_cmd_data_i;
     wire manager_reply_valid_o;
     wire manager_reply_ready_i;
     wire [15:0] manager_reply_status_o;
     wire [511:0] manager_reply_data_o;
    control_boot_manager boot(
        .clk_i(clk_i),
        .rst_ni(reset_ready_o),
        .cmd_valid_i(manager_cmd_valid_i),
        .cmd_ready_o(manager_cmd_ready_o),
        .cmd_op_i(manager_cmd_op_i),
        .cmd_target_i(manager_cmd_target_i),
        .cmd_address_i(manager_cmd_address_i),
        .cmd_data_i(manager_cmd_data_i),
        .reply_valid_o(manager_reply_valid_o),
        .reply_ready_i(manager_reply_ready_i),
        .reply_status_o(manager_reply_status_o),
        .reply_data_o(manager_reply_data_o),
        .deploy_valid_i(deploy_valid_i),
        .deploy_generation_i(deploy_generation_i),
        .release_valid_i(release_valid_i),
        .release_sequence_i(release_sequence_i),
        .release_epoch_i(release_epoch_i),
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
        .life_o(life_o),
        .start_valid_i(start_valid_i),
        .start_credit_i(start_credit_i),
        .start_job_i(start_job_i),
        .start_epoch_i(start_epoch_i),
        .start_sequence_i(start_sequence_i),
        .start_generation_i(start_generation_i),
        .start_args_i(start_args_i),
        .start_ready_o(start_ready_o),
        .result_valid_o(result_valid_o),
        .result_ready_i(result_ready_i),
        .result_job_o(result_job_o),
        .result_epoch_o(result_epoch_o),
        .result_sequence_o(result_sequence_o),
        .result_status_o(result_status_o),
        .result_error_pc_o(result_error_pc_o),
        .result_source_o(result_source_o),
        .result_child_error_pc_o(result_child_error_pc_o),
        .result_failed_task_sequence_o(result_failed_task_sequence_o),
        .result_confirmed_read_bytes_o(result_confirmed_read_bytes_o),
        .result_confirmed_write_bytes_o(result_confirmed_write_bytes_o),
        .result_counter_overflow_o(result_counter_overflow_o),
        .result_saturated_o(result_saturated_o),
        .host_req_valid_i(host_req_valid_i),
        .host_req_write_i(host_req_write_i),
        .host_req_address_i(host_req_address_i),
        .host_req_data_i(host_req_data_i),
        .host_req_ready_o(host_req_ready_o),
        .host_rsp_valid_o(host_rsp_valid_o),
        .host_rsp_ready_i(host_rsp_ready_i),
        .host_rsp_data_o(host_rsp_data_o),
        .reset_ready_o(reset_ready_o),
        .deployment_ready_o(deployment_ready_o),
        .run_active_o(run_active_o),
        .link_pending_o(link_pending_o)
    );
    typed_boot_front #(.KIND(KIND)) host_front(
        .clk_i(clk_i),
        .cmd_valid_i(cmd_valid_i),
        .cmd_ready_o(cmd_ready_o),
        .cmd_op_i(cmd_op_i),
        .cmd_target_i(cmd_target_i),
        .cmd_address_i(cmd_address_i),
        .cmd_data_i(cmd_data_i),
        .reply_valid_o(reply_valid_o),
        .reply_ready_i(reply_ready_i),
        .reply_status_o(reply_status_o),
        .reply_data_o(reply_data_o),
        .down_cmd_valid_o(manager_cmd_valid_i),
        .down_cmd_ready_i(manager_cmd_ready_o),
        .down_cmd_op_o(manager_cmd_op_i),
        .down_cmd_target_o(manager_cmd_target_i),
        .down_cmd_address_o(manager_cmd_address_i),
        .down_cmd_data_o(manager_cmd_data_i),
        .down_reply_valid_i(manager_reply_valid_o),
        .down_reply_ready_o(manager_reply_ready_i),
        .down_reply_status_i(manager_reply_status_o),
        .down_reply_data_i(manager_reply_data_o),
        .run_active_i(run_active_o),
        .native_pending_i(native_pending_o),
        .fragment_valid_o(fragment_valid_i),
        .fragment_ready_i(fragment_ready_o),
        .fragment_address_o(fragment_address_i),
        .fragment_data_o(fragment_data_i),
        .fragment_tag_o(fragment_tag_i),
        .fragment_slot_o(fragment_slot_i),
        .fragment_last_o(fragment_last_i),
        .fragment_rsp_valid_i(fragment_rsp_valid_o),
        .fragment_rsp_ready_o(fragment_rsp_ready_i),
        .fragment_error_i(fragment_error_o),
        .native_result_valid_i(native_result_valid_o),
        .native_result_ready_o(native_result_ready_i),
        .native_result_packet_i(native_result_packet_o),
        .rst_ni(reset_ready_o),
        .result_valid_i(result_valid_o)
    );
    for(genvar k=0;k<3;k=k+1)begin: programs
        control_pm #(.USE_SRAM(PM_USE_SRAM)) pm(.clk_i,.rst_ni(reset_ready_o),
            .req_valid_i(pm_req_valid_o[k]),.req_write_i(pm_req_write_o[k]),
            .req_address_i(pm_req_address_o[k*14+:14]),.req_data_i(pm_req_data_o[k*128+:128]),
            .req_ready_o(pm_req_ready_i[k]),.rsp_valid_o(pm_rsp_valid_i[k]),.rsp_ready_i(pm_rsp_ready_o[k]),
            .rsp_data_o(pm_rsp_data_i[k*128+:128]),.rsp_error_o(pm_rsp_error_i[k]));
    end
endmodule
