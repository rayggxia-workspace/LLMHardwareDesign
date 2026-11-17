set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CC_LIBS) {read_liberty $lib}
read_db $::env(CC_SEED)/3_place.odb
read_sdc $::env(CC_SEED)/3_place.sdc
source $platform/setRC.tcl
set_thread_count 8
set_dont_use {TAPCELL_X1 FILLCELL_X1 AOI211_X1 OAI211_X1 OAI221_X4}
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/geometry.tcl
geometry_snapshot geometry-before.tsv
estimate_parasitics -placement
report_worst_slack -max -digits 6 > before-slack.rpt
report_checks -path_delay max -group_path_count 30 -format full_clock_expanded -fields {slew cap fanout} -digits 6 > before-paths.rpt
set block [ord::get_db_block]
set size $::env(CC_SIZE)
set used [dict create]
set cl 0
set log [open clusters.tsv w]
puts $log "cluster\tinstance\tmaster"
if {$size > 0} {
  foreach path [find_timing_paths -path_delay max -group_path_count 100 -endpoint_path_count 1 -slack_max 0] {
    set points [get_property $path points]
    set names {}
    set loader 0
    foreach point $points {
      set pin [get_property $point pin]
      foreach cell [get_cells -of_objects $pin] {
        set name [get_full_name $cell]
        if {[string match memory_service.actor2.loader.* $name]} {set loader 1}
        if {$name ni $names} {lappend names $name}
      }
    }
    if {!$loader} {continue}
    set cluster {}
    foreach name $names {
      if {[dict exists $used $name]} {continue}
      set inst [$block findInst $name]
      if {$inst eq "NULL"} {error "Missing timing instance $name"}
      if {[[$inst getMaster] isBlock] || [$inst getPlacementStatus] in {LOCKED FIRM}} {continue}
      dict set used $name 1
      lappend cluster $inst
      puts $log "$cl\t$name\t[[$inst getMaster] getName]"
      if {[llength $cluster] == $size} {
        gpl::placement_cluster_cmd $cluster
        incr cl
        set cluster {}
      }
    }
    if {[llength $cluster] > 1} {gpl::placement_cluster_cmd $cluster; incr cl}
  }
  if {$cl == 0} {error "No actual loader path cluster found"}
}
close $log
puts "ACTUAL_CLUSTERS $cl SELECTED_INSTANCES [dict size $used]"
global_placement -incremental -timing_driven -skip_io -density 0.35 -timing_driven_net_weight_max $::env(CC_WEIGHT)
detailed_placement
estimate_parasitics -placement
repair_design
repair_timing -setup
detailed_placement
check_placement -verbose
estimate_parasitics -placement
report_worst_slack -max -digits 6 > after-slack.rpt
report_checks -path_delay max -group_path_count 30 -format full_clock_expanded -fields {slew cap fanout} -digits 6 > after-paths.rpt
report_check_types -max_slew -max_capacitance -violators > electrical.rpt
geometry_snapshot geometry-after.tsv
set f [open geometry-before.tsv];set before [read $f];close $f
set f [open geometry-after.tsv];set after [read $f];close $f
if {$before ne $after} {error "Geometry changed"}
write_db placed.odb
write_sdc placed.sdc
write_verilog placed.v
puts "CLUSTER_EXPERIMENT_COMPLETE; placement estimate only, not backend acceptance"
