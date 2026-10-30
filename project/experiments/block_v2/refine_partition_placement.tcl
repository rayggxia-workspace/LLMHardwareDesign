# Second, explicit timing-driven global placement after spatial buffering.
# The first geometric pass supplies real locations for the partition hook.
# Standard resize, CTS, routing and all final gates remain required afterward.
puts "ISSUE143_R_REFINE begin timing-driven placement after native spatial fanout buffers"
global_placement -density $::env(PLACE_DENSITY) -pad_left 0 -pad_right 0 \
  -routability_driven -timing_driven -skip_initial_place \
  -min_phi_coef 0.95 -max_phi_coef 1.05
estimate_parasitics -placement
detailed_placement_helper
check_placement -verbose
puts "ISSUE143_R_REFINE completed; downstream native electrical and timing repair remain enabled"
