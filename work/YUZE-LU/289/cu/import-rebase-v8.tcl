read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef
foreach lef $::env(CU_REBASE_LEFS) {read_lef $lef}
read_def $::env(CU_REBASE_DIR)/source.def
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/rebase-evidence.tcl
# DEF serializes database LOCKED as FIXED, read back by OpenDB as FIRM.
# Restore source status only after independently checking identity and placement.
set b [ord::get_db_block]
set f [open $::env(CU_REBASE_DIR)/before-instances.tsv]
set restored 0
while {[gets $f line]>=0} {
 lassign [split $line "\t"] name master x y orient status
 set inst [$b findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne $master || [$inst getLocation] ne [list $x $y] || [$inst getOrient] ne $orient} {error "Instance changed during DEF import: $name"}
 if {[$inst getPlacementStatus] ne $status} {
  if {$status ne "LOCKED" || [$inst getPlacementStatus] ne "FIRM"} {error "Unexpected status conversion: $name"}
  $inst setPlacementStatus LOCKED
  incr restored
 }
}
close $f
puts "RESTORED_DEF_LOCKED_STATUS $restored"
rebase_evidence $::env(CU_REBASE_DIR)/after
foreach kind {geometry instances nets} {
 set f [open $::env(CU_REBASE_DIR)/before-${kind}.tsv];set before [read $f];close $f
 set f [open $::env(CU_REBASE_DIR)/after-${kind}.tsv];set after [read $f];close $f
 if {$before ne $after} {error "New G master reconstruction changed $kind"}
}
write_db $::env(CU_REBASE_TARGET)
puts EXACT_GEOMETRY_PLACEMENT_CONNECTIVITY_REBASE_PASSED
