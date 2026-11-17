set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
set out $::env(F_OUT)
set base $::env(F_BASE)
set_thread_count 8
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(F_LIBS) {read_liberty $lib}
read_lef $platform/lef/NangateOpenCellLibrary.tech.lef
read_lef $platform/lef/NangateOpenCellLibrary.macro.mod.lef
foreach lef $::env(F_LEFS) {read_lef $lef}
read_def $base/6_final.def
read_sdc $base/6_final.sdc
read_spef $base/6_final.spef
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
write_db rebuilt-baseline.odb
report_checks -path_delay min -group_path_count 10 -digits 9 > rebuilt-hold-paths.rpt
proc boundary {} {
 set result {}
 foreach b [[ord::get_db_block] getBTerms] {
  foreach p [$b getBPins] {foreach x [$p getBoxes] {lappend result [list [$b getName] [[$x getTechLayer] getName] [$x xMin] [$x yMin] [$x xMax] [$x yMax]]}}
 }
 return [lsort $result]
}
proc macro_positions {} {
 set result {}
 foreach inst [[ord::get_db_block] getInsts] {
  if {[[$inst getMaster] isBlock]} {lappend result [list [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]}
 }
 return [lsort $result]
}
proc net_signature {net} {
 set signature {}
 foreach it [$net getITerms] {set i [$it getInst];lappend signature [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [[$it getMTerm] getName]]}
 foreach b [$net getBTerms] {lappend signature [list BTERM [$b getName]]}
 return [lsort $signature]
}
# DEF encodes source LOCKED cells as FIRM; restore only that known mapping.
set f [open original-instances.tcllist r]
set restored 0
set checked 0
while {[gets $f row] >= 0} {
 lassign $row name master location orient status
 set inst [$block findInst $name]
 if {$inst eq "NULL"} {error "Missing original instance $name"}
 if {[[$inst getMaster] getName] ne $master || [$inst getLocation] ne $location || [$inst getOrient] ne $orient} {error "Instance geometry changed in rebase: $name"}
 if {$status eq "LOCKED" && [$inst getPlacementStatus] eq "FIRM"} {$inst setPlacementStatus LOCKED;incr restored}
 if {[$inst getPlacementStatus] ne $status} {error "Placement status changed in rebase: $name"}
 incr checked
}
close $f
if {$checked != [llength [$block getInsts]]} {error "Rebase instance inventory differs"}
set f [open original-boundary.tcllist r];set original_boundary [string trim [read $f]];close $f
if {[boundary] ne $original_boundary} {error "Original F BPin geometry changed in rebase"}
set f [open original-die.tcllist r];set original_die [string trim [read $f]];close $f
set die [$block getDieArea]
if {[list [$die xMin] [$die yMin] [$die xMax] [$die yMax]] ne $original_die} {error "Original F die changed in rebase"}
puts "F_REBASE_INVENTORY_PASS count=$checked restored_locked=$restored"
set f [open original-nets.tcllist r]
set checked_nets 0
while {[gets $f row] >= 0} {
 lassign $row name kind expected
 set net [$block findNet $name]
 if {$net eq "NULL" || [$net getSigType] ne $kind} {error "Net missing/type changed: $name"}
 set terms {}
 foreach it [$net getITerms] {lappend terms [list I [[$it getInst] getName] [[$it getMTerm] getName]]}
 foreach b [$net getBTerms] {lappend terms [list B [$b getName]]}
 if {[lsort $terms] ne $expected} {error "Net connectivity differs after rebase: $name"}
 incr checked_nets
}
close $f
if {$checked_nets != [llength [$block getNets]]} {error "Rebase net inventory differs"}
puts "F_REBASE_NETS_PASS $checked_nets"
set old_boundary [boundary]
set old_macros [macro_positions]
set original [dict create]
foreach n [$block getNets] {dict set original [$n getName] [net_signature $n]}
if {$::env(F_MODE) eq "probe"} {
 set_routing_layers -signal metal1-metal10 -clock metal1-metal10
 pin_access -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -verbose 1
 write_db pinprobe.odb
 puts F_PIN_ACCESS_PROBE_PASSED
 exit
}
remove_fillers
set_dont_use {TAPCELL_X1 FILLCELL_X1 AOI211_X1 OAI211_X1 OAI221_X4}
foreach i [$block getInsts] {
 if {[[$i getMaster] getName] eq "ANTENNA_X1"} {
  set_dont_touch [get_cells [list [$i getName]]]
  set_dont_touch [get_nets [list [[[$i findITerm A] getNet] getName]]]
 }
}
set_wire_rc -signal -layer metal3
set_wire_rc -clock -layer metal5
repair_timing -hold -hold_margin $::env(F_MARGIN)
detailed_placement
check_placement -verbose
set f [open changed-route-nets.tsv w]
foreach net [$block getNets] {
 if {[$net getSigType] in {POWER GROUND}} {continue}
 set n [$net getName]
 # New S internal metal/cut OBS changes make all attached old route access stale,
 # even when master name, terminal rectangle and parent connectivity are identical.
 set touches_new_s 0
 foreach term [$net getITerms] {
  if {[[[$term getInst] getMaster] getName] eq "local_s_base"} {set touches_new_s 1}
 }
 if {$touches_new_s || ![dict exists $original $n] || [dict get $original $n] ne [net_signature $net]} {
  set wire [$net getWire]
  if {$wire ne "NULL"} {odb::dbWire_destroy $wire}
  puts $f $n
 }
}
close $f
set_routing_layers -signal metal1-metal10 -clock metal1-metal10
set_global_routing_layer_adjustment metal2-metal6 0.20
set_global_routing_layer_adjustment metal7-metal10 0.0
global_route -use_cugr -verbose -congestion_report_file congestion.rpt
source /public/home/yuzelu/project-circuit/issue250-f-native-frame-20261112-18-boot-m10/g-escape-guards.tcl
detailed_route -output_drc route-drc.rpt -output_maze maze.log -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10 -via_access_layer metal10 -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5
source /public/home/yuzelu/project-circuit/issue250-f-native-frame-20261112-18-boot-m10/post-detailed.tcl
filler_placement {FILLCELL_X32 FILLCELL_X16 FILLCELL_X8 FILLCELL_X4 FILLCELL_X2 FILLCELL_X1}
add_global_connection -net VDD -inst_pattern .* -pin_pattern VDD -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern VSS -ground
global_connect
if {[boundary] ne $old_boundary || [macro_positions] ne $old_macros} {error "F interface or macro placement changed"}
write_db candidate.odb
write_def candidate.def
write_verilog candidate.v
write_sdc candidate.sdc
extract_parasitics -ext_model_file $platform/rcx_patterns.rules
write_spef candidate.spef
read_spef candidate.spef
sta::find_timing
set f [open counts.tsv w]
puts $f "setup\t[sta::endpoint_violation_count max]"
puts $f "hold\t[sta::endpoint_violation_count min]"
foreach kind {capacitance slew fanout} {puts $f "$kind\t[sta::max_${kind}_violation_count]"}
close $f
report_worst_slack -max -digits 9 > setup.rpt
report_worst_slack -min -digits 9 > hold.rpt
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 9 > electrical.rpt
check_antennas -report_file antenna.rpt
foreach net {VDD VSS} {if {[check_power_grid -net $net] ne "1"} {error "Incomplete $net"}}
drt::check_drc_cmd native-drc.rpt 0 0 0 0 f_new_s_native
puts F_ECO_CANDIDATE_COMPLETE_NOT_QUALIFIED
