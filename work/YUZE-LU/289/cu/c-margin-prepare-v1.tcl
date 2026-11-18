set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db edited.odb
read_sdc $::env(C_ECO_SOURCE_SDC)
set_propagated_clock [all_clocks]
source $platform/setRC.tcl
source $root/geometry.tcl
source $root/c-freeze-outputs-v1.tcl
freeze_selected_c_outputs
set lf [open longwire-placement.tcllist];set longwire_positions [lindex [read $lf] 0];close $lf
set f [open placement-contract.tcllist];lassign [lindex [read $f] 0] original_positions original_statuses movable;close $f
# Only actually resized/moved and newly created cells are movable in this ECO.
foreach i [[ord::get_db_block] getInsts] {
 set name [$i getName]
 if {[dict exists $original_positions $name] && $name ni $movable && ![[$i getMaster] isBlock]} {$i setPlacementStatus LOCKED}
}
foreach name $movable {
 set i [[ord::get_db_block] findInst $name]
 if {$i eq "NULL" || [$i isDoNotTouch] || [[$i getMaster] isBlock]} {error "Resized movable instance is protected $name"}
 $i setPlacementStatus PLACED
}
foreach name [dict keys $longwire_positions] {
 if {$name ni $movable} {[[ord::get_db_block] findInst $name] setPlacementStatus LOCKED}
}
detailed_placement -max_displacement {50 50}
foreach name [dict keys $longwire_positions] {
 set i [[ord::get_db_block] findInst $name]
 if {$name ni $movable && [list [$i getLocation] [$i getOrient]] ne [dict get $longwire_positions $name]} {error "Qualified longwire placement changed $name"}
}
set f [open original-cell-movement.tsv w]
foreach i [[ord::get_db_block] getInsts] {
 set name [$i getName]
 if {![dict exists $original_positions $name]} {continue}
 set before [dict get $original_positions $name];set after [list [$i getLocation] [$i getOrient]]
 if {$before ne $after} {
  if {$name ni $movable} {error "Unrelated original cell moved $name"}
  puts $f "$name\t$before\t$after"
 }
 $i setPlacementStatus [dict get $original_statuses $name]
}
close $f
check_placement -verbose
global_connect
geometry_snapshot geometry-after-legal.tsv
exec cmp geometry-original.tsv geometry-after-legal.tsv
proc net_signature {net} {
 set a {}
 foreach it [$net getITerms] {set i [$it getInst];lappend a [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [[$it getMTerm] getName]]}
 foreach bt [$net getBTerms] {lappend a [list BTERM [$bt getName]]}
 return [lsort $a]
}
set f [open original-signatures.tcllist];set original [lindex [read $f] 0];close $f
set out [open changed-route-nets.tsv w];set nrip 0
foreach n [[ord::get_db_block] getNets] {
 if {[$n getSigType] in {POWER GROUND}} {continue}
 set name [$n getName]
 if {![dict exists $original $name] || [dict get $original $name] ne [net_signature $n]} {
  set wire [$n getWire]
  if {$wire ne "NULL"} {odb::dbWire_destroy $wire;incr nrip}
  puts $out $name
 }
}
close $out
puts EXISTING_MACRO_MASTERS_UNCHANGED_PRESERVE_UNMODIFIED_PORT_ACCESS
if {[info exists ::env(C_EXTRA_RIP_HOOKS)]} {foreach hook $::env(C_EXTRA_RIP_HOOKS) {source $hook}}
set b [ord::get_db_block]
set sit [[$b findInst services.store.leaf] findITerm {req_data[74]}]
if {$sit eq "NULL"} {error "Missing validated S74 AP recovery target"}
set snet [$sit getNet];set sw [$snet getWire]
if {$sw ne "NULL"} {odb::dbWire_destroy $sw}
set af [open targeted-access-rip.tsv w];puts $af [$snet getName];close $af
# Retained macro wires implicated by earlier strict late-AP failures are explicitly restored.
set normalized {}
foreach i [$b getInsts] {dict set normalized [string map [list "\\" ""] [$i getName]] $i}
set af [open additional-known-access-rip.tsv w]
foreach spec {{{services.engine[2].genblk1.recurrent.leaf.leaf} cmd_ready} {{services.engine[0].element.arithmetic.leaf} {in_data[105]}}} {
 lassign $spec inst term
 set it [[dict get $normalized $inst] findITerm $term]
 if {$it eq "NULL"} {error "Known access pin disappeared"}
 set n [$it getNet];set w [$n getWire]
 if {$w ne "NULL"} {odb::dbWire_destroy $w}
 puts $af [$n getName]
}
close $af
set pf [open pre-route-pg.tsv w]
foreach rail {VDD VSS} {set val [check_power_grid -net $rail];puts $pf "$rail\t$val";if {$val ne "1"} {error "Pre-route PG disconnected"}}
close $pf
write_db legalized.odb
write_def legalized.def
write_verilog legalized.v
puts "JOINT_LEGALIZED_AND_RIPPED changed_existing=$nrip"
if {[info exists ::env(C_EDIT_ONLY)] && $::env(C_EDIT_ONLY) eq "1"} {exit}
set_routing_layers -signal metal2-metal10 -clock metal4-metal10
set_global_routing_layer_adjustment metal2-metal10 0.0
global_route -use_cugr -congestion_iterations 3 -verbose -congestion_report_file congestion.rpt
write_guides route.guide
write_db global.odb
pin_access -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -verbose 1
write_db regenerated-ap.odb
puts COMMON_LEGALIZED_GRT_AP_FROZEN_FOR_SIX_ROUTE_SEEDS
