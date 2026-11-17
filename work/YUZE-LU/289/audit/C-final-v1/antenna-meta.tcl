read_db $::env(C_ANT_RES)/6_final.odb
set b [ord::get_db_block]
set f [open design-name.txt w];puts $f [$b getName];close $f
set tech [[ord::get_db] getTech]
set f [open dbu.txt w];puts $f [$tech getDbUnitsPerMicron];close $f
set f [open layers.tsv w]
foreach l [$tech getLayers] {puts $f "[$l getName]\t[$l getWidth]"};close $f
set f [open vias.tsv w]
foreach v [concat [$tech getVias] [$b getVias]] {
 foreach box [$v getBoxes] {puts $f "[$v getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"}
};close $f
set f [open bpins.tsv w]
foreach bt [$b getBTerms] {foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {puts $f [join [list [$bt getName] [[$bt getNet] getName] [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]}}};close $f
set f [open endpoints.tsv w]
foreach net [$b getNets] {
 if {[$net getSigType] in {POWER GROUND}} {continue}
 foreach it [$net getITerms] {
  set i [$it getInst];set m [$i getMaster];set p [$it getMTerm]
  puts $f [join [list [$net getName] [$i getName] [$m getName] [$p getName] [$p getIoType] {*}[$i getLocation] [$i getOrient] [$m getWidth] [$m getHeight]] "\t"]
 }
};close $f
write_def odb-readback.def
