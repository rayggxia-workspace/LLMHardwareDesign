`timescale 1ns/1ps
// One F service with a fixed G-to-E path and a G-to-S bypass.
module lc_f_store_adapter (
  input wire clk, rst_n,
  input wire svc_valid, output wire svc_ready,
  input wire [7:0] svc_resource,
  input wire [2:0] svc_token,
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
  output wire g_valid, input wire g_ready, output wire [31:0] g_x,
  input wire g_rsp_valid, output wire g_rsp_ready,
  input wire [31:0] g_result, input wire g_error, g_saturated,
  output wire e_valid, input wire e_ready, output wire [127:0] e_a, e_b,
  input wire e_rsp_valid, output wire e_rsp_ready,
  input wire [127:0] e_result, input wire e_error, e_saturated
);
  `include "f_store_desc.svh"

  typedef enum logic [3:0] {
    IDLE, READ_INPUT, INPUT_WAIT, SEND_G, G_WAIT, READ_ADDEND, ADDEND_WAIT,
    SEND_E, E_WAIT, WRITE_OUTPUT, OUTPUT_WAIT, RESPOND
  } state_t;
  state_t state;
  reg use_add;
  reg [9:0] src_word, add_word, dst_word;
  reg [31:0] input_lanes, addend_lanes, result_lanes;

  assign svc_ready = rst_n && state==IDLE;
  assign rsp_valid = rst_n && state==RESPOND;
  assign s_valid = rst_n && (state==READ_INPUT || state==READ_ADDEND || state==WRITE_OUTPUT);
  assign s_write = state==WRITE_OUTPUT;
  assign s_word = s_write ? dst_word : state==READ_ADDEND ? add_word : src_word;
  assign s_data = {96'b0, result_lanes};
  assign s_rsp_ready = rst_n && (state==INPUT_WAIT || state==ADDEND_WAIT || state==OUTPUT_WAIT);
  assign g_valid = rst_n && state==SEND_G;
  assign g_x = input_lanes;
  assign g_rsp_ready = rst_n && state==G_WAIT;
  assign e_valid = rst_n && state==SEND_E;
  assign e_a = {96'b0, result_lanes};
  assign e_b = {96'b0, addend_lanes};
  assign e_rsp_ready = rst_n && state==E_WAIT;

  always @(posedge clk) begin
    if (!rst_n) begin
      state<=IDLE;
      rsp_token<=0; rsp_sequence<=0; rsp_job<=0; rsp_epoch<=0; rsp_task_sequence<=0;
      rsp_status<=0; rsp_read_bytes<=0; rsp_write_bytes<=0; rsp_saturated<=0;
      use_add<=0; src_word<=0; add_word<=0; dst_word<=0;
      input_lanes<=0; addend_lanes<=0; result_lanes<=0;
    end else case (state)
      IDLE: if (svc_valid && svc_ready) begin
        rsp_token<=svc_token; rsp_sequence<=svc_sequence;
        rsp_job<=svc_job; rsp_epoch<=svc_epoch; rsp_task_sequence<=svc_task_sequence;
        rsp_status<=0; rsp_read_bytes<=0; rsp_write_bytes<=0; rsp_saturated<=0;
        if (svc_resource!=F_STORE_RESOURCE || !f_store_desc_ok(svc_desc)) begin
          rsp_status<=5;
          state<=RESPOND;
        end else begin
          use_add<=svc_desc[32+:16]==F_GE_STORE_OP;
          src_word<=svc_desc[512+:10]; add_word<=svc_desc[522+:10]; dst_word<=svc_desc[532+:10];
          state<=READ_INPUT;
        end
      end
      READ_INPUT: if (s_valid && s_ready) state<=INPUT_WAIT;
      INPUT_WAIT: if (s_rsp_valid && s_rsp_ready) begin
        input_lanes<=s_rsp_data[31:0];
        rsp_read_bytes<=16;
        state<=SEND_G;
      end
      SEND_G: if (g_valid && g_ready) state<=G_WAIT;
      G_WAIT: if (g_rsp_valid && g_rsp_ready) begin
        rsp_saturated<=g_saturated;
        result_lanes<=g_result;
        if (g_error) begin rsp_status<=9; state<=RESPOND; end
        else state<=use_add ? READ_ADDEND : WRITE_OUTPUT;
      end
      READ_ADDEND: if (s_valid && s_ready) state<=ADDEND_WAIT;
      ADDEND_WAIT: if (s_rsp_valid && s_rsp_ready) begin
        addend_lanes<=s_rsp_data[31:0];
        rsp_read_bytes<=32;
        state<=SEND_E;
      end
      SEND_E: if (e_valid && e_ready) state<=E_WAIT;
      E_WAIT: if (e_rsp_valid && e_rsp_ready) begin
        rsp_saturated<=rsp_saturated || e_saturated;
        result_lanes<=e_result[31:0];
        if (e_error) begin rsp_status<=9; state<=RESPOND; end
        else state<=WRITE_OUTPUT;
      end
      WRITE_OUTPUT: if (s_valid && s_ready) state<=OUTPUT_WAIT;
      OUTPUT_WAIT: if (s_rsp_valid && s_rsp_ready) begin
        if (s_rsp_data!=s_data) rsp_status<=9;
        else rsp_write_bytes<=16;
        state<=RESPOND;
      end
      RESPOND: if (rsp_ready) state<=IDLE;
      default: state<=IDLE;
    endcase
  end
endmodule
