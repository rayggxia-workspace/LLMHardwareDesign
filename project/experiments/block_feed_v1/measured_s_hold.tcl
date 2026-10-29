# Measured S GRT: six reset->AOI->control-D shorts, two din[31]->D
# sub-picosecond shorts, and two overloaded BUF_X4 data drivers. Delay only
# the six sequential reset branches; reset->ready is a separate tight path.
# No clock/state/SDC or timing exception is changed.
set block [ord::get_db_block]
if {[$block getName] ne "block_feed_s_macro"} {error "Measured S top changed"}
if {[llength [info commands odb::dbInst_isDoNotTouch]]==1} {
  set getter isDoNotTouch
} elseif {[llength [info commands odb::dbInst_getDoNotTouch]]==1} {
  set getter getDoNotTouch
} else {error "Missing scoped native protection readback"}
set f [open $::env(RESULTS_DIR)/feed-measured-s-repair.tsv w]

proc feed_s_signal_pins {inst} {
  set pins {}
  foreach term [$inst getITerms] {
    set def [$term getMTerm]
    if {[$def getSigType] in {POWER GROUND}} {continue}
    set net [$term getNet]
    if {$net eq "NULL"} {error "Measured driver has open signal pin"}
    lappend pins [list [$def getName] [$def getIoType] [$net getName]]
  }
  return [lsort $pins]
}
foreach {name previous next_master} {
  wire42991 BUF_X4 BUF_X8
  wire42863 BUF_X4 BUF_X8
  output964 BUF_X1 BUF_X2
} {
  set inst [$block findInst $name]
  if {$inst eq "NULL" || [[$inst getMaster] getName] ne $previous} {error "Measured S driver changed"}
  set before [feed_s_signal_pins $inst]
  set larger [[ord::get_db] findMaster $next_master]
  if {$larger eq "NULL" || ![$inst swapMaster $larger]} {error "Measured S sizing failed"}
  if {[feed_s_signal_pins $inst] ne $before} {error "Measured S sizing changed signal nets"}
  foreach term [$inst getITerms] {
    set kind [[$term getMTerm] getSigType]
    if {$kind in {POWER GROUND}} {
      set pg [$block findNet [expr {$kind eq "POWER" ? "VDD" : "VSS"}]]
      if {$pg eq "NULL"} {error "Missing original S PG"}
      $term connect $pg
    }
  }
  set_dont_touch [get_cells $name]
  puts $f "resize\t$name\t$previous\t$next_master"
}

proc feed_s_delay {block getter f prefix pins count final_master} {
  if {![llength $pins] || $count<1} {error "Empty measured delay"}
  set original [[lindex $pins 0] getNet]
  if {$original eq "NULL"} {error "Open measured delay source"}
  foreach pin $pins {if {[$pin getNet] ne $original} {error "Measured reset branches no longer share a source"}}
  set small [[ord::get_db] findMaster BUF_X1]
  set last [[ord::get_db] findMaster $final_master]
  if {$small eq "NULL" || $last eq "NULL"} {error "Missing native delay master"}
  set anchor [[lindex $pins 0] getInst]
  lassign [$anchor getLocation] x y
  set row_height [$small getHeight]
  set rows [expr {($count+7)/8}]
  set core [$block getCoreArea]
  set xbase [expr {max([$core xMin],min($x-16000,[$core xMax]-36000))}]
  set ybase [expr {max([$core yMin],min($y-5*$row_height,[$core yMax]-($rows+2)*$row_height))}]
  set current $original
  for {set i 0} {$i<$count} {incr i} {
    set name ${prefix}_$i
    if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_net] ne "NULL"} {error "Duplicate measured S delay"}
    set next [odb::dbNet_create $block ${name}_net]
    set master [expr {$i==$count-1 ? $last : $small}]
    set buffer [odb::dbInst_create $block $master $name]
    set row [expr {$i/8}];set col [expr {$row%2 ? 7-$i%8 : $i%8}]
    $buffer setLocation [expr {$xbase+$col*4000}] [expr {$ybase+$row*$row_height}]
    $buffer setOrient R0;$buffer setPlacementStatus PLACED
    [$buffer findITerm A] connect $current
    [$buffer findITerm Z] connect $next
    foreach term [$buffer getITerms] {
      set kind [[$term getMTerm] getSigType]
      if {$kind in {POWER GROUND}} {
        set pg [$block findNet [expr {$kind eq "POWER" ? "VDD" : "VSS"}]]
        if {$pg eq "NULL"} {error "Missing delay PG"}
        $term connect $pg
      }
    }
    set_dont_touch [get_cells $name]
    puts $f "delay\t$name\t[$master getName]\t[$current getName]\t[$next getName]"
    set current $next
  }
  foreach pin $pins {
    set inst [$pin getInst];set protection [$inst $getter]
    $inst setDoNotTouch false
    try {$pin disconnect;$pin connect $current} finally {$inst setDoNotTouch $protection}
    if {[$inst $getter]!=$protection || [$pin getNet] ne $current} {error "Measured protection/connection mismatch"}
  }
  if {[llength [$current getITerms]]!=[llength $pins]+1} {error "Measured delay endpoint count changed"}
}

set reset_driver [$block findInst input175]
if {$reset_driver eq "NULL" || [[$reset_driver getMaster] getName] ne "BUF_X8"} {error "Measured reset driver changed"}
set reset_net [[$reset_driver findITerm Z] getNet]
set reset_pins {}
foreach suffix {1539975 1404330 1404306 1404275 1404322 1404294} {
  set name [format {$abc$1205636$auto$blifparse.cc:397:parse_blif$%s} $suffix]
  set inst [$block findInst $name]
  if {$inst eq "NULL" || [[$inst getMaster] getName] ne "AOI21_X1"} {error "Measured sequential reset gate changed"}
  set pin [$inst findITerm A]
  if {[$pin getNet] ne $reset_net} {error "Measured sequential reset source changed"}
  lappend reset_pins $pin
}
set untouched {}
foreach term [$reset_net getITerms] {
  if {[lsearch -exact $reset_pins $term]<0} {lappend untouched "[[$term getInst] getName]/[[$term getMTerm] getName]"}
}
if {[lsort $untouched] ne [lsort {input175/Z max_cap36103/A fanout36092/A}]} {error "Unmeasured reset fanout changed"}
feed_s_delay $block $getter $f feed_measured_s_reset_delay $reset_pins 80 BUF_X8
# Preserve the two branches used by the long reset->ready path.
foreach name {max_cap36103 fanout36092} {
  if {[[$block findInst $name] findITerm A] eq "NULL" || [[[$block findInst $name] findITerm A] getNet] ne $reset_net} {error "Long reset branch changed"}
}
foreach suffix {639369 639497 666028} {
  set name [format {$auto$ff.cc:337:slice$%s} $suffix]
  set inst [$block findInst $name]
  if {$inst eq "NULL" || [[$inst getMaster] getName] ne "DFF_X1"} {error "Measured din short endpoint changed"}
  feed_s_delay $block $getter $f feed_measured_s_endpoint_${suffix} [list [$inst findITerm D]] 2 BUF_X1
}
close $f
global_connect
detailed_placement_helper
check_placement -verbose
# Rebuild all global routes after loading a persisted checkpoint and moving
# cells, so the pre-DRT estimate covers the complete current route database.
set layers [list -signal "$::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER)"]
if {[info exists ::env(MIN_CLK_ROUTING_LAYER)] && [info exists ::env(MAX_CLK_ROUTING_LAYER)]} {
  lappend layers -clock "$::env(MIN_CLK_ROUTING_LAYER)-$::env(MAX_CLK_ROUTING_LAYER)"
}
set_routing_layers {*}$layers
pin_access
global_route -congestion_report_file $::env(REPORTS_DIR)/feed-s-full-global-route.rpt -congestion_iterations 30 -verbose
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
sta::find_timing
# Work only on measured data-net buffer DRVs. These are real native cells;
# preserve signal connectivity and PG, then reroute the changed nets. Starting
# from this full live global route keeps unchanged-net/clock RC available.
set closure [open $::env(RESULTS_DIR)/feed-s-live-closure.tsv w]
for {set attempt 0} {$attempt<4} {incr attempt} {
  sta::find_timing
  set current [list [sta::max_capacitance_violation_count] [sta::max_slew_violation_count] [sta::endpoint_violation_count max] [sta::endpoint_violation_count min]]
  puts $closure "$attempt\t[join $current \t]";flush $closure
  if {$current eq {0 0 0 0}} {break}
  report_check_types -max_capacitance -violators -digits 12 > $::env(RESULTS_DIR)/feed-s-live-caps-$attempt.rpt
  set capfile [open $::env(RESULTS_DIR)/feed-s-live-caps-$attempt.rpt r]
  set captext [read $capfile];close $capfile
  global_route -start_incremental
  foreach line [split $captext \n] {
    if {![regexp {^([^[:space:]]+)/Z[[:space:]]+.*\(VIOLATED\)} $line -> name]} {continue}
    set inst [$block findInst $name]
    if {$inst eq "NULL"} {error "Measured capacitance driver missing"}
    set previous [[$inst getMaster] getName]
    if {$previous ni {BUF_X1 BUF_X2 BUF_X4 BUF_X8 CLKBUF_X1 CLKBUF_X2 CLKBUF_X3}} {error "Unqualified cap repair master: $name $previous"}
    set net [[$inst findITerm Z] getNet]
    if {[$net getSigType] in {CLOCK POWER GROUND}} {error "Cap repair must be a data-net buffer"}
    set before [feed_s_signal_pins $inst]
    if {![$inst swapMaster [[ord::get_db] findMaster BUF_X16]]} {error "Native cap sizing failed"}
    if {[feed_s_signal_pins $inst] ne $before} {error "Cap sizing changed function/connectivity"}
    puts $closure "resize\t$name\t$previous\tBUF_X16"
  }
  global_connect
  detailed_placement_helper
  check_placement -verbose
  global_route -end_incremental
  estimate_parasitics -global_routing
  sta::find_timing
  # Match this image's global_route.tcl: resizer owns its parasitic
  # update session; bracket the subsequent DPL, not repair_timing itself.
  repair_timing -setup_margin 0 -hold_margin 0.020 -repair_tns 100 -verbose
  global_route -start_incremental
  global_connect
  detailed_placement_helper
  check_placement -verbose
  global_route -end_incremental
  estimate_parasitics -global_routing
}
close $closure
set counts [list [sta::max_capacitance_violation_count] [sta::max_slew_violation_count] [sta::endpoint_violation_count max] [sta::endpoint_violation_count min]]
set f [open $::env(RESULTS_DIR)/feed-measured-s-checks.tsv w]
puts $f [join $counts "\t"];close $f
report_checks -path_delay min_max -group_path_count 256 -digits 12 > $::env(RESULTS_DIR)/feed-measured-s-timing.rpt
report_check_types -max_capacitance -max_slew -violators -digits 12 > $::env(RESULTS_DIR)/feed-measured-s-electrical.rpt
if {$counts ne {0 0 0 0}} {error "Measured S branch repair did not close all native checks"}
write_guides $::env(RESULTS_DIR)/route.guide
