# The native S GRT repair retained a short reset -> control-D path. Delay
# only reset's existing input-buffer branch in the fixed lower-metal leaf.
# No clock, state, handshake, timing exception or SDC is changed.
global_route -start_incremental
set block [ord::get_db_block]
if {[$block getName] ne "block_feed_s_macro"} {error "Measured S top changed"}
set target [$block findInst input175]
if {$target eq "NULL" || [[$target getMaster] getName] ne "BUF_X8"} {error "Measured S reset buffer changed"}
set pin [$target findITerm A]
set original [$pin getNet]
set reset [$block findBTerm reset]
if {$original eq "NULL" || $reset eq "NULL"} {error "Missing measured reset branch"}
set drivers {}
foreach term [$original getITerms] {
  if {[[$term getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $term}
}
if {[llength $drivers]!=1 || [llength [$original getITerms]]!=2} {error "Measured reset fanout changed"}
set driver [lindex $drivers 0]
set receiver [$driver getInst]
if {![string match feed_input_receiver_* [$receiver getName]] ||
    [[$receiver getMaster] getName] ne "BUF_X8" ||
    [[$receiver findITerm A] getNet] ne [$reset getNet]} {error "Measured reset source identity changed"}
if {[llength [info commands odb::dbInst_isDoNotTouch]]==1} {
  set getter isDoNotTouch
} elseif {[llength [info commands odb::dbInst_getDoNotTouch]]==1} {
  set getter getDoNotTouch
} else {error "Missing scoped native protection readback"}
set protection [$target $getter]
set master [[ord::get_db] findMaster BUF_X1]
if {$master eq "NULL"} {error "Missing native reset delay cell"}
set core [$block getCoreArea]
lassign [$target getLocation] x y
set row_height [$master getHeight]
set xbase [expr {max([$core xMin],min($x-16000,[$core xMax]-36000))}]
set ybase [expr {max([$core yMin],min($y-5*$row_height,[$core yMax]-12*$row_height))}]
set f [open $::env(RESULTS_DIR)/feed-measured-s-reset-delay.tsv w]
set current $original
for {set i 0} {$i<80} {incr i} {
  set name feed_measured_s_reset_delay_$i
  if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_net] ne "NULL"} {error "Duplicate reset delay"}
  set next [odb::dbNet_create $block ${name}_net]
  set buffer [odb::dbInst_create $block $master $name]
  set row [expr {$i/8}]
  set col [expr {$row%2 ? 7-$i%8 : $i%8}]
  $buffer setLocation [expr {$xbase+$col*4000}] [expr {$ybase+$row*$row_height}]
  $buffer setOrient R0
  $buffer setPlacementStatus PLACED
  [$buffer findITerm A] connect $current
  [$buffer findITerm Z] connect $next
  foreach term [$buffer getITerms] {
    set kind [[$term getMTerm] getSigType]
    if {$kind in {POWER GROUND}} {
      set supply [expr {$kind eq "POWER" ? "VDD" : "VSS"}]
      set pg [$block findNet $supply]
      if {$pg eq "NULL"} {error "Missing original S PG"}
      $term connect $pg
    }
  }
  set_dont_touch [get_cells $name]
  puts $f "$name\tBUF_X1\t[$current getName]\t[$next getName]"
  set current $next
}
$target setDoNotTouch false
try {$pin disconnect; $pin connect $current} finally {$target setDoNotTouch $protection}
if {[$target $getter]!=$protection || [llength [$current getITerms]]!=2} {error "Reset branch/protection mismatch"}
close $f
global_connect
detailed_placement_helper
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
sta::find_timing
set counts [list [sta::max_capacitance_violation_count] [sta::max_slew_violation_count] [sta::endpoint_violation_count max] [sta::endpoint_violation_count min]]
set f [open $::env(RESULTS_DIR)/feed-measured-s-checks.tsv w]
puts $f [join $counts "\t"];close $f
report_checks -path_delay min_max -group_path_count 6 -digits 12 > $::env(RESULTS_DIR)/feed-measured-s-timing.rpt
report_check_types -max_capacitance -max_slew -violators -digits 12 > $::env(RESULTS_DIR)/feed-measured-s-electrical.rpt
if {$counts ne {0 0 0 0}} {error "Measured S reset delay did not close all native checks"}
write_guides $::env(RESULTS_DIR)/route.guide
