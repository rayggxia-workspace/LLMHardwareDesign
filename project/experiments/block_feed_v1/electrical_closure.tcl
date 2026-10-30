# Close DRVs after global-route hold repair, using unchanged native limits.
# Every change stays in the prefabricated native macro and is re-routed.
global_route -start_incremental
global_route -end_incremental
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
sta::find_timing
set feed_closure [open $::env(RESULTS_DIR)/feed-electrical-closure.tsv w]
for {set attempt 0} {$attempt<3} {incr attempt} {
  set caps [sta::max_capacitance_violation_count]
  set slews [sta::max_slew_violation_count]
  set setup [sta::endpoint_violation_count max]
  set hold [sta::endpoint_violation_count min]
  puts $feed_closure "$attempt\t$caps\t$slews\t$setup\t$hold"
  flush $feed_closure
  if {$caps==0 && $slews==0 && $setup==0 && $hold==0} {break}
  global_route -start_incremental
  if {$caps>0 || $slews>0} {repair_design -cap_margin 40 -verbose}
  if {$setup>0 || $hold>0} {repair_timing -setup_margin 0 -hold_margin 0.020 -repair_tns 100 -verbose}
  global_connect
  detailed_placement_helper
  check_placement -verbose
  global_route -end_incremental
  estimate_parasitics -global_routing
}
set caps [sta::max_capacitance_violation_count]
set slews [sta::max_slew_violation_count]
set setup [sta::endpoint_violation_count max]
set hold [sta::endpoint_violation_count min]
puts $feed_closure "final\t$caps\t$slews\t$setup\t$hold"
close $feed_closure
if {$caps!=0 || $slews!=0 || $setup!=0 || $hold!=0} {error "Native pre-detail electrical/timing closure failed; no waiver"}
write_guides $::env(RESULTS_DIR)/route.guide
