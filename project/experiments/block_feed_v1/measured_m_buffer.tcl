# Actual M receiver-equipped GRT has one remaining BUF_X1 cap violation:
# hold40391/Z,84.73fF>60.73fF. A real BUF_X2 gives121.15fF library limit.
global_route -start_incremental
set block [ord::get_db_block]
set inst [$block findInst hold40391]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne "BUF_X1"} {error "Measured M driver identity changed"}
proc feed_pin_snapshot {inst} {
 set pins {}
 foreach term [$inst getITerms] {
  set def [$term getMTerm]
  if {[$def getSigType] in {POWER GROUND}} {continue}
  set net [$term getNet]
  if {$net eq "NULL"} {error "Open measured driver pin"}
  lappend pins [list [$def getName] [$def getIoType] [$net getName]]
 }
 return [lsort $pins]
}
set old [feed_pin_snapshot $inst]
set master [[ord::get_db] findMaster BUF_X2]
if {$master eq "NULL" || ![$inst swapMaster $master]} {error "Measured M sizing failed"}
if {[feed_pin_snapshot $inst] ne $old} {error "Measured buffer signal identity changed"}
foreach term [$inst getITerms] {
 set kind [[$term getMTerm] getSigType]
 if {$kind in {POWER GROUND}} {
  set name [expr {$kind eq "POWER" ? "VDD" : "VSS"}]
  set net [$block findNet $name]
  if {$net eq "NULL"} {error "Original PG missing"}
  $term connect $net
 }
}
global_connect
set_dont_touch [get_cells hold40391]
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
puts $f "target\thold40391\tBUF_X1\tBUF_X2"
puts $f "final\t$caps\t$slews\t$setup\t$hold"
close $f
report_checks -path_delay min_max -group_path_count 3 -digits 12 > $::env(RESULTS_DIR)/feed-measured-buffer-timing.rpt
report_check_types -max_capacitance -max_slew -violators -digits 12 > $::env(RESULTS_DIR)/feed-measured-buffer-electrical.rpt
if {$caps!=0 || $slews!=0 || $setup!=0 || $hold!=0} {error "Measured sizing did not close all native rules; no waiver"}
write_guides $::env(RESULTS_DIR)/route.guide
