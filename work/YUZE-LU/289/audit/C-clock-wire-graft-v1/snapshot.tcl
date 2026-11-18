# Read-only metadata. Caller supplies CLOCK_ODB and CLOCK_META; no writes to source DB.
read_db $::env(CLOCK_ODB)
set b [ord::get_db_block];set tech [[ord::get_db] getTech]
set n [$b findNet net73798]
if {$n eq "NULL" || [$n getSigType] ne "CLOCK" || [llength [$n getBTerms]]} {error "Clock net contract"}
set rows {}
foreach it [$n getITerms] {
 set inst [$it getInst];set mt [$it getMTerm]
 lappend rows [join [list ENDPOINT [$inst getName] [[$inst getMaster] getName] [$mt getName] [$mt getIoType] {*}[$inst getLocation] [$inst getOrient]] "\t"]
 foreach geom [$it getGeometries] {lassign $geom l box;lappend rows [join [list PIN [$inst getName] [$mt getName] [$l getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]}
}
set f [open $::env(CLOCK_META)/endpoints.tsv w];puts $f [join [lsort $rows] "\n"];close $f
set f [open $::env(CLOCK_META)/layers.tsv w];foreach l [$tech getLayers] {puts $f "[$l getName]\t[$l getWidth]"};close $f
set f [open $::env(CLOCK_META)/vias.tsv w]
foreach v [concat [$tech getVias] [$b getVias]] {foreach x [$v getBoxes] {puts $f [join [list [$v getName] [[$x getTechLayer] getName] [$x xMin] [$x yMin] [$x xMax] [$x yMax]] "\t"]}}
close $f
write_def $::env(CLOCK_META)/readback.def
