# Real combinational delay on five measured fast reset branches; no SDC edits.
set block [ord::get_db_block]
if {[$block getName] ne "block_feed_s_macro"} {error "S reset repair scope mismatch"}
source [file join [file dirname $::env(DESIGN_CONFIG)] s-reset-config.tcl]
if {[llength $s_reset_targets]!=5 || $s_reset_count ni {48 64 96 128}} {error "Unexpected measured S repair"}
set master [[ord::get_db] findMaster BUF_X1]
if {$master eq "NULL"} {error "Missing real native BUF_X1"}
proc issue162_other_pins {inst} {
 set result {}
 foreach pin [$inst getITerms] {
  if {[[$pin getMTerm] getName] eq "A"} {continue}
  set net [$pin getNet]
  lappend result [list [[$pin getMTerm] getName] [expr {$net eq "NULL" ? "NULL" : [$net getName]}]]
 }
 return [lsort $result]
}
proc issue162_met {text} {
 set values [regexp -all -inline {([-+0-9.]+)\s+slack \(MET\)} $text]
 if {![llength $values] || [string match {*slack (VIOLATED)*} $text]} {error "Current reset branch timing guard failed"}
 set worst 1e9
 foreach {match value} $values {set worst [expr {min($worst,$value)}]}
 return $worst
}
set total_before [llength [$block getInsts]]
set targets {};set number 0
foreach row $s_reset_targets {
 lassign $row name pin_name master_name net_name
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne "AOI21_X1" || $master_name ne "AOI21_X1" || $pin_name ne "A"} {error "Measured S target identity changed"}
 set pin [$inst findITerm A]
 if {$pin eq "NULL" || [$pin getNet] eq "NULL" || [[$pin getNet] getName] ne $net_name} {error "Measured reset input net changed"}
 set sta_pin [get_pins [list ${name}/A]]
 if {[llength $sta_pin]!=1} {error "Measured reset STA branch missing"}
 set path $::env(RESULTS_DIR)/s-reset-before-$number-max.rpt
 report_checks -from [get_ports reset] -through $sta_pin -path_delay max -group_path_count 8 -digits 9 > $path
 set f [open $path r];set text [read $f];close $f
 set slack [issue162_met $text]
 if {$slack<2.0} {error "Insufficient current global-RC reset-only setup headroom"}
 report_checks -from [get_ports reset] -through $sta_pin -path_delay min -group_path_count 8 -digits 9 > $::env(RESULTS_DIR)/s-reset-before-$number-min.rpt
 lappend targets [list $inst $pin $slack];incr number
}
sta::find_timing
set baseline [list [sta::max_capacitance_violation_count] [sta::max_slew_violation_count] [sta::endpoint_violation_count max] [sta::endpoint_violation_count min]]
set f [open $::env(RESULTS_DIR)/s-reset-before-counts.tsv w];puts $f [join $baseline "\t"];close $f
global_route -start_incremental
set f [open $::env(RESULTS_DIR)/s-reset-delay.tsv w]
puts $f "config\t$s_reset_count\t$s_reset_evidence_sha"
set number 0
foreach row $targets {
 lassign $row inst pin setup
 set original [$pin getNet];set saved [issue162_other_pins $inst]
 set terms {};foreach term [$original getITerms] {lappend terms "[[$term getInst] getName]/[[$term getMTerm] getName]"}
 set ports {};foreach term [$original getBTerms] {lappend ports [$term getName]}
 set current $original;lassign [$inst getLocation] x y;set core [$block getCoreArea]
 set xbase [expr {max([$core xMin],min($x-8000,[$core xMax]-($s_reset_count+1)*3200))}]
 set ybase [expr {max([$core yMin],min($y-5600,[$core yMax]-5600))}]
 puts $f "target\t$number\t[$inst getName]\tA\t[$original getName]\t$setup"
 for {set i 0} {$i<$s_reset_count} {incr i} {
  set name issue162_s_reset_${number}_$i
  if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_net] ne "NULL"} {error "Duplicate S reset delay cell"}
  set next [odb::dbNet_create $block ${name}_net]
  set buffer [odb::dbInst_create $block $master $name]
  $buffer setLocation [expr {$xbase+$i*3200}] $ybase;$buffer setOrient R0;$buffer setPlacementStatus PLACED
  [$buffer findITerm A] connect $current;[$buffer findITerm Z] connect $next
  foreach term [$buffer getITerms] {
   set kind [[$term getMTerm] getSigType]
   if {$kind in {POWER GROUND}} {
    set pg [$block findNet [expr {$kind eq "POWER" ? "VDD" : "VSS"}]]
    if {$pg eq "NULL"} {error "Original S supply missing"}
    $term connect $pg
   }
  }
  set_dont_touch [get_cells $name]
  set_dont_touch [get_nets ${name}_net]
  puts $f "buffer\t$number\t$i\t$name\tBUF_X1\t[$current getName]\t[$next getName]"
  set current $next
 }
 $pin disconnect;$pin connect $current
 if {[issue162_other_pins $inst] ne $saved} {error "Non-target AOI inputs/output or PG changed"}
 if {[llength [$current getITerms]]!=2 || [llength [$current getBTerms]]!=0} {error "S delay chain endpoint connectivity"}
 set expected [lsearch -all -inline -not -exact $terms "[$inst getName]/A"]
 lappend expected issue162_s_reset_${number}_0/A
 set now {};foreach term [$original getITerms] {lappend now "[[$term getInst] getName]/[[$term getMTerm] getName]"}
 set now_ports {};foreach term [$original getBTerms] {lappend now_ports [$term getName]}
 if {[lsort $now] ne [lsort $expected] || [lsort $now_ports] ne [lsort $ports]} {error "Other reset fanout changed"}
 puts $f "verified\t$number\tother_inputs_output_PG_and_fanout_preserved";incr number
}
if {[llength [$block getInsts]]!=$total_before+5*$s_reset_count} {error "Unexpected S cell count change"}
close $f
set_dont_touch [get_nets net175]
global_connect
detailed_placement_helper
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
sta::find_timing
set inserted [list [sta::max_capacitance_violation_count] [sta::max_slew_violation_count] [sta::endpoint_violation_count max] [sta::endpoint_violation_count min]]
set f [open $::env(RESULTS_DIR)/s-reset-inserted-counts.tsv w];puts $f [join $inserted "\t"];close $f
report_checks -path_delay min_max -group_path_count 8 -digits 9 > $::env(RESULTS_DIR)/s-reset-inserted-timing.rpt
report_check_types -max_capacitance -max_slew -violators -digits 9 > $::env(RESULTS_DIR)/s-reset-inserted-electrical.rpt
# A diagnostic checkpoint is never a qualified leaf or a success receipt.
write_db $::env(RESULTS_DIR)/s-reset-inserted-diagnostic.odb
write_sdc -no_timestamp $::env(RESULTS_DIR)/s-reset-inserted-diagnostic.sdc
# Reuse the actual native flow's design/timing repairs after local insertion.
# Final all-endpoint RC/electrical/DRC/function/LEC gates still run separately.
repair_design_helper
global_route -start_incremental
detailed_placement_helper
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
repair_timing_helper
global_route -start_incremental
detailed_placement_helper
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
set number 0
set branch_failed 0
foreach row $s_reset_targets {
 lassign $row name pin_name
 set pin [get_pins [list ${name}/$pin_name]]
 foreach kind {min max} {
  set path $::env(RESULTS_DIR)/s-reset-after-$number-$kind.rpt
  report_checks -from [get_ports reset] -through $pin -path_delay $kind -group_path_count 8 -digits 9 > $path
  set f [open $path r];set text [read $f];close $f
  if {[catch {issue162_met $text} problem]} {puts "S branch $number $kind failed: $problem";set branch_failed 1}
 }
 incr number
}
sta::find_timing
set after [list [sta::max_capacitance_violation_count] [sta::max_slew_violation_count] [sta::endpoint_violation_count max] [sta::endpoint_violation_count min]]
set f [open $::env(RESULTS_DIR)/s-reset-after-counts.tsv w];puts $f [join $after "\t"];close $f
report_checks -path_delay min_max -group_path_count 8 -digits 9 > $::env(RESULTS_DIR)/s-reset-after-timing.rpt
report_check_types -max_capacitance -max_slew -violators -digits 9 > $::env(RESULTS_DIR)/s-reset-after-electrical.rpt
write_db $::env(RESULTS_DIR)/s-reset-final-diagnostic.odb
write_sdc -no_timestamp $::env(RESULTS_DIR)/s-reset-final-diagnostic.sdc
if {$branch_failed} {error "Measured S reset branch final timing failed; diagnostic artifacts retained"}
foreach index {0 1 2} {if {[lindex $after $index]>[lindex $baseline $index]} {error "S reset ECO introduced electrical/setup violation endpoints; diagnostic artifacts retained"}}
write_guides $::env(RESULTS_DIR)/route.guide
