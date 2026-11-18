set_thread_count 8
set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(CU_LIBS) {read_liberty $lib}
read_db $::env(C_CLOSE_SOURCE_ODB)
read_sdc $::env(C_ECO_SOURCE_SDC)
source $root/geometry.tcl
source $root/c-freeze-outputs-v1.tcl
freeze_selected_c_outputs
geometry_snapshot geometry-original.tsv
remove_fillers
set b [ord::get_db_block]
proc net_signature {net} {
 set a {}
 foreach it [$net getITerms] {set i [$it getInst];lappend a [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [[$it getMTerm] getName]]}
 foreach bt [$net getBTerms] {lappend a [list BTERM [$bt getName]]}
 return [lsort $a]
}
set signatures {};foreach n [$b getNets] {if {[$n getSigType] ni {POWER GROUND}} {dict set signatures [$n getName] [net_signature $n]}}
set f [open original-signatures.tcllist w];puts $f [list $signatures];close $f
set original_positions {};set original_statuses {};set movable {}
foreach i [$b getInsts] {
 dict set original_positions [$i getName] [list [$i getLocation] [$i getOrient]]
 dict set original_statuses [$i getName] [$i getPlacementStatus]
}
set f [open $::env(C_SIZES_PLAN)];gets $f header
while {[gets $f line]>=0} {
 lassign [split $line "\t"] name old new
 set i [$b findInst $name]
 if {$i eq "NULL" || [[$i getMaster] getName] ne $old || [$i isDoNotTouch] || $new eq "OAI221_X4"} {error "Exact sizing replay mismatch $name"}
 replace_cell $name $new;lappend movable $name
}
close $f
set locked {}
foreach name {i289_idx_mid1 i289_idx_mid2 wire118427 i289_pd_mid i289_cache_mid} {
 set i [$b findInst $name];if {$i eq "NULL"} {error "Missing actual splitter $name"}
 dict set locked $name [list [$i getLocation] [$i getOrient]]
}
set lf [open longwire-placement.tcllist w];puts $lf [list $locked];close $lf
set f [open placement-contract.tcllist w];puts $f [list [list $original_positions $original_statuses $movable]];close $f
geometry_snapshot geometry-after-edit.tsv
exec cmp geometry-original.tsv geometry-after-edit.tsv
write_db edited.odb
write_def edited.def
write_verilog edited.v
puts "ACTUAL_SOURCE_SIZING_ONLY count=[llength $movable]"
puts NO_TOPOLOGY_CLOCK_DIODE_PDN_OR_INTERFACE_CHANGE
