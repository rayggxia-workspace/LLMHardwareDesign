`timescale 1ns/1ps
// NoPool candidate: exactly 2x256B register tiles. This is an internal native
// adapter; these metadata buses are not proposed new leaf-macro pin bundles.
module private_a_tile_frontend(
  input logic clk, reset, halt, flush,
  input logic cmd_valid, output logic cmd_ready,
  input logic cmd_slot,
  input logic [15:0] cmd_generation, cmd_kk, cmd_planned_uses,
  input logic [127:0] cmd_key,
  input logic [9:0] cmd_S_base, cmd_copy_offset,
  input logic [127:0] copy_key,
  input logic [10:0] copy_committed_prefix,
  output logic load_done_valid, input logic load_done_ready,
  output logic load_done_slot, load_done_error,
  output logic [15:0] load_done_generation,
  output logic [127:0] load_done_key,
  output logic s_valid, input logic s_ready,
  output logic [9:0] s_address, output logic [31:0] s_tag,
  input logic response_valid, output logic response_ready,
  input logic [31:0] response_tag,
  input logic [127:0] response_data,
  input logic w_valid, output logic w_ready,
  input logic w_slot,
  input logic [15:0] w_generation, w_kk, w_use_sequence,
  input logic [127:0] w_key,
  input logic [31:0] w_record,
  input logic use_valid, output logic use_ready,
  input logic use_slot,
  input logic [15:0] use_generation, use_kk, use_sequence,
  input logic [127:0] use_key,
  output logic a_valid, input logic a_ready,
  output logic [255:0] a_data,
  output logic [2:0] a_step,
  output logic [31:0] a_weight_record,
  output logic [127:0] a_key,
  output logic a_slot,
  output logic [15:0] a_generation, a_kk, a_use_sequence,
  input logic close_valid, output logic close_ready,
  input logic close_slot,
  input logic [15:0] close_generation,
  input logic release_valid, output logic release_ready,
  input logic release_slot,
  input logic [15:0] release_generation,
  output logic quiescent, source_reads_drained,
  output logic [1:0] live_slots,
  output logic [31:0] fault_cycles
);
  typedef enum logic [1:0] {FREE, LOADING, READY, INVALID} slot_state_t;
  slot_state_t state[2];
  logic [127:0] A[2][16];
  logic [127:0] key[2];
  logic [15:0] generation[2], last_generation[2], kk[2];
  logic [15:0] planned[2], issued[2], completed[2], W_sequence[2];
  logic [31:0] W_record[2];
  logic [9:0] S_base[2], copy_offset[2];
  logic [4:0] returned[2];
  logic [1:0] closed, W_pending, done_pending, done_error;
  logic request_pending, inflight, request_slot, rr;
  logic [3:0] request_word;
  logic [9:0] request_address;
  logic [31:0] request_tag;
  logic active, active_slot;
  logic [2:0] step_q;
  logic [31:0] active_record;
  logic [15:0] active_sequence;
  logic error_pending;
  logic load_done_from_error;
  logic [127:0] error_key;
  logic error_slot;
  logic [15:0] error_generation;
  wire command_shape = cmd_generation > last_generation[cmd_slot] &&
      cmd_planned_uses != 0 && {1'b0,cmd_S_base} + 11'd16 <= 11'd1024 &&
      {1'b0,cmd_copy_offset} + 11'd16 <= 11'd1024 &&
      (state[!cmd_slot] == FREE || key[!cmd_slot] == cmd_key);
  wire W_identity = (state[w_slot] == READY || state[w_slot] == LOADING) && !closed[w_slot] &&
      w_key == key[w_slot] && w_generation == generation[w_slot] && w_kk == kk[w_slot] &&
      w_use_sequence == issued[w_slot] + 16'd1 && issued[w_slot] < planned[w_slot];
  wire W_match = W_identity && !W_pending[w_slot];
  wire use_identity = (state[use_slot] == READY || state[use_slot] == LOADING) &&
      !closed[use_slot] &&
      use_key == key[use_slot] && use_generation == generation[use_slot] &&
      use_kk == kk[use_slot] && use_sequence == issued[use_slot] + 16'd1 &&
      issued[use_slot] < planned[use_slot];
  wire use_match = use_identity && state[use_slot] == READY &&
      !done_pending[use_slot] && W_pending[use_slot] && !active &&
      use_sequence == W_sequence[use_slot];
  wire close_match = state[close_slot] == READY &&
      close_generation == generation[close_slot] && !closed[close_slot] &&
      issued[close_slot] == planned[close_slot];
  wire release_match = state[release_slot] == READY && closed[release_slot] &&
      release_generation == generation[release_slot] &&
      completed[release_slot] == planned[release_slot] && !done_pending[release_slot] &&
      !(active && active_slot == release_slot) && !W_pending[release_slot];
  wire response_match = inflight && response_tag == request_tag;
  wire fault_now = (cmd_valid && cmd_ready && !command_shape) ||
      (response_valid && response_ready && !response_match) ||
      (w_valid && !halt && !W_identity) || (use_valid && !halt && !use_identity) ||
      (close_valid && !close_match) || (release_valid && !release_match) ||
      (flush && !(halt && quiescent));
  assign cmd_ready = !reset && !halt && !error_pending && state[cmd_slot] == FREE;
  assign s_valid = !reset && request_pending;
  assign s_address = request_address;
  assign s_tag = request_tag;
  assign response_ready = !reset;
  assign w_ready = !reset && !halt && W_match;
  assign use_ready = !reset && !halt && use_match;
  assign close_ready = !reset && close_match;
  assign release_ready = !reset && release_match;
  assign a_valid = !reset && active;
  assign a_data = {A[active_slot][{step_q,1'b1}], A[active_slot][{step_q,1'b0}]};
  assign a_step = step_q;
  assign a_weight_record = active_record;
  assign a_key = key[active_slot];
  assign a_slot = active_slot;
  assign a_generation = generation[active_slot];
  assign a_kk = kk[active_slot];
  assign a_use_sequence = active_sequence;
  assign live_slots = {state[1] != FREE,state[0] != FREE};
  assign source_reads_drained = !request_pending && !inflight &&
      state[0] != LOADING && state[1] != LOADING;
  assign quiescent = !request_pending && !inflight && !active &&
      !load_done_valid && done_pending == 0 && !error_pending;

  always_ff @(posedge clk) begin
    if (reset) begin
      state[0]<=FREE;state[1]<=FREE;
      closed<=0;W_pending<=0;done_pending<=0;done_error<=0;
      request_pending<=0;inflight<=0;request_slot<=0;request_word<=0;
      request_address<=0;request_tag<=0;rr<=0;
      active<=0;active_slot<=0;step_q<=0;active_record<=0;active_sequence<=0;
      load_done_valid<=0;load_done_slot<=0;load_done_error<=0;
      load_done_generation<=0;load_done_key<=0;
      load_done_from_error<=0;
      error_pending<=0;error_key<=0;error_slot<=0;error_generation<=0;
      fault_cycles<=0;
      for(integer i=0;i<2;i=i+1) begin
        key[i]<=0;generation[i]<=0;last_generation[i]<=0;kk[i]<=0;
        planned[i]<=0;issued[i]<=0;completed[i]<=0;W_sequence[i]<=0;
        W_record[i]<=0;S_base[i]<=0;copy_offset[i]<=0;returned[i]<=0;
      end
    end else begin
      if(fault_now) fault_cycles<=fault_cycles+1'b1;
      if(cmd_valid && cmd_ready) begin
        if(cmd_generation>last_generation[cmd_slot]) last_generation[cmd_slot]<=cmd_generation;
        if(!command_shape) begin
          error_pending<=1;error_key<=cmd_key;error_slot<=cmd_slot;error_generation<=cmd_generation;
        end else begin
          state[cmd_slot]<=LOADING;key[cmd_slot]<=cmd_key;
          generation[cmd_slot]<=cmd_generation;last_generation[cmd_slot]<=cmd_generation;
          kk[cmd_slot]<=cmd_kk;planned[cmd_slot]<=cmd_planned_uses;
          S_base[cmd_slot]<=cmd_S_base;copy_offset[cmd_slot]<=cmd_copy_offset;
          returned[cmd_slot]<=0;issued[cmd_slot]<=0;completed[cmd_slot]<=0;
          closed[cmd_slot]<=0;W_pending[cmd_slot]<=0;done_pending[cmd_slot]<=0;done_error[cmd_slot]<=0;
        end
      end
      if(!request_pending && !inflight && !halt) begin
        for(integer n=1;n>=0;n=n-1) begin
          if(state[rr ^ 1'(n)]==LOADING && key[rr ^ 1'(n)]==copy_key &&
             {1'b0,copy_offset[rr ^ 1'(n)]}+{6'd0,returned[rr ^ 1'(n)]}<copy_committed_prefix) begin
            request_pending<=1;request_slot<=rr ^ 1'(n);
            request_word<=returned[rr ^ 1'(n)][3:0];
            request_address<=S_base[rr ^ 1'(n)]+{5'd0,returned[rr ^ 1'(n)]};
            request_tag<={generation[rr ^ 1'(n)],rr ^ 1'(n),returned[rr ^ 1'(n)][3:0],11'd0};
          end
        end
      end
      if(s_valid && s_ready) begin request_pending<=0;inflight<=1;rr<=!request_slot;end
      if(response_valid && response_ready && response_match) begin
        inflight<=0;A[request_slot][request_word]<=response_data;
        returned[request_slot]<=returned[request_slot]+1'b1;
        if(request_word==15) begin state[request_slot]<=READY;done_pending[request_slot]<=1;end
      end
      // A cancelled partial tile is invalidated only after the proffered request
      // and actual source response have drained. Its terminal is still held.
      if(halt && !request_pending && !inflight) begin
        for(integer i=0;i<2;i=i+1) begin
          if(state[i]==LOADING) begin state[i]<=INVALID;done_pending[i]<=1;done_error[i]<=1;end
        end
      end
      if(!load_done_valid) begin
        if(error_pending) begin
          load_done_valid<=1;load_done_error<=1;load_done_slot<=error_slot;load_done_from_error<=1;
          load_done_generation<=error_generation;load_done_key<=error_key;error_pending<=0;
        end else begin
          for(integer n=1;n>=0;n=n-1) begin
            if(done_pending[n]) begin
              load_done_valid<=1;load_done_error<=done_error[n];load_done_slot<=1'(n);load_done_from_error<=0;
              load_done_generation<=generation[n];load_done_key<=key[n];
            end
          end
        end
      end else if(load_done_ready) begin
        load_done_valid<=0;
        if(!load_done_from_error && state[load_done_slot]!=FREE && generation[load_done_slot]==load_done_generation)
          done_pending[load_done_slot]<=0;
      end
      if(w_valid && w_ready) begin
        W_pending[w_slot]<=1;W_sequence[w_slot]<=w_use_sequence;W_record[w_slot]<=w_record;
      end
      if(use_valid && use_ready) begin
        active<=1;active_slot<=use_slot;step_q<=0;
        active_record<=W_record[use_slot];active_sequence<=use_sequence;
        issued[use_slot]<=issued[use_slot]+1'b1;W_pending[use_slot]<=0;
      end
      if(a_valid && a_ready) begin
        if(step_q==7) begin active<=0;completed[active_slot]<=completed[active_slot]+1'b1;end
        else step_q<=step_q+1'b1;
      end
      if(close_valid && close_ready) closed[close_slot]<=1;
      if(release_valid && release_ready) state[release_slot]<=FREE;
      if(flush && halt && quiescent) begin
        state[0]<=FREE;state[1]<=FREE;closed<=0;W_pending<=0;
      end
    end
  end
endmodule
