`timescale 1ns/1ps
// Bounded exclusive M/feeder service: one S8 row, K=8, two S64 outputs.
// All addresses are private-S 16-byte words. The M and S share this reset domain.
module lc_m_dot_store_adapter (
  input wire clk, rst_n,
  input wire svc_valid, output wire svc_ready,
  input wire [1:0] svc_kind,
  input wire [2:0] svc_resource, svc_token,
  input wire [31:0] svc_sequence, svc_job, svc_epoch, svc_task_sequence,
  input wire [1023:0] svc_desc,
  output wire rsp_valid, input wire rsp_ready,
  output reg [2:0] rsp_token,
  output reg [31:0] rsp_sequence, rsp_job, rsp_epoch, rsp_task_sequence,
  output reg [15:0] rsp_status,
  output reg [31:0] rsp_read_bytes, rsp_write_bytes,

  output wire load_valid, input wire load_ready,
  output reg [9:0] load_a_word, load_b_word,
  input wire load_done, load_error, output wire load_take,
  output wire m_cmd_valid, input wire m_cmd_ready,
  output wire [3:0] m_cmd_op,
  output wire [63:0] m_cmd_data,
  input wire m_rsp_valid, m_rsp_error, m_rsp_saturated,
  input wire [127:0] m_rsp_data, output wire m_rsp_ready,

  output wire s_write_valid, input wire s_write_ready,
  output reg [9:0] s_write_word,
  output reg [127:0] s_write_data,
  input wire s_ack_valid, input wire [127:0] s_ack_data, output wire s_ack_ready
);
  `include "m_dot_store_desc.svh"
  typedef enum logic [3:0] {
    IDLE, LOAD, LOAD_WAIT, START, START_WAIT, READ_RAW, READ_WAIT,
    WRITE_S, WRITE_WAIT, REPLY
  } state_t;
  state_t state;
  assign svc_ready=rst_n && state==IDLE;
  assign rsp_valid=rst_n && state==REPLY;
  assign load_valid=rst_n && state==LOAD;
  assign load_take=rst_n && state==LOAD_WAIT;
  assign m_cmd_valid=rst_n && (state==START || state==READ_RAW);
  assign m_cmd_op=state==START ? 4'd10 : 4'd3;
  // Native START: S8/S8, clear previous row, K=8, N=2, one tile, one row.
  assign m_cmd_data=state==START ? 64'h9284 : 64'd0;
  assign m_rsp_ready=rst_n && (state==START_WAIT || state==READ_WAIT);
  assign s_write_valid=rst_n && state==WRITE_S;
  assign s_ack_ready=rst_n && state==WRITE_WAIT;

  always @(posedge clk) begin
    if(!rst_n) begin
      state<=IDLE;
      rsp_token<=0; rsp_sequence<=0; rsp_job<=0; rsp_epoch<=0; rsp_task_sequence<=0;
      rsp_status<=0; rsp_read_bytes<=0; rsp_write_bytes<=0;
      load_a_word<=0; load_b_word<=0; s_write_word<=0; s_write_data<=0;
    end else case(state)
      IDLE: if(svc_valid && svc_ready) begin
        rsp_token<=svc_token; rsp_sequence<=svc_sequence; rsp_job<=svc_job;
        rsp_epoch<=svc_epoch; rsp_task_sequence<=svc_task_sequence;
        rsp_status<=0; rsp_read_bytes<=0; rsp_write_bytes<=0;
        if(svc_kind!=0 || svc_resource!=0 || !m_dot_store_desc_ok(svc_desc)) begin
          rsp_status<=16'd5;
          state<=REPLY;
        end else begin
          load_a_word<=svc_desc[512+:10]; load_b_word<=svc_desc[522+:10];
          s_write_word<=svc_desc[532+:10];
          state<=LOAD;
        end
      end
      LOAD: if(load_ready) state<=LOAD_WAIT;
      LOAD_WAIT: if(load_done) begin
        if(load_error) begin rsp_status<=16'd9; state<=REPLY; end
        else begin rsp_read_bytes<=32'd128; state<=START; end
      end
      START: if(m_cmd_ready) state<=START_WAIT;
      START_WAIT: if(m_rsp_valid) begin
        if(m_rsp_error || m_rsp_saturated || m_rsp_data!=0) begin
          rsp_status<=16'd9; state<=REPLY;
        end else state<=READ_RAW;
      end
      READ_RAW: if(m_cmd_ready) state<=READ_WAIT;
      READ_WAIT: if(m_rsp_valid) begin
        if(m_rsp_error || m_rsp_saturated) begin rsp_status<=16'd9; state<=REPLY; end
        else begin s_write_data<=m_rsp_data; state<=WRITE_S; end
      end
      WRITE_S: if(s_write_ready) state<=WRITE_WAIT;
      WRITE_WAIT: if(s_ack_valid) begin
        if(s_ack_data==s_write_data) rsp_write_bytes<=32'd16;
        else rsp_status<=16'd9;
        state<=REPLY;
      end
      REPLY: if(rsp_ready) state<=IDLE;
      default: state<=IDLE;
    endcase
  end
endmodule
