proc c_ant_original_state {path pkg exclude_new} {
 source $pkg/plan.tcl
 set excluded [dict create]
 if {$exclude_new} {foreach spec $c_ant_plan {dict set excluded [lindex $spec 2] 1}}
 set rows {}
 foreach i [[ord::get_db_block] getInsts] {
  if {[dict exists $excluded [$i getName]]} {continue}
  lappend rows [join [list INST [$i getName] [[$i getMaster] getName] {*}[$i getLocation] [$i getOrient] [$i getPlacementStatus]] "\t"]
  foreach it [$i getITerms] {
   set net [$it getNet];set name NULL;if {$net ne "NULL"} {set name [$net getName]}
   lappend rows [join [list TERM [$i getName] [[$it getMTerm] getName] $name] "\t"]
  }
 }
 set f [open $path w];puts $f [join [lsort $rows] "\n"];close $f
}
