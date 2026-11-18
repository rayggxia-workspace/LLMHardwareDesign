# Stable physical contract: every BPin box, die, and hard macro transform.
proc geometry_snapshot {path} {
 set b [ord::get_db_block]
 set rows {}
 set die [$b getDieArea]
 lappend rows [join [list DIE [$die xMin] [$die yMin] [$die xMax] [$die yMax]] "\t"]
 foreach p [$b getBTerms] {
  foreach bp [$p getBPins] {
   foreach box [$bp getBoxes] {
    lappend rows [join [list PIN [$p getName] [$p getIoType] [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]
   }
  }
 }
 foreach i [$b getInsts] {
  if {![[$i getMaster] isBlock]} {continue}
  lappend rows [join [list MACRO [$i getName] [[$i getMaster] getName] {*}[$i getLocation] [$i getOrient]] "\t"]
  foreach it [$i getITerms] {
   foreach geom [$it getGeometries] {
    lassign $geom layer rect
    if {[$layer getName] ne "metal10"} {continue}
    lappend rows [join [list MACROPIN [$i getName] [[$i getMaster] getName] [[$it getMTerm] getName] [[$it getMTerm] getIoType] [$rect xMin] [$rect yMin] [$rect xMax] [$rect yMax]] "\t"]
   }
  }
 }
 set f [open $path w]
 puts $f [join [lsort $rows] "\n"]
 close $f
 return $rows
}
