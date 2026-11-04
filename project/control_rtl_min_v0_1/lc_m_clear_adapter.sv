// Strict adapter for registered M_CLEAR_ALL_VALID only; no data/object service.
`timescale 1ns/1ps
module lc_m_clear_adapter (
input wire clk_i,
input wire rst_ni,
input wire provider_released_i,
output wire poison_o,
output wire m_cmd_valid_o,
input wire m_cmd_ready_i,
output wire [3:0] m_cmd_op_o,
output wire [5:0] m_cmd_index_o,
output wire [63:0] m_cmd_data_o,
input wire m_rsp_valid_i,
output wire m_rsp_ready_o,
input wire [127:0] m_rsp_data_i,
input wire m_rsp_error_i,
input wire m_rsp_saturated_i,
  output wire svc_req_ready_o,
  output wire svc_rsp_valid_o,
  output wire [1:0] svc_rsp_kind_o,
  output wire [2:0] svc_rsp_token_o,
  output wire [31:0] svc_rsp_sequence_o,
  output wire [31:0] svc_rsp_job_o,
  output wire [31:0] svc_rsp_epoch_o,
  output wire [31:0] svc_rsp_task_sequence_o,
  output wire [15:0] svc_rsp_status_o,
  output wire [31:0] svc_rsp_read_bytes_o,
  output wire [31:0] svc_rsp_write_bytes_o,
  output wire svc_rsp_saturated_o,
  input wire svc_req_valid_i,
  input wire [1:0] svc_req_kind_i,
  input wire [2:0] svc_req_resource_i,
  input wire [2:0] svc_req_token_i,
  input wire [31:0] svc_req_sequence_i,
  input wire [31:0] svc_req_job_i,
  input wire [31:0] svc_req_epoch_i,
  input wire [31:0] svc_req_task_sequence_i,
  input wire [1023:0] svc_req_descriptor_i,
  input wire [63:0] svc_req_object_base_i,
  input wire [31:0] svc_req_object_length_i,
  input wire [31:0] svc_req_object_version_i,
  input wire svc_rsp_ready_i
);
  localparam [2:0] IDLE=0, REQUEST=1, WAIT_RSP=2, RESPONSE=3;
  reg [2:0] state;
  reg poisoned;
  reg [2:0] token;
  reg [31:0] service_sequence, job, epoch, task_sequence;
  reg [15:0] status;
  reg saturation;
  wire descriptor_ok = svc_req_descriptor_i[0+:16]==1 && svc_req_descriptor_i[16+:8]==0 &&
       svc_req_descriptor_i[24+:8]==0 && svc_req_descriptor_i[32+:8]==6 &&
       svc_req_descriptor_i[40+:24]==0 && svc_req_descriptor_i[64+:32]==32'hffffffff &&
       svc_req_descriptor_i[96+:64]==0 && svc_req_descriptor_i[160+:48]==48'hffffffffffff &&
       svc_req_descriptor_i[208+:240]==0 && svc_req_descriptor_i[448+:32]==32'h00010001 &&
       svc_req_descriptor_i[480+:32]==0 && svc_req_descriptor_i[512+:512]==0 &&
       svc_req_object_base_i==0 && svc_req_object_length_i==0 && svc_req_object_version_i==0;
  wire request_fire=svc_req_valid_i && svc_req_ready_o;
  wire command_fire=m_cmd_valid_o && m_cmd_ready_i;
  wire native_done=m_rsp_valid_i && m_rsp_ready_o;
  assign poison_o=poisoned;
  assign svc_req_ready_o=rst_ni && provider_released_i && !poisoned && state==IDLE && !m_rsp_valid_i;
  assign m_cmd_valid_o=rst_ni && state==REQUEST;
  assign m_cmd_op_o=6;
  assign m_cmd_index_o=0;
  assign m_cmd_data_o=0;
  // Native M is untagged and registered: only one accepted command may own it.
  assign m_rsp_ready_o=rst_ni && state==WAIT_RSP && !poisoned;
  assign svc_rsp_valid_o=rst_ni && state==RESPONSE && !poisoned;
  assign svc_rsp_kind_o=0;
  assign svc_rsp_token_o=token;
  assign svc_rsp_sequence_o=service_sequence;
  assign svc_rsp_job_o=job;
  assign svc_rsp_epoch_o=epoch;
  assign svc_rsp_task_sequence_o=task_sequence;
  assign svc_rsp_status_o=status;
  assign svc_rsp_read_bytes_o=0;
  assign svc_rsp_write_bytes_o=0;
  assign svc_rsp_saturated_o=saturation;
  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      state<=IDLE; poisoned<=0; token<=0; service_sequence<=0; job<=0; epoch<=0; task_sequence<=0;
      status<=0; saturation<=0;
    end else begin
      if (request_fire) begin
        token<=svc_req_token_i; service_sequence<=svc_req_sequence_i; job<=svc_req_job_i;
        epoch<=svc_req_epoch_i; task_sequence<=svc_req_task_sequence_i; saturation<=0;
        if (svc_req_kind_i!=0 || svc_req_resource_i!=0) begin status<=4; state<=RESPONSE; end
        else if (!descriptor_ok) begin status<=5; state<=RESPONSE; end
        else begin status<=0; state<=REQUEST; end
      end
      if (command_fire) state<=WAIT_RSP;
      if (native_done) begin
        status<=m_rsp_error_i || m_rsp_data_i!=0 ? 9 : 0;
        saturation<=m_rsp_saturated_i; state<=RESPONSE;
      end
      if (svc_rsp_valid_o && svc_rsp_ready_i) state<=IDLE;
      // Revocation or a response outside its owning window cannot be retagged.
      // Preserve a command already held; only coordinated reset clears poison.
      if ((!provider_released_i && state!=IDLE) ||
          (m_rsp_valid_i && state!=WAIT_RSP)) poisoned<=1;
    end
  end
endmodule
