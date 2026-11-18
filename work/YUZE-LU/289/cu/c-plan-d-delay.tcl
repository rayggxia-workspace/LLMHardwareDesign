set_thread_count 8
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db unshared.odb
read_sdc $::env(CU_SEED)/4_cts.sdc
set_propagated_clock [all_clocks]
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
estimate_parasitics -placement
set budget [open delay-budget.tsv w]
set plan [open delay-plan.tcl w]
puts $plan "set delay_plan \{"
set records {}
foreach path [find_timing_paths -path_delay min -slack_max 0 -group_path_count 10000 -endpoint_path_count 1] {
 lappend records [list [get_property $path endpoint] [get_property $path slack]]
}
set seen [dict create]
foreach record $records {
 lassign $record pin h
 set name [get_full_name $pin]
 if {[dict exists $seen $name]} {continue}
 dict set seen $name 1
 set maxp [find_timing_paths -to $pin -path_delay max -group_path_count 1]
 if {[llength $maxp]!=1} {error "No setup budget $name"}
 set s [get_property [lindex $maxp 0] slack]
 set n [expr {int(ceil((-$h+$::env(CU_HOLD_MARGIN))/$::env(CU_CELL_DELAY)))}]
 set cap [expr {int(floor(($s-0.01)/0.04))}]
 set chosen [expr {max(0,min($n,$cap))}]
 puts $budget "$name\t$h\t$s\t$n\t$cap\t$chosen"
 if {$chosen>0} {puts $plan [list [list $name $chosen]]}
}
puts $plan \}
close $budget
close $plan
report_checks -path_delay max -group_path_count 10 -format full_clock_expanded > unshared-setup.rpt