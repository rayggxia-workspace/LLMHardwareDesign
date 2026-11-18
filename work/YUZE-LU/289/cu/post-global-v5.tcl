# Keep normal internal buffer choices; enforce only selected output strength.
set b [ord::get_db_block]
set kind [dict get [dict create cfj_group_c_memory_legacy C u_n32_controlled_dma_64 U] [$b getName]]
set f [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/$kind-outputs.txt]
set changes {}
set audit [open $::env(RESULTS_DIR)/post-repair-drivers.tsv w]
puts $audit "port\tinstance\tmaster"
while {[gets $f p] >= 0} {
 set p [string trim $p];if {$p eq ""} {continue}
 set term [$b findBTerm $p]
 set drivers {}
 foreach it [[$term getNet] getITerms] {
  if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend drivers [$it getInst]}
 }
 if {[llength $drivers]!=1} {error "Selected output driver ambiguity $p"}
 set inst [lindex $drivers 0]
 set name [[$inst getMaster] getName]
 puts $audit "$p\t[$inst getName]\t$name"
 if {[string match *-baseline-* $::env(RESULTS_DIR)]} {continue}
 if {![regexp {^(BUF|INV|CLKBUF)_X([0-9]+)$} $name -> family strength]} {error "Unproven selected output logic $p $name"}
 if {$strength<8} {lappend changes [list [$inst getName] ${family}_X8]}
}
close $f
close $audit
set counts {}
foreach i [$b getInsts] {
 if {[string match hold* [$i getName]]} {dict incr counts [[$i getMaster] getName]}
}
set f [open $::env(RESULTS_DIR)/hold-buffer-cells.tsv w]
dict for {name count} $counts {puts $f "$name\t$count"}
close $f
if {[llength $changes]} {
 global_route -start_incremental
 foreach change $changes {lassign $change name new; replace_cell $name $new}
 detailed_placement
 check_placement -verbose
 set args {}
 if {[lsearch -exact $::env(GLOBAL_ROUTE_ARGS) -allow_congestion]>=0} {lappend args -allow_congestion}
 if {[lsearch -exact $::env(GLOBAL_ROUTE_ARGS) -use_cugr]>=0} {lappend args -use_cugr}
 global_route -end_incremental {*}$args
 estimate_parasitics -global_routing
 write_guides $::env(RESULTS_DIR)/route.guide
}
report_worst_slack -max -digits 6 > $::env(REPORTS_DIR)/selected-x8-final-est-setup.rpt
report_worst_slack -min -digits 6 > $::env(REPORTS_DIR)/selected-x8-final-est-hold.rpt
puts "SELECTED_OUTPUT_RESIZES_AFTER_REPAIR [llength $changes]"
