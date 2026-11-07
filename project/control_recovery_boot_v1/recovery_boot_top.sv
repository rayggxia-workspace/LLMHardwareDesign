`timescale 1ns/1ps
module recovery_boot_top #(parameter integer KIND=0,parameter bit PM_USE_SRAM=1)(
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
     wire engine_cmd_valid_i;
     wire engine_cmd_ready_o;
     wire [3:0] engine_cmd_op_i;
     wire [1:0] engine_cmd_target_i;
     wire [13:0] engine_cmd_address_i;
     wire [255:0] engine_cmd_data_i;
     wire engine_reply_valid_o;
     wire engine_reply_ready_i;
     wire [15:0] engine_reply_status_o;
     wire [511:0] engine_reply_data_o;
    (* async_reg="true" *) reg [1:0] outer_reset_release;
    always @(posedge clk_i or negedge rst_ni)begin
        if(!rst_ni)outer_reset_release<=0;
        else outer_reset_release<={outer_reset_release[0],1'b1};
    end
    wire outer_rst_ni=outer_reset_release[1];
    wire inner_rst_ni,halt_i,quiescent_o,fault_o,engine_result_valid_o;
    wire [31:0] observed_reads_o,observed_writes_o;
    recovery_engine #(.KIND(KIND),.PM_USE_SRAM(PM_USE_SRAM)) engine(
        .clk_i(clk_i),
        .rst_ni(inner_rst_ni),
        .cmd_valid_i(engine_cmd_valid_i),
        .cmd_ready_o(engine_cmd_ready_o),
        .cmd_op_i(engine_cmd_op_i),
        .cmd_target_i(engine_cmd_target_i),
        .cmd_address_i(engine_cmd_address_i),
        .cmd_data_i(engine_cmd_data_i),
        .reply_valid_o(engine_reply_valid_o),
        .reply_ready_i(engine_reply_ready_i),
        .reply_status_o(engine_reply_status_o),
        .reply_data_o(engine_reply_data_o),
        .poison_o(poison_o),
        .image_valid_o(image_valid_o),
        .reset_ready_o(reset_ready_o),
        .deployment_ready_o(deployment_ready_o),
        .run_active_o(run_active_o),
        .link_pending_o(link_pending_o),
        .commit_count_o(commit_count_o),
        .ack_count_o(ack_count_o),
        .halt_i(halt_i),
        .quiescent_o(quiescent_o),
        .fault_o(fault_o),
        .observed_reads_o(observed_reads_o),
        .observed_writes_o(observed_writes_o),
        .engine_result_valid_o(engine_result_valid_o)
    );
    recovery_supervisor supervisor(
        .clk_i(clk_i),
        .rst_ni(outer_rst_ni),
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
        .poison_o(poison_o),
        .image_valid_o(image_valid_o),
        .reset_ready_o(reset_ready_o),
        .run_active_o(run_active_o),
        .link_pending_o(link_pending_o),
        .commit_count_o(commit_count_o),
        .ack_count_o(ack_count_o),
        .engine_cmd_valid_i(engine_cmd_valid_i),
        .engine_cmd_ready_o(engine_cmd_ready_o),
        .engine_cmd_op_i(engine_cmd_op_i),
        .engine_cmd_target_i(engine_cmd_target_i),
        .engine_cmd_address_i(engine_cmd_address_i),
        .engine_cmd_data_i(engine_cmd_data_i),
        .engine_reply_valid_o(engine_reply_valid_o),
        .engine_reply_ready_i(engine_reply_ready_i),
        .engine_reply_status_o(engine_reply_status_o),
        .engine_reply_data_o(engine_reply_data_o),
        .inner_rst_ni(inner_rst_ni),
        .halt_i(halt_i),
        .quiescent_o(quiescent_o),
        .fault_o(fault_o),
        .observed_reads_o(observed_reads_o),
        .observed_writes_o(observed_writes_o),
        .engine_result_valid_o(engine_result_valid_o)
    );
endmodule
