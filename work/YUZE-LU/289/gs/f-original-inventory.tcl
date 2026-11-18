read_db $::env(F_BASE)/6_final.odb
set block [ord::get_db_block]
set f [open original-instances.tcllist w]
foreach i [$block getInsts] {puts $f [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus]]}
close $f
set result {}
foreach b [$block getBTerms] {
 foreach p [$b getBPins] {foreach x [$p getBoxes] {lappend result [list [$b getName] [[$x getTechLayer] getName] [$x xMin] [$x yMin] [$x xMax] [$x yMax]]}}
}
set f [open original-boundary.tcllist w];puts $f [lsort $result];close $f
set die [$block getDieArea]
set f [open original-die.tcllist w];puts $f [list [$die xMin] [$die yMin] [$die xMax] [$die yMax]];close $f
set f [open original-nets.tcllist w]
foreach net [$block getNets] {
 set terms {}
 foreach it [$net getITerms] {lappend terms [list I [[$it getInst] getName] [[$it getMTerm] getName]]}
 foreach b [$net getBTerms] {lappend terms [list B [$b getName]]}
 puts $f [list [$net getName] [$net getSigType] [lsort $terms]]
}
close $f