# Exact extracted failure: all twelve short paths share hold40391/Z after its
# necessary CLKBUF_X2 cap fix. Add three small data buffers before that cell.
# This is actual native circuit delay, not a hold exception or SDC change.
global_route -start_incremental
source [file join [file dirname $::env(DESIGN_CONFIG)] measured-driver.tcl]
set block [ord::get_db_block]
set inst [$block findInst hold40391]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne "CLKBUF_X2"} {error "Measured hold driver changed"}
set pin [$inst findITerm A]
set original [$pin getNet]
if {$original eq "NULL"} {error "Missing measured data input"}
set current $original
set master [[ord::get_db] findMaster BUF_X1]
if {$master eq "NULL"} {error "Missing native data delay cell"}
lassign [$inst getLocation] x y
set f [open $::env(RESULTS_DIR)/feed-measured-hold-delay.tsv w]
for {set i 0} {$i<3} {incr i} {
  set name feed_measured_hold_delay_$i
  if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_net] ne "NULL"} {error "Duplicate measured delay"}
  set next [odb::dbNet_create $block ${name}_net]
  set buffer [odb::dbInst_create $block $master $name]
  $buffer setLocation [expr {$x+($i+1)*2000}] $y
  $buffer setOrient R0;$buffer setPlacementStatus PLACED
  [$buffer findITerm A] connect $current
  [$buffer findITerm Z] connect $next
  foreach term [$buffer getITerms] {
    set kind [[$term getMTerm] getSigType]
    if {$kind in {POWER GROUND}} {
      set supply [expr {$kind eq "POWER" ? "VDD" : "VSS"}]
      set pg [$block findNet $supply]
      if {$pg eq "NULL"} {error "Original PG missing"}
      $term connect $pg
    }
  }
  set_dont_touch [get_cells $name]
  puts $f "$name\tBUF_X1\t[$current getName]\t[$next getName]"
  set current $next
}
if {[llength [info commands odb::dbInst_isDoNotTouch]]==1} {
  set getter isDoNotTouch
} elseif {[llength [info commands odb::dbInst_getDoNotTouch]]==1} {
  set getter getDoNotTouch
} else {error "Missing native scoped protection readback"}
set protection [$inst $getter]
if {!$protection} {error "Measured sized driver unexpectedly unprotected"}
$inst setDoNotTouch false
try {
  $pin disconnect;$pin connect $current
} finally {
  $inst setDoNotTouch $protection
}
if {[$inst $getter]!=$protection} {error "Measured driver protection was not restored"}
if {[$pin getNet] eq $original || [llength [$current getITerms]]!=2} {error "Measured delay chain disconnected"}
close $f
# The one-session native reroute additionally measured a -5.94ps short
# internal path ending at this exact DFF. Delay only its D input, not CK/Q.
set endpoint [$block findInst {$auto$ff.cc:337:slice$562242}]
if {$endpoint eq "NULL" || [[$endpoint getMaster] getName] ne "DFF_X1"} {error "Measured short endpoint changed"}
set epin [$endpoint findITerm D]
set current [$epin getNet]
if {$current eq "NULL"} {error "Measured short endpoint is open"}
lassign [$endpoint getLocation] ex ey
set f [open $::env(RESULTS_DIR)/feed-measured-hold-delay.tsv a]
for {set i 0} {$i<2} {incr i} {
  set name feed_measured_endpoint_delay_$i
  if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_net] ne "NULL"} {error "Duplicate endpoint delay"}
  set next [odb::dbNet_create $block ${name}_net]
  set buffer [odb::dbInst_create $block $master $name]
  $buffer setLocation [expr {$ex+($i+1)*2000}] $ey
  $buffer setOrient R0;$buffer setPlacementStatus PLACED
  [$buffer findITerm A] connect $current
  [$buffer findITerm Z] connect $next
  foreach term [$buffer getITerms] {
    set kind [[$term getMTerm] getSigType]
    if {$kind in {POWER GROUND}} {
      set supply [expr {$kind eq "POWER" ? "VDD" : "VSS"}]
      $term connect [$block findNet $supply]
    }
  }
  set_dont_touch [get_cells $name]
  puts $f "$name\tBUF_X1\t[$current getName]\t[$next getName]"
  set current $next
}
set endpoint_protection [$endpoint $getter]
$endpoint setDoNotTouch false
try {$epin disconnect;$epin connect $current} finally {$endpoint setDoNotTouch $endpoint_protection}
if {[$endpoint $getter]!=$endpoint_protection || [llength [$current getITerms]]!=2} {error "Endpoint delay/protection mismatch"}
close $f
global_connect
detailed_placement_helper
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
sta::find_timing
set counts [list [sta::max_capacitance_violation_count] [sta::max_slew_violation_count] [sta::endpoint_violation_count max] [sta::endpoint_violation_count min]]
set f [open $::env(RESULTS_DIR)/feed-measured-hold-checks.tsv w]
puts $f [join $counts "\t"];close $f
report_checks -path_delay min_max -group_path_count 3 -digits 12 > $::env(RESULTS_DIR)/feed-measured-hold-timing.rpt
report_check_types -max_capacitance -max_slew -violators -digits 12 > $::env(RESULTS_DIR)/feed-measured-hold-electrical.rpt
if {$counts ne {0 0 0 0}} {error "Measured delay did not close native timing/electrical checks"}
write_guides $::env(RESULTS_DIR)/route.guide
