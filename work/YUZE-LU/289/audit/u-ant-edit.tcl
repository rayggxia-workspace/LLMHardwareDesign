set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
read_db $root/u-physical/candidate-guard-v1/guarded-before-route.odb
set block [ord::get_db_block]
source $root/cu/geometry.tcl
geometry_snapshot $::env(U_RESULTS)/geometry-before.tsv
proc net_signature {net} {
 set result {}
 foreach it [$net getITerms] {set i [$it getInst];lappend result [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [[$it getMTerm] getName]]}
 foreach b [$net getBTerms] {lappend result [list BTERM [$b getName]]}
 return [lsort $result]
}
set original [dict create]
foreach net [$block getNets] {dict set original [$net getName] [net_signature $net]}
set f [open original-net-signatures.tcllist w];puts $f [list $original];close $f
source insert-diodes-v1.tcl
write_db antenna-edit.odb
puts ANTENNA_EDIT_WRITTEN_FRESH_PROCESS_REQUIRED
