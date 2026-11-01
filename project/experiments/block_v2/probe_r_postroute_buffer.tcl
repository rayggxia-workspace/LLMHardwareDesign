# Measured single-cell candidate only. Original123 bytes are never overwritten.
# A full final producer, fresh RC and every independent gate are still required.
set_thread_count 16
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
read_db $::env(BV1_ODB)
read_sdc $::env(BV1_SDC)
read_spef $::env(BV1_SPEF)
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
set name place571072
set inst [$block findInst $name]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne "BUF_X4" || [$inst getOrient] ne "R0"} {error "Measured cell identity/orientation changed"}
if {[llength [info commands odb::dbInst_isDoNotTouch]]==1} {set getter isDoNotTouch} else {set getter getDoNotTouch}
if {[$inst $getter]} {error "Protected target"}
set location [$inst getLocation]
set status [$inst getPlacementStatus]
proc pins {inst} {
 set result {}
 foreach t [$inst getITerms] {lappend result [list [[$t getMTerm] getName] [[$t getNet] getName]]}
 return [lsort $result]
}
set connections [pins $inst]
proc measure {prefix} {
 sta::find_timing
 set f [open $prefix-summary.tsv w]
 puts $f "diagnostic_only\ttrue"
 puts $f "native_leaf_accepted\tfalse"
 puts $f "setup_checks\t[sta::endpoint_violation_count max]"
 puts $f "hold_checks\t[sta::endpoint_violation_count min]"
 foreach kind {capacitance slew fanout} {puts $f "$kind\t[sta::max_${kind}_violation_count]"}
 close $f
 report_worst_slack -max -digits 9 > $prefix-timing.rpt
 report_worst_slack -min -digits 9 >> $prefix-timing.rpt
 report_checks -path_delay min_max -through [get_pins place571072/A] -group_path_count 3 -digits 9 -format full_clock_expanded > $prefix-target.rpt
 report_check_types -max_capacitance -max_slew -max_fanout -violators -digits 9 -no_line_splits > $prefix-electrical.rpt
}
measure before
if {[sta::endpoint_violation_count max]!=0 || [sta::endpoint_violation_count min]!=1} {error "Expected exact123 final baseline absent"}
report_checks -path_delay max -through [get_pins place571072/A] -group_path_count 1 -digits 9 > guard-setup.rpt
set f [open guard-setup.rpt];set text [read $f];close $f
if {![regexp {([-+0-9.]+)\s+slack \(MET\)} $text -> slack] || $slack<0.200} {error "Insufficient current setup headroom"}
source $::env(BV1_GEOMETRY_HELPER)
set f [open wire-pin-context.tsv w]
set itr [odb::new_dbWirePathItr]
set path [odb::new_dbWirePath]
set shape [odb::new_dbWirePathShape]
foreach label {A Z} {
 set net [[$inst findITerm $label] getNet]
 if {[$net getSigType] ne "SIGNAL" || [llength [$net getBTerms]]!=0} {error "Unexpected target net scope"}
 set wire [$net getWire];$itr begin $wire
 while {[$itr getNextPath $path]} {while {[$itr getNextShape $shape]} {
  bvgeom::wire_shape $f $label [odb::dbWirePathShape_shape_get $shape]
 }}
}
close $f
odb::delete_dbWirePathShape $shape
odb::delete_dbWirePath $path
odb::delete_dbWirePathItr $itr
write_def before.def
if {[replace_cell [get_cells place571072] CLKBUF_X3]!=1} {error "Equivalent combinational replacement rejected"}
if {[[$inst getMaster] getName] ne "CLKBUF_X3" || [pins $inst] ne $connections || [$inst getLocation] ne $location || [$inst getPlacementStatus] ne $status || [$inst $getter] || [$inst getOrient] ne "R0"} {error "Replacement changed connections/placement/protection"}
measure after
write_def after.def
write_db candidate.odb
set f [open candidate.tsv w]
puts $f "instance\t$name"
puts $f "old_master\tBUF_X4"
puts $f "new_master\tCLKBUF_X3"
puts $f "location_dbu\t$location"
puts $f "connections_location_orientation_protection_preserved\ttrue"
puts $f "native_leaf_accepted\tfalse"
close $f
drt::check_drc_cmd candidate-native-drc.rpt 0 0 0 0 candidate_native_drc
puts SINGLE_BUFFER_CANDIDATE_COMPLETE
