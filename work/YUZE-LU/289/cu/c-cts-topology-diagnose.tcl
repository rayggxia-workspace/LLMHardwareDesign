set_thread_count 8
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $::env(CU_ODB)
read_sdc $::env(CU_SDC)
set_propagated_clock [all_clocks]
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
estimate_parasitics -placement
sta::find_timing
set f [open counts.tsv w]
foreach delay {min max} {puts $f "$delay\t[sta::endpoint_violation_count $delay]"}
close $f
report_worst_slack -min -digits 9 > hold.rpt
report_worst_slack -max -digits 9 > setup.rpt
report_checks -path_delay min -group_path_count 100 -format full_clock_expanded -digits 6 > min-paths.rpt
report_checks -path_delay max -group_path_count 30 -format full_clock_expanded -digits 6 > max-paths.rpt
set b [ord::get_db_block]
set clocks {};set maxfo 0;set nets 0
foreach net [$b getNets] {
 if {[$net getSigType] ne "CLOCK"} {continue}
 incr nets
 set maxfo [expr {max($maxfo,[llength [$net getITerms]])}]
 foreach it [$net getITerms] {
  set i [$it getInst];set m [$i getMaster]
  if {[regexp {^(BUF|CLKBUF|INV)_X} [$m getName]]} {dict set clocks [$i getName] $m}
 }
}
set area 0
set f [open clock-cells.tsv w]
dict for {name m} $clocks {set area [expr {$area+double([$m getWidth])*[$m getHeight]/4000000}];puts $f "$name\t[$m getName]"}
close $f
set f [open clock-metrics.tsv w];puts $f "clock_nets\t$nets\nclock_buffers\t[dict size $clocks]\nclock_area_um2\t$area\nmax_clock_fanout\t$maxfo\nall_instances\t[llength [$b getInsts]]";close $f
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/geometry.tcl
geometry_snapshot geometry.tsv
puts CTS_TOPOLOGY_DIAGNOSTIC_ONLY_NO_GENERIC_HOLD_REPAIR