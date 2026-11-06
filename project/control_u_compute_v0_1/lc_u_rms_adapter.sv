`timescale 1ns/1ps
// Two-segment RMS normalization over real S rereads, followed by S16 ADD.
module lc_u_rms_adapter (
  input wire clk, rst_n,
  input wire svc_valid, output wire svc_ready,
  input wire [2:0] svc_resource, svc_token,
  input wire [31:0] svc_sequence, svc_job, svc_epoch, svc_task_sequence,
  input wire [1023:0] svc_desc,
  output wire rsp_valid, input wire rsp_ready,
  output reg [2:0] rsp_token,
  output reg [31:0] rsp_sequence, rsp_job, rsp_epoch, rsp_task_sequence,
  output reg [15:0] rsp_status,
  output reg [31:0] rsp_read_bytes, rsp_write_bytes,
  output reg rsp_saturated,
  output wire s_valid, input wire s_ready, output wire s_write,
  output wire [9:0] s_word, output wire [127:0] s_data,
  input wire s_rsp_valid, output wire s_rsp_ready, input wire [127:0] s_rsp_data,
  output wire n_valid, input wire n_ready,
  output reg [3:0] n_op, output wire [3:0] n_count,
  output wire [31:0] n_param, output wire [127:0] n_data, n_aux,
  input wire n_rsp_valid, output wire n_rsp_ready,
  input wire [127:0] n_result, input wire n_error, n_saturated,
  output wire e_valid, input wire e_ready, output wire [127:0] e_a, e_b,
  input wire e_rsp_valid, output wire e_rsp_ready,
  input wire [127:0] e_result, input wire e_error, e_saturated
);
  `include "u_rms_desc.svh"

  localparam [3:0] N_BEGIN=0, N_STATS=1, N_FINALIZE=2, N_REPLAY=5;
  typedef enum logic [3:0] {
    IDLE, SEND_N, WAIT_N, READ_SEGMENT, WAIT_SEGMENT,
    SEND_E, WAIT_E, WRITE_SEGMENT, WAIT_WRITE, RESPOND
  } state_t;
  state_t state;
  reg segment;
  reg [9:0] src0, src1, dst;
  reg [3:0] count0, count1;
  reg [15:0] bias;
  reg [31:0] epsilon;
  reg [127:0] payload, output0, output1;
  wire [3:0] count = segment ? count1 : count0;

  assign svc_ready = rst_n && state==IDLE;
  assign rsp_valid = rst_n && state==RESPOND;
  assign s_valid = rst_n && (state==READ_SEGMENT || state==WRITE_SEGMENT);
  assign s_write = state==WRITE_SEGMENT;
  assign s_word = s_write ? dst+{9'b0,segment} : (segment ? src1 : src0);
  assign s_data = segment ? output1 : output0;
  assign s_rsp_ready = rst_n && (state==WAIT_SEGMENT || state==WAIT_WRITE);
  assign n_valid = rst_n && state==SEND_N;
  assign n_rsp_ready = rst_n && state==WAIT_N;
  assign n_count = (n_op==N_STATS || n_op==N_REPLAY) ? count : 4'b0;
  assign n_param = n_op==N_BEGIN ? 32'd1 : 32'b0;
  assign n_data = n_op==N_BEGIN ? {96'b0,epsilon} : n_op==N_FINALIZE ? 128'b0 : payload;
  assign n_aux = n_op==N_REPLAY ? {8{16'd1024}} : 128'b0;
  assign e_valid = rst_n && state==SEND_E;
  assign e_a = payload;
  for (genvar lane=0; lane<8; lane=lane+1) begin: lane_bias
    assign e_b[16*lane+:16] = 4'(lane)<count ? bias : 16'b0;
  end
  assign e_rsp_ready = rst_n && state==WAIT_E;

  always @(posedge clk) begin
    if (!rst_n) begin
      state<=IDLE;
      rsp_token<=0; rsp_sequence<=0; rsp_job<=0; rsp_epoch<=0; rsp_task_sequence<=0;
      rsp_status<=0; rsp_read_bytes<=0; rsp_write_bytes<=0; rsp_saturated<=0;
      n_op<=N_BEGIN; segment<=0; src0<=0; src1<=0; dst<=0;
      count0<=0; count1<=0; bias<=0; epsilon<=0;
      payload<=0; output0<=0; output1<=0;
    end else case (state)
      IDLE: if (svc_valid && svc_ready) begin
        rsp_token<=svc_token; rsp_sequence<=svc_sequence;
        rsp_job<=svc_job; rsp_epoch<=svc_epoch; rsp_task_sequence<=svc_task_sequence;
        rsp_status<=0; rsp_read_bytes<=0; rsp_write_bytes<=0; rsp_saturated<=0;
        if (svc_resource!=U_RMS_RESOURCE[2:0] || !u_rms_desc_ok(svc_desc)) begin
          rsp_status<=5; state<=RESPOND;
        end else begin
          src0<=svc_desc[512+:10]; src1<=svc_desc[522+:10]; dst<=svc_desc[532+:10];
          count0<=svc_desc[544+:4]; count1<=svc_desc[548+:4];
          bias<=svc_desc[560+:16]; epsilon<=svc_desc[576+:32];
          segment<=0; n_op<=N_BEGIN; state<=SEND_N;
        end
      end
      SEND_N: if (n_ready) state<=WAIT_N;
      WAIT_N: if (n_rsp_valid) begin
        rsp_saturated<=rsp_saturated || n_saturated;
        if (n_error) begin
          rsp_status<=9; state<=RESPOND;
        end else case (n_op)
          N_BEGIN: begin n_op<=N_STATS; state<=READ_SEGMENT; end
          N_STATS: begin
            if (segment) begin n_op<=N_FINALIZE; state<=SEND_N; end
            else begin segment<=1; state<=READ_SEGMENT; end
          end
          N_FINALIZE: begin n_op<=N_REPLAY; segment<=0; state<=READ_SEGMENT; end
          N_REPLAY: begin payload<=n_result; state<=SEND_E; end
          default: begin rsp_status<=9; state<=RESPOND; end
        endcase
      end
      READ_SEGMENT: if (s_ready) state<=WAIT_SEGMENT;
      WAIT_SEGMENT: if (s_rsp_valid) begin
        payload<=s_rsp_data; rsp_read_bytes<=rsp_read_bytes+32'd16; state<=SEND_N;
      end
      SEND_E: if (e_ready) state<=WAIT_E;
      WAIT_E: if (e_rsp_valid) begin
        rsp_saturated<=rsp_saturated || e_saturated;
        if (e_error) begin rsp_status<=9; state<=RESPOND; end
        else if (segment) begin
          // Both segments finished compute before either destination is written.
          output1<=e_result; segment<=0; state<=WRITE_SEGMENT;
        end else begin output0<=e_result; segment<=1; state<=READ_SEGMENT; end
      end
      WRITE_SEGMENT: if (s_ready) state<=WAIT_WRITE;
      WAIT_WRITE: if (s_rsp_valid) begin
        if (s_rsp_data!=s_data) begin rsp_status<=9; state<=RESPOND; end
        else begin
          rsp_write_bytes<=rsp_write_bytes+32'd16;
          if (segment) state<=RESPOND;
          else begin segment<=1; state<=WRITE_SEGMENT; end
        end
      end
      RESPOND: if (rsp_ready) state<=IDLE;
      default: state<=IDLE;
    endcase
  end
endmodule
