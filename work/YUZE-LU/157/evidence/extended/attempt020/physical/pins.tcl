# Deterministic same geometry and M10 pin template for independent trials.
set block [ord::get_db_block]
set names {}
foreach term [$block getBTerms] {if {[$term getSigType] != "POWER" && [$term getSigType] != "GROUND"} {lappend names [$term getName]}}
set i 0
foreach name [lsort $names] {
 set edge [expr {$i % 4}]
 set position [expr {160.0+4.0*int($i/4)}]
 set inner [expr {24.0+4.0*(int($i/4)%2)}]
 switch $edge {
  0 {set xy [list $inner $position]}
  1 {set xy [list [expr {3000.0-$inner}] $position]}
  2 {set xy [list $position $inner]}
  3 {set xy [list $position [expr {3000.0-$inner}]]}
 }
 place_pin -pin_name $name -layer metal10 -location $xy -pin_size {2.0 2.0}
 incr i
}
