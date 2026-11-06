`timescale 1ns/1ps
// Stage a committed two-word T fragment in S, then add its two S peers.
module lc_j_lease_adapter (
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
  output wire t_begin, input wire t_begin_ready,
  output wire t_write, input wire t_write_ready, output wire [9:0] t_index,
  output wire [127:0] t_payload,
  output wire t_commit, input wire t_commit_ready,
  output wire t_revoke, input wire t_revoke_ready,
  input wire t_read, output wire t_take, input wire [9:0] t_read_index,
  input wire [127:0] t_data, input wire t_last, t_error,
  input wire [1:0] t_owner, input wire [31:0] t_generation, input wire [9:0] t_words,
  output wire t_release, input wire t_release_ready,
  output wire e_valid, input wire e_ready, output wire [127:0] e_a,e_b,
  input wire e_rsp_valid, output wire e_rsp_ready,
  input wire [127:0] e_result, input wire e_error,e_saturated
);
  `include "j_lease_desc.svh"
  typedef enum logic [4:0] {
    IDLE, BEGIN_T, SOURCE_REQ, SOURCE_RSP, FILL_T, COMMIT_T, T_WORD,
    SCRATCH_REQ, SCRATCH_RSP, TAKE_T, RELEASE_T, A_REQ, A_RSP, B_REQ, B_RSP,
    SEND_E, WAIT_E, OUTPUT_REQ, OUTPUT_RSP, REVOKE_T, RESPOND, QUARANTINE
  } state_t;
  state_t state;
  reg word_index;
  reg [9:0] input_base, add_base, scratch_base, dst_base;
  reg [5:0] fill_wait;
  reg [127:0] payload, addend;

  assign svc_ready=rst_n && state==IDLE;
  assign rsp_valid=rst_n && state==RESPOND;
  assign t_begin=rst_n && state==BEGIN_T;
  assign t_write=rst_n && state==FILL_T;
  assign t_index={9'b0,word_index};
  assign t_payload=payload;
  assign t_commit=rst_n && state==COMMIT_T;
  assign t_revoke=rst_n && state==REVOKE_T;
  assign t_take=rst_n && state==TAKE_T && t_read;
  assign t_release=rst_n && state==RELEASE_T;
  assign s_valid=rst_n && (state==SOURCE_REQ || state==SCRATCH_REQ || state==A_REQ ||
                           state==B_REQ || state==OUTPUT_REQ);
  assign s_write=state==SCRATCH_REQ || state==OUTPUT_REQ;
  assign s_word=(state==SOURCE_REQ ? input_base :
                 state==B_REQ ? add_base :
                 state==OUTPUT_REQ ? dst_base : scratch_base)+{9'b0,word_index};
  assign s_data=payload;
  assign s_rsp_ready=rst_n && (state==SOURCE_RSP || state==SCRATCH_RSP || state==A_RSP ||
                               state==B_RSP || state==OUTPUT_RSP);
  assign e_valid=rst_n && state==SEND_E;
  assign e_a=payload;
  assign e_b=addend;
  assign e_rsp_ready=rst_n && state==WAIT_E;

  always @(posedge clk) begin
    if (!rst_n) begin
      state<=IDLE; word_index<=0; fill_wait<=0;
      input_base<=0; add_base<=0; scratch_base<=0; dst_base<=0;
      payload<=0; addend<=0;
      rsp_token<=0; rsp_sequence<=0; rsp_job<=0; rsp_epoch<=0; rsp_task_sequence<=0;
      rsp_status<=0; rsp_read_bytes<=0; rsp_write_bytes<=0; rsp_saturated<=0;
    end else case (state)
      IDLE: if (svc_valid) begin
        rsp_token<=svc_token; rsp_sequence<=svc_sequence; rsp_job<=svc_job;
        rsp_epoch<=svc_epoch; rsp_task_sequence<=svc_task_sequence;
        rsp_status<=0; rsp_read_bytes<=0; rsp_write_bytes<=0; rsp_saturated<=0;
        word_index<=0;
        if (svc_resource!=J_LEASE_RESOURCE || !j_lease_desc_ok(svc_desc)) begin
          rsp_status<=5; state<=RESPOND;
        end else if (t_error) begin
          rsp_status<=9; state<=RESPOND;
        end else begin
          input_base<=svc_desc[512+:10]; add_base<=svc_desc[522+:10];
          scratch_base<=svc_desc[532+:10]; dst_base<=svc_desc[544+:10];
          state<=BEGIN_T;
        end
      end
      BEGIN_T: if (t_begin_ready) state<=SOURCE_REQ;
      SOURCE_REQ: if (s_ready) state<=SOURCE_RSP;
      SOURCE_RSP: if (s_rsp_valid) begin
        payload<=s_rsp_data; rsp_read_bytes<=rsp_read_bytes+32'd16;
        fill_wait<=0; state<=FILL_T;
      end
      FILL_T: begin
        if (t_error) state<=REVOKE_T;
        else if (t_write_ready) begin
          if (word_index) state<=COMMIT_T;
          else begin word_index<=1; state<=SOURCE_REQ; end
        end else if (&fill_wait) state<=REVOKE_T;
        else fill_wait<=fill_wait+1'b1;
      end
      COMMIT_T: if (t_commit_ready) begin word_index<=0; state<=T_WORD; end
      REVOKE_T: if (t_revoke_ready) begin rsp_status<=9; state<=RESPOND; end
      T_WORD: if (t_read) begin
        if (t_owner!=0 || t_generation!=rsp_task_sequence || t_words!=2 ||
            t_read_index!={9'b0,word_index} || t_last!=word_index) state<=QUARANTINE;
        else begin payload<=t_data; state<=SCRATCH_REQ; end
      end
      SCRATCH_REQ: if (s_ready) state<=SCRATCH_RSP;
      SCRATCH_RSP: if (s_rsp_valid) begin
        if (s_rsp_data!=payload) state<=QUARANTINE;
        else begin rsp_write_bytes<=rsp_write_bytes+32'd16; state<=TAKE_T; end
      end
      TAKE_T: if (t_read) begin
        if (word_index) state<=RELEASE_T;
        else begin word_index<=1; state<=T_WORD; end
      end
      RELEASE_T: if (t_release_ready) begin word_index<=0; state<=A_REQ; end
      A_REQ: if (s_ready) state<=A_RSP;
      A_RSP: if (s_rsp_valid) begin payload<=s_rsp_data; rsp_read_bytes<=rsp_read_bytes+32'd16; state<=B_REQ; end
      B_REQ: if (s_ready) state<=B_RSP;
      B_RSP: if (s_rsp_valid) begin addend<=s_rsp_data; rsp_read_bytes<=rsp_read_bytes+32'd16; state<=SEND_E; end
      SEND_E: if (e_ready) state<=WAIT_E;
      WAIT_E: if (e_rsp_valid) begin
        rsp_saturated<=rsp_saturated || e_saturated;
        if (e_error) begin rsp_status<=9; state<=RESPOND; end
        else begin payload<=e_result; state<=OUTPUT_REQ; end
      end
      OUTPUT_REQ: if (s_ready) state<=OUTPUT_RSP;
      OUTPUT_RSP: if (s_rsp_valid) begin
        if (s_rsp_data!=payload) begin rsp_status<=9; state<=RESPOND; end
        else begin
          rsp_write_bytes<=rsp_write_bytes+32'd16;
          if (word_index) state<=RESPOND;
          else begin word_index<=1; state<=A_REQ; end
        end
      end
      RESPOND: if (rsp_ready) state<=IDLE;
      // A committed lease must survive a damaged read or unconfirmed store.
      QUARANTINE: begin end
      default: state<=QUARANTINE;
    endcase
  end
endmodule
