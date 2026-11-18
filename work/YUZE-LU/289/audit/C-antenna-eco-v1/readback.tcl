set pkg $::env(C_ANT_ECO_PACKAGE)
read_db candidate.odb
source $pkg/structural-state.tcl
source $pkg/geometry-all.tcl
source $pkg/plan.tcl
c_ant_original_state original-readback.tsv $pkg 1
exec cmp original-before.tsv original-readback.tsv
geometry_snapshot interface-readback.tsv
exec cmp antenna-interface-before.tsv interface-readback.tsv
set block [ord::get_db_block]
set f [open diode-readback.tsv w]
foreach spec $c_ant_plan {
 lassign $spec netname ports name
 set i [$block findInst $name];set net [$block findNet $netname]
 if {$i eq "NULL" || [[$i getMaster] getName] ne "ANTENNA_X1" || [[$i findITerm A] getNet] ne $net} {error "Readback diode binding mismatch $name"}
 foreach p $ports {set bt [$block findBTerm $p];if {$bt eq "NULL" || [$bt getIoType] ne "INPUT" || [$bt getNet] ne $net} {error "Readback INPUT mapping mismatch"}}
 foreach rail {VDD VSS} {if {[[$i findITerm $rail] getNet] ne [$block findNet $rail]} {error "Readback diode PG topology mismatch"}}
 puts $f [join [list $name $netname [[$i getMaster] getName] {*}[$i getLocation] [$i getOrient]] "\t"]
}
close $f
puts C_ANTENNA_FRESH_DB_READBACK_PASS_NOT_PHYSICAL_SIGNOFF
