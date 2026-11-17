read_db $::env(C_OBS_ODB)
set db [ord::get_db]
set tech [$db getTech]
set b [ord::get_db_block]
set units [$tech getDbUnitsPerMicron]
set f [open macro-instances.tsv w]
set masters [dict create]
foreach i [$b getInsts] {
 set m [$i getMaster]
 if {![$m isBlock]} {continue}
 set name [$m getName]
 if {![regexp {^[A-Za-z0-9_]+$} $name]} {error "Unsafe master filename $name"}
 dict set masters $name $m
 puts $f [join [list [$i getName] $name {*}[$i getLocation] [$i getOrient]] "\t"]
}
close $f
foreach name [lsort [dict keys $masters]] {
 set m [dict get $masters $name]
 set f [open "$name.tsv" w]
 puts $f "UNITS\t$units"
 puts $f "MASTER\t$name\t[$m getWidth]\t[$m getHeight]"
 if {[catch {$m getOrigin} origin]} {set origin UNKNOWN}
 puts $f "ORIGIN\t$origin"
 foreach box [$m getObstructions] {
  set layer [$box getTechLayer]
  if {$layer eq "NULL"} {error "Non-layer obstruction requires explicit decoding: $name"}
  puts $f [join [list OBS [$layer getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\t"]
 }
 close $f
}
puts C_INSTALLED_HARDMACRO_OBS_EXPORTED
