`timescale 1ns/1ps
// Two tagged *control* clients, one unchanged ordinary local_s_base port.
// Exactly two owner/tag records cover all accepted but unretired requests.
// The SRAM owns its existing response data buffers; this adapter adds no data
// FIFO, bank, wide port or assumed response tag pin on the SRAM leaf.
module native_s128_mux2(
  input logic clk, reset,
  input logic [1:0] c_valid, c_write,
  input logic [19:0] c_address,
  input logic [255:0] c_data,
  input logic [63:0] c_tag,
  output logic [1:0] c_ready, c_response_valid,
  input logic [1:0] c_response_ready,
  output logic [127:0] c_response_data,
  output logic [63:0] c_response_tag,
  output logic req_valid, req_write,
  output logic [9:0] req_address,
  output logic [127:0] req_data,
  input logic req_ready, rsp_valid,
  output logic rsp_ready,
  input logic [127:0] rsp_data,
  output logic [1:0] owners_occupied
);
  logic owner[2];
  logic [31:0] tag[2];
  logic head, tail, round_robin, selected, held_selection, stalled;
  logic push, pop, space;
  assign owners_occupied = count;
  logic [1:0] count;
  assign selected = stalled ? held_selection :
      (c_valid[round_robin] ? round_robin : !round_robin);
  assign c_response_valid = {2{!reset && count != 0 && rsp_valid}} &
      (owner[head] ? 2'b10 : 2'b01);
  assign c_response_tag = {tag[head],tag[head]};
  assign c_response_data = rsp_data;
  assign rsp_ready = !reset && count != 0 && c_response_ready[owner[head]];
  assign pop = rsp_valid && rsp_ready;
  assign space = count < 2 || pop;
  assign req_valid = !reset && space && c_valid[selected];
  assign req_write = c_write[selected];
  assign req_address = c_address[10*selected+:10];
  assign req_data = c_data[128*selected+:128];
  assign c_ready = {2{!reset && space && req_ready}} & (selected ? 2'b10 : 2'b01);
  assign push = req_valid && req_ready;
  always_ff @(posedge clk) begin
    if (reset) begin
      head<=0;tail<=0;count<=0;round_robin<=0;stalled<=0;held_selection<=0;
      owner[0]<=0;owner[1]<=0;tag[0]<=0;tag[1]<=0;
    end else begin
`ifndef SYNTHESIS
      assert(count<=2) else $fatal(1,"native S owner queue overflow");
      assert(!rsp_valid || count!=0) else $fatal(1,"native S orphan response");
`endif
      if (req_valid && !req_ready) begin stalled<=1;held_selection<=selected;end
      if (push) begin
        owner[tail]<=selected;tag[tail]<=c_tag[32*selected+:32];tail<=!tail;
        round_robin<=!selected;stalled<=0;
      end
      if (pop) head<=!head;
      case ({push,pop})
        2'b10: count<=count+1'b1;
        2'b01: count<=count-1'b1;
        default: begin end
      endcase
    end
  end
endmodule
