`timescale 1ns/1ps
// One native R256 row, E narrowing, G SiLU, and one stored consumer receipt.
module lc_c_state_adapter (
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
  output wire r_read, input wire r_read_ready, output wire r_bank,
  input wire r_read_rsp, output wire r_read_take, input wire [127:0] r_data,
  output wire r_load, input wire r_load_ready, output wire [127:0] r_coefficient,
  output wire r_cmd, input wire r_cmd_ready, output wire r_role,
  input wire r_rsp_valid, output wire r_rsp_ready, input wire r_error,
  output wire e_valid, input wire e_ready, output wire [127:0] e_a,
  input wire e_rsp_valid, output wire e_rsp_ready, input wire [127:0] e_result,
  input wire e_error,e_saturated,
  output wire g_valid, input wire g_ready, output wire [31:0] g_x,
  input wire g_rsp_valid, output wire g_rsp_ready, input wire [31:0] g_result,
  input wire g_error,g_saturated,
  output wire s_valid, input wire s_ready, output wire s_write,
  output wire [9:0] s_word, output wire [127:0] s_data,
  input wire s_rsp_valid, output wire s_rsp_ready, input wire [127:0] s_rsp_data,
  output wire consumer_valid, input wire consumer_ready,
  output wire [127:0] consumer_identity,consumer_data,
  input wire receipt_valid, output wire receipt_ready,
  input wire [127:0] receipt_identity,input wire receipt_error,
  output reg active_bank, output reg [31:0] generation,
  output reg candidate_valid,publish, output wire receipt_reject
);
  `include "c_state_desc.svh"
  typedef enum logic [4:0] {
    IDLE, OLD_READ, OLD_WAIT, LOAD_DECAY, START_R, WAIT_R, CANDIDATE_READ, CANDIDATE_WAIT,
    START_E, WAIT_E, START_G, WAIT_G, WRITE_S, WAIT_WRITE, READ_S, WAIT_READ,
    SEND_CONSUMER, WAIT_RECEIPT, RESPOND
  } state_t;
  state_t state;
  localparam [6:0] LAST_RECEIPT_WAIT=7'd95;
  reg [6:0] receipt_wait;
  reg [9:0] dst;
  reg [31:0] decay;
  reg [127:0] payload;

  assign svc_ready=rst_n && state==IDLE;
  assign rsp_valid=rst_n && state==RESPOND;
  assign r_read=rst_n && (state==OLD_READ || state==CANDIDATE_READ);
  assign r_bank=state==OLD_READ ? active_bank : !active_bank;
  assign r_read_take=rst_n && (state==OLD_WAIT || state==CANDIDATE_WAIT);
  assign r_load=rst_n && state==LOAD_DECAY;
  assign r_coefficient={96'b0,decay};
  assign r_cmd=rst_n && state==START_R;
  assign r_role=active_bank;
  assign r_rsp_ready=rst_n && state==WAIT_R;
  assign e_valid=rst_n && state==START_E;
  assign e_a=payload;
  assign e_rsp_ready=rst_n && state==WAIT_E;
  assign g_valid=rst_n && state==START_G;
  assign g_x=payload[31:0];
  assign g_rsp_ready=rst_n && state==WAIT_G;
  assign s_valid=rst_n && (state==WRITE_S || state==READ_S);
  assign s_write=state==WRITE_S;
  assign s_word=dst;
  assign s_data=payload;
  assign s_rsp_ready=rst_n && (state==WAIT_WRITE || state==WAIT_READ);
  assign consumer_valid=rst_n && state==SEND_CONSUMER;
  assign consumer_identity={rsp_job,rsp_epoch,rsp_task_sequence,generation+32'd1};
  assign consumer_data=payload;
  assign receipt_ready=rst_n && state==WAIT_RECEIPT;
  assign receipt_reject=receipt_ready && receipt_valid && receipt_identity!=consumer_identity;

  always @(posedge clk) begin
    if (!rst_n) begin
      state<=IDLE; active_bank<=0; generation<=0; candidate_valid<=0; publish<=0;
      receipt_wait<=0; dst<=0; decay<=0; payload<=0;
      rsp_token<=0; rsp_sequence<=0; rsp_job<=0; rsp_epoch<=0; rsp_task_sequence<=0;
      rsp_status<=0; rsp_read_bytes<=0; rsp_write_bytes<=0; rsp_saturated<=0;
    end else begin
      publish<=0;
      case (state)
        IDLE: if (svc_valid) begin
          rsp_token<=svc_token; rsp_sequence<=svc_sequence; rsp_job<=svc_job;
          rsp_epoch<=svc_epoch; rsp_task_sequence<=svc_task_sequence;
          rsp_status<=0; rsp_read_bytes<=0; rsp_write_bytes<=0; rsp_saturated<=0;
          if (svc_resource!=C_STATE_RESOURCE || !c_state_desc_ok(svc_desc)) begin
            rsp_status<=5; state<=RESPOND;
          end else if (&generation) begin
            rsp_status<=7; state<=RESPOND;
          end else begin
            dst<=svc_desc[512+:10]; decay<=svc_desc[544+:32]; state<=OLD_READ;
          end
        end
        OLD_READ: if (r_read_ready) state<=OLD_WAIT;
        OLD_WAIT: if (r_read_rsp) state<=LOAD_DECAY;
        LOAD_DECAY: if (r_load_ready) state<=START_R;
        START_R: if (r_cmd_ready) state<=WAIT_R;
        WAIT_R: if (r_rsp_valid) begin
          if (r_error) begin rsp_status<=9; state<=RESPOND; end
          else begin candidate_valid<=1; state<=CANDIDATE_READ; end
        end
        CANDIDATE_READ: if (r_read_ready) state<=CANDIDATE_WAIT;
        CANDIDATE_WAIT: if (r_read_rsp) begin payload<=r_data; state<=START_E; end
        START_E: if (e_ready) state<=WAIT_E;
        WAIT_E: if (e_rsp_valid) begin
          rsp_saturated<=e_saturated;
          if (e_error) begin rsp_status<=9; candidate_valid<=0; state<=RESPOND; end
          else begin payload<=e_result; state<=START_G; end
        end
        START_G: if (g_ready) state<=WAIT_G;
        WAIT_G: if (g_rsp_valid) begin
          rsp_saturated<=rsp_saturated || g_saturated;
          if (g_error) begin rsp_status<=9; candidate_valid<=0; state<=RESPOND; end
          else begin payload<={96'b0,g_result}; state<=WRITE_S; end
        end
        WRITE_S: if (s_ready) state<=WAIT_WRITE;
        WAIT_WRITE: if (s_rsp_valid) begin
          if (s_rsp_data!=payload) begin rsp_status<=9; candidate_valid<=0; state<=RESPOND; end
          else begin rsp_write_bytes<=16; state<=READ_S; end
        end
        READ_S: if (s_ready) state<=WAIT_READ;
        WAIT_READ: if (s_rsp_valid) begin
          rsp_read_bytes<=16;
          if (s_rsp_data!=payload) begin rsp_status<=9; candidate_valid<=0; state<=RESPOND; end
          else begin payload<=s_rsp_data; state<=SEND_CONSUMER; end
        end
        SEND_CONSUMER: if (consumer_ready) begin receipt_wait<=0; state<=WAIT_RECEIPT; end
        WAIT_RECEIPT: begin
          if (receipt_valid && receipt_identity==consumer_identity) begin
            if (receipt_error) rsp_status<=9;
            else begin
              active_bank<=!active_bank;
              generation<=generation+32'd1;
              publish<=1;
            end
            candidate_valid<=0; state<=RESPOND;
          end else if (receipt_wait==LAST_RECEIPT_WAIT) begin
            rsp_status<=9; candidate_valid<=0; state<=RESPOND;
          end else receipt_wait<=receipt_wait+1'b1;
        end
        RESPOND: if (rsp_ready) state<=IDLE;
        default: begin state<=RESPOND; rsp_status<=9; candidate_valid<=0; end
      endcase
    end
  end
endmodule
