# Read the immutable #206 native database. Write only to this job's new folder.
read_db $::env(COUPLING_NATIVE_ODB)
set block [ord::get_db_block]
set out $::env(COUPLING_NATIVE_OUT)
set summary [open $out/inventory.tsv w]
puts $summary "block\t[$block getName]"
puts $summary "dbu_per_um\t[$block getDbUnitsPerMicron]"
puts $summary "net_count\t[llength [$block getNets]]"
puts $summary "instance_count\t[llength [$block getInsts]]"
set masters [dict create]
foreach inst [$block getInsts] {
  set master [$inst getMaster]
  dict incr masters [list [$master getName] [$master getType]]
}
dict for {master count} $masters {puts $summary "master\t[join $master \t]\t$count"}
foreach layer [[ord::get_db_tech] getLayers] {
  puts $summary "layer\t[$layer getName]\t[$layer getType]\t[$layer getRoutingLevel]"
}
set ports [open $out/ports.tsv w]
foreach term [$block getBTerms] {
  set net [$term getNet]
  puts $ports "[binary encode hex [encoding convertto utf-8 [$term getName]]]\t[binary encode hex [encoding convertto utf-8 [$net getName]]]\t[$term getIoType]\t[$net getSigType]"
}
close $ports
close $summary
# OBS are routing keepouts. They must never be exported as real metal.
source $::env(COUPLING_GEOMETRY_TCL)
rename bvgeom::rectangle bvgeom::original_rectangle
set ::coupling_layers [dict create]
proc bvgeom::rectangle {stream net layer kind object {dx 0} {dy 0} {transform ""}} {
  if {[$layer getType] ni {ROUTING CUT}} {return}
  dict incr ::coupling_layers [list [$layer getName] $kind]
  original_rectangle $stream $net $layer $kind $object $dx $dy $transform
}
bvgeom::export $out/conductors.tsv
set counts [open $out/shapes.tsv w]
dict for {key count} $::coupling_layers {puts $counts "[join $key \t]\t$count"}
close $counts
puts "NATIVE_SNAPSHOT_COMPLETE"
