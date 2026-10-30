# Exact native old BPin material becomes same-net dbWire, not deleted metal.
set b [ord::get_db_block];set tech [ord::get_db_tech]
set itr [odb::dbWirePathItr];set path [odb::dbWirePath];set ps [odb::dbWirePathShape]
foreach spec $specs {
 lassign $spec pin net layer x0 y0 x1 y1 x y retain
 set bt [$b findBTerm $pin]
 if {$bt eq "NULL" || [[$bt getNet] getName] ne $net} {error "Actual interface net mismatch"}
 set boxes {};foreach p [$bt getBPins] {foreach z [$p getBoxes] {lappend boxes $z}}
 if {[llength $boxes]!=1} {error "Original BPin rectangle count differs"}
 set z [lindex $boxes 0]
 if {[[$z getTechLayer] getName] ne $layer || [list [$z xMin] [$z yMin] [$z xMax] [$z yMax]] ne [list $x0 $y0 $x1 $y1]} {error "Current actual BPin rectangle differs"}
 set ly [$tech findLayer $layer]
 if {$layer ni {metal5 metal6} || [$ly getWidth]!=280 || $x1-$x0!=280 || $y1-$y0!=280} {error "Original width/layer contract differs"}
 set wire [[$bt getNet] getWire];if {$wire eq "NULL"} {error "Original route missing"}
 set found 0;$itr begin $wire
 while {[$itr getNextPath $path]} {while {[$itr getNextShape $ps]} {
  set shape [odb::dbWirePathShape_shape_get $ps]
  if {[$shape isVia] || [[$shape getTechLayer] getName] ne $layer} {continue}
  if {[$shape xMin]<=$x-140 && [$shape yMin]<=$y-140 && [$shape xMax]>=$x+140 && [$shape yMax]>=$y+140} {set found 1}
 }}
 if {!$found} {error "New BPin is not fully in current actual own WIRE"}
}
foreach spec $specs {
 lassign $spec pin net layer x0 y0 x1 y1 x y retain
 set bt [$b findBTerm $pin];set n [$bt getNet];set ly [$tech findLayer $layer]
 if {$retain} {
  if {[$b findNet HPY_EXACT_PIN_RETAIN_STAGING] ne "NULL"} {error "Temporary staging name exists"}
  set tmp [odb::dbNet_create $b HPY_EXACT_PIN_RETAIN_STAGING];set tw [odb::dbWire_create $tmp]
  set enc [odb::dbWireEncoder];$enc begin $tw;$enc newPath $ly ROUTED
  # Explicit zero endpoint extensions avoid relying on zero-length paths.
  if {$layer eq "metal5"} {set cy [expr {($y0+$y1)/2}];$enc addPoint $x0 $cy 0;$enc addPoint $x1 $cy 0} else {set cx [expr {($x0+$x1)/2}];$enc addPoint $cx $y0 0;$enc addPoint $cx $y1 0}
  $enc end;[$n getWire] append $tw;odb::dbNet_destroy $tmp
 }
 place_pin -pin_name $pin -layer $layer -location [list [expr {$x/2000.}] [expr {$y/2000.}]] -pin_size {.14 .14}
 set boxes {};foreach p [$bt getBPins] {foreach z [$p getBoxes] {lappend boxes $z}}
 if {[llength $boxes]!=1} {error "New BPin is not one rectangle"};set z [lindex $boxes 0]
 if {[list [$z xMin] [$z yMin] [$z xMax] [$z yMax]] ne [list [expr {$x-140}] [expr {$y-140}] [expr {$x+140}] [expr {$y+140}]]} {error "New point clamped or snapped"}
}
puts NATIVE_2832_WIRE_ACCESS_POINTS_WITH_EXACT_2827_OLD_PIN_METAL_RETAINED_REQUIRES_FULL_GATES
