proc rebase_evidence {prefix} {
 set b [ord::get_db_block]
 source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/geometry.tcl
 geometry_snapshot ${prefix}-geometry.tsv
 set rows {}
 foreach inst [$b getInsts] {
  lappend rows [join [list [$inst getName] [[$inst getMaster] getName] {*}[$inst getLocation] [$inst getOrient] [$inst getPlacementStatus]] "\t"]
 }
 set f [open ${prefix}-instances.tsv w];puts $f [join [lsort $rows] "\n"];close $f
 set rows {}
 foreach net [$b getNets] {
  set terms {}
  foreach port [$net getBTerms] {lappend terms "PORT:[$port getName]"}
  foreach it [$net getITerms] {lappend terms "INST:[[$it getInst] getName]/[[$it getMTerm] getName]"}
  lappend rows [join [list [$net getName] [$net getSigType] {*}[lsort $terms]] "\t"]
 }
 set f [open ${prefix}-nets.tsv w];puts $f [join [lsort $rows] "\n"];close $f
}
