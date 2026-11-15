`timescale 1ns/1ps

// Native control link for consecutive hardware target IDs. The MC's forward
// data and framing are shared; each branch has its own valid and ready.
// Return source identity comes from the physical branch, and the MC bridge
// checks it against the first beat before admitting the packet.
module mc_lc_packet128_switch #(
  parameter int ENDPOINTS = 3,
  parameter logic [ENDPOINTS-1:0] REBIND_TARGET = '0,
  parameter logic [8*ENDPOINTS-1:0] LOCAL_TARGET = '0
) (
  input  logic clk, reset,
  input  logic tx_valid, tx_sop,
  output logic tx_ready,
  input  logic [7:0] tx_target, tx_header_target,
  output logic [ENDPOINTS-1:0] lc_rx_valid,
  input  logic [ENDPOINTS-1:0] lc_rx_ready,
  output logic [8*ENDPOINTS-1:0] lc_rx_target, lc_rx_header_target,
  input  logic [ENDPOINTS-1:0] lc_tx_valid,
  output logic [ENDPOINTS-1:0] lc_tx_ready,
  input  logic [128*ENDPOINTS-1:0] lc_tx_data,
  input  logic [ENDPOINTS-1:0] lc_tx_sop, lc_tx_eop,
  output logic rx_valid,
  input  logic rx_ready,
  output logic [127:0] rx_data,
  output logic [7:0] rx_source,
  output logic rx_sop, rx_eop,
  output logic transport_idle
);
  logic [ENDPOINTS-1:0] destination, held_return, priority_mask;
  logic [ENDPOINTS-1:0] preferred, eligible, first, selected, next_priority;
  logic [127:0] return_data;
  logic [7:0] local_return_target;

  assign preferred = lc_tx_valid & priority_mask;
  assign eligible = |preferred ? preferred : lc_tx_valid;
  assign selected = |held_return ? held_return : first;
  assign tx_ready = !reset && |(destination & lc_rx_ready);
  assign lc_rx_valid = (!reset && tx_valid) ? destination : '0;
  assign lc_tx_ready = (!reset && rx_ready) ? selected : '0;
  assign rx_valid = !reset && |(selected & lc_tx_valid);
  assign rx_sop = |(selected & lc_tx_sop);
  assign rx_eop = |(selected & lc_tx_eop);
  // The parent also checks the controllers and other in-flight transports
  // before allowing a deployment generation to change.
  assign transport_idle = !reset && !tx_valid && !(|lc_tx_valid) && !(|held_return);

  for (genvar branch = 0; branch < ENDPOINTS; branch++) begin : branches
    assign destination[branch] = tx_target == 8'(branch);
    if (REBIND_TARGET[branch]) begin : local_binding
      localparam logic [7:0] TARGET = LOCAL_TARGET[8*branch+:8];
      assign lc_rx_target[8*branch+:8] = TARGET;
      // Retain first-beat header validation at the local controller.
      assign lc_rx_header_target[8*branch+:8] = !tx_sop ? tx_header_target :
        tx_header_target == tx_target ? TARGET : TARGET ^ 8'h01;
    end else begin : direct_binding
      assign lc_rx_target[8*branch+:8] = tx_target;
      assign lc_rx_header_target[8*branch+:8] = tx_header_target;
    end
    if (branch == 0) begin : first_branch
      assign first[branch] = eligible[branch];
      assign next_priority[branch] = 1'b0;
    end else begin : following_branches
      assign first[branch] = eligible[branch] && !(|eligible[branch-1:0]);
      assign next_priority[branch] = |selected[branch-1:0];
    end
  end

  always_comb begin
    return_data = '0;
    rx_source = '0;
    local_return_target = '0;
    for (int branch = 0; branch < ENDPOINTS; branch++) begin
      return_data |= lc_tx_data[128*branch+:128] & {128{selected[branch]}};
      rx_source |= 8'(branch) & {8{selected[branch]}};
      local_return_target |= LOCAL_TARGET[8*branch+:8] & {8{selected[branch]}};
    end
    rx_data = return_data;
    if (rx_sop && |(selected & REBIND_TARGET)) begin
      rx_data[24+:8] = rx_source;
      // A wrong physical source header must still fail MC packet admission.
      if (return_data[24+:8] != local_return_target) rx_data[0+:16] = '0;
    end
  end

  always_ff @(posedge clk) begin
    if (reset) begin
      held_return <= '0;
      priority_mask <= '0;
    end else if (rx_valid) begin
      if (rx_ready && rx_eop) begin
        held_return <= '0;
        priority_mask <= next_priority;
      end else begin
        // Hold even on a stalled first beat, and across gaps within a frame.
        held_return <= selected;
      end
    end
  end
endmodule
