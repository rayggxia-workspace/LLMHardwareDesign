`timescale 1ns/1ps
// One outstanding source object on a fixed forward/reverse edge.
// store_commit belongs to that edge and comes from the destination S write response.
module p_stored_ack_guard #(parameter integer ID_BITS=272) (
  input wire clk, reset,
  input wire arm_valid, output wire arm_ready, input wire [ID_BITS-1:0] arm_identity,
  input wire store_commit,
  input wire ack_valid, output wire ack_ready, input wire [ID_BITS-1:0] ack_identity,
  output reg done_valid, input wire done_ready,
  output reg rejected, output reg busy
);
  reg [ID_BITS-1:0] identity;
  reg committed;

  assign arm_ready = !reset && !busy;
  assign ack_ready = !reset;

  always @(posedge clk) begin
    if (reset) begin
      busy <= 0;
      committed <= 0;
      done_valid <= 0;
      rejected <= 0;
    end else begin
      rejected <= 0;
      if (arm_valid && arm_ready) begin
        identity <= arm_identity;
        busy <= 1;
      end
      if (store_commit && busy)
        committed <= 1;
      if (ack_valid && ack_ready) begin
        if (busy && committed && !done_valid && ack_identity == identity)
          done_valid <= 1;
        else
          rejected <= 1;
      end
      if (done_valid && done_ready) begin
        busy <= 0;
        committed <= 0;
        done_valid <= 0;
      end
    end
  end
endmodule
