set_thread_count 8
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $::env(CU_SOURCE_ODB)
read_sdc $::env(CU_SOURCE_SDC)
source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/geometry.tcl
geometry_snapshot geometry-before.tsv
set b [ord::get_db_block]
set core [$b getCoreArea]
set corearea [expr {double([$core xMax]-[$core xMin])*([$core yMax]-[$core yMin])}]
set macroarea 0;set stdarea 0;set statuses {};set original {}
foreach i [$b getInsts] {
 set m [$i getMaster]
 set area [expr {double([$m getWidth])*[$m getHeight]}]
 if {[$m isBlock]} {set macroarea [expr {$macroarea+$area}]} else {set stdarea [expr {$stdarea+$area}];dict incr statuses [$i getPlacementStatus]}
 dict set original [$i getName] [$i getLocation]
}
set f [open area-and-mobility.tsv w]
puts $f "core_dbu2\t$corearea\nmacro_dbu2\t$macroarea\nstd_dbu2\t$stdarea\nstd_fraction_of_nonmacro_core\t[expr {$stdarea/($corearea-$macroarea)}]\nstatuses\t$statuses"
close $f
estimate_parasitics -placement
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/pre-global-v3.tcl
set_routing_layers -signal metal2-metal10 -clock metal4-metal10
set_global_routing_layer_adjustment metal2-metal10 0.0
estimate_parasitics -placement
set args [list -skip_initial_place -density 0.40 -routability_driven -timing_driven -routability_inflation_ratio_coef $::env(CU_INFLATION) -routability_max_inflation_ratio 3 -timing_driven_net_weight_max $::env(CU_WEIGHT)]
if {$::env(CU_METHOD) eq "grt"} {lappend args -routability_use_grt}
puts "PLACEMENT_STUDY_ARGUMENTS $args"
global_placement {*}$args
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/pre-global-v3.tcl
detailed_placement
check_placement -verbose
set changed 0
foreach i [$b getInsts] {if {[dict exists $original [$i getName]] && [dict get $original [$i getName]] ne [$i getLocation]} {incr changed}}
if {$changed==0} {error "Placement no-op; no movable cells changed"}
puts "ACTUALLY_MOVED_INSTANCES $changed"
geometry_snapshot geometry-after.tsv
exec cmp geometry-before.tsv geometry-after.tsv
estimate_parasitics -placement
report_worst_slack -max -digits 9 > estimated-setup.rpt
report_checks -path_delay max -group_path_count 10 -format full_clock_expanded > placement-paths.rpt
write_db placed.odb
write_sdc placed.sdc
write_verilog placed.v
puts ROUTABILITY_PLACEMENT_ONLY_REQUIRES_NEW_CTS_AND_FULL_BACKEND
global_route -use_cugr -congestion_iterations 3 -verbose -congestion_report_file congestion.rpt
write_guides route.guide
write_db global-candidate.odb
estimate_parasitics -global_routing
report_worst_slack -max -digits 9 > global-setup.rpt
puts GRT_PLACEMENT_COMPARISON_COMPLETE_NOT_SIGNOFF
