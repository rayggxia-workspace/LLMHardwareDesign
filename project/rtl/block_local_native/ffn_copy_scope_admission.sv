// Admit one FFN scope only if all local generation counters can cover its
// compiled worst case. The request and its budget stay stable until accepted.
// A running scope keeps using its reserved generations during a pending rearm.
module ffn_copy_scope_admission(
  input wire scope_valid,
  output wire scope_ready,
  input wire [15:0] tile_generation,scatter_generation,mid_generation,
  input wire [15:0] tile_budget,scatter_budget,mid_budget,
  // Scope idle includes terminal retirement. Its generation counters stay
  // fixed until the next launch or a proved rearm.
  input wire scope_idle,admit_new_owner,fence_done,
  output wire rearm_valid,
  output wire launch_valid,
  input wire launch_ready
);
  wire [16:0] tile_end={1'b0,tile_generation}+{1'b0,tile_budget};
  wire [16:0] scatter_end={1'b0,scatter_generation}+{1'b0,scatter_budget};
  wire [16:0] mid_end={1'b0,mid_generation}+{1'b0,mid_budget};
  wire fits=tile_end<=17'd65535&&scatter_end<=17'd65535&&mid_end<=17'd65535;

  assign rearm_valid=scope_valid&&!fits&&!fence_done;
  assign launch_valid=scope_valid&&scope_idle&&fits&&admit_new_owner;
  assign scope_ready=launch_ready&&scope_idle&&fits&&admit_new_owner;
endmodule
