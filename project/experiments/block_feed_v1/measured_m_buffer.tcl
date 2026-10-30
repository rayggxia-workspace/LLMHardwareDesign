# Actual M receiver-equipped GRT has one remaining CLKBUF_X1 cap violation:
# hold40391/Z,84.73fF>60.73fF. Master was read from the actual source ODB.
global_route -start_incremental
source [file join [file dirname $::env(DESIGN_CONFIG)] measured-driver.tcl]
detailed_placement_helper
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
sta::find_timing
set caps [sta::max_capacitance_violation_count]
set slews [sta::max_slew_violation_count]
set setup [sta::endpoint_violation_count max]
set hold [sta::endpoint_violation_count min]
set f [open $::env(RESULTS_DIR)/feed-electrical-closure.tsv w]
puts $f "target\thold40391\tCLKBUF_X1\tCLKBUF_X2"
puts $f "final\t$caps\t$slews\t$setup\t$hold"
close $f
report_checks -path_delay min_max -group_path_count 3 -digits 12 > $::env(RESULTS_DIR)/feed-measured-buffer-timing.rpt
report_check_types -max_capacitance -max_slew -violators -digits 12 > $::env(RESULTS_DIR)/feed-measured-buffer-electrical.rpt
if {$caps!=0 || $slews!=0 || $setup!=0 || $hold!=0} {error "Measured sizing did not close all native rules; no waiver"}
write_guides $::env(RESULTS_DIR)/route.guide
