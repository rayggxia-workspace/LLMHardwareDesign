// One synchronous, local fence for reuse of the finite FFN COPY tag namespace.
// The caller holds rearm_valid until ready. It must use admit_new_owner to gate
// the outer job and unrelated owners of this namespace. Work already admitted
// by the current job continues all of its child transfers until its terminal.
// The caller reserves the largest admitted job's generation budget at launch.
module ffn_copy_epoch_fence(
  input  wire clk,reset,
  input  wire rearm_valid,
  output wire rearm_ready,
  output reg  done_valid,
  input  wire done_ready,
  input  wire outer_scope_idle,
  input  wire header_tx_idle,
  input  wire [2:0] header_rx_idle,
  input  wire copy_idle,scatter_idle,
  input  wire x_quant_idle,mid_quant_idle,
  input  wire [2:0] p_a_drained,
  input  wire [3:0] s_owners_empty,
  // Assert only after the physical forward and reverse routes have no held
  // valid, buffered words, or ACKs. A DDR purge does not prove this condition.
  input  wire copy_transport_drained,
  output wire admit_new_owner,
  output wire namespace_rearm
);
  wire all_drained=outer_scope_idle&&header_tx_idle&&(&header_rx_idle)&&
      copy_idle&&scatter_idle&&x_quant_idle&&mid_quant_idle&&
      (&p_a_drained)&&(&s_owners_empty)&&copy_transport_drained;

  assign rearm_ready=!reset&&!done_valid&&all_drained;
  assign namespace_rearm=rearm_valid&&rearm_ready;
  assign admit_new_owner=!reset&&!rearm_valid&&!done_valid;

  always @(posedge clk)begin
    if(reset)done_valid<=0;
    else if(namespace_rearm)done_valid<=1;
    else if(done_valid&&done_ready)done_valid<=0;
  end
endmodule
