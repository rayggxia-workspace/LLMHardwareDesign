# All preflight evidence comes from the current source's real same-net vias.
set b [ord::get_db_block]
set itr [odb::dbWirePathItr];set path [odb::dbWirePath];set ps [odb::dbWirePathShape]
foreach spec $specs {
 lassign $spec pin net layer x0 y0 x1 y1 x y via_name
 set bt [$b findBTerm $pin]
 if {$bt eq "NULL" || [[$bt getNet] getName] ne $net} {error "Source interface net mismatch"}
 set boxes {};foreach p [$bt getBPins] {foreach z [$p getBoxes] {lappend boxes $z}}
 if {[llength $boxes]!=1} {error "Source pin is not one original rectangle"}
 set z [lindex $boxes 0]
 if {[[$z getTechLayer] getName] ne $layer || [list [$z xMin] [$z yMin] [$z xMax] [$z yMax]] ne [list $x0 $y0 $x1 $y1]} {error "Original layer/rectangle mismatch"}
 set wire [[$bt getNet] getWire];if {$wire eq "NULL"} {error "No original routed wire"}
 set found 0;$itr begin $wire
 while {[$itr getNextPath $path]} {while {[$itr getNextShape $ps]} {
  set shape [odb::dbWirePathShape_shape_get $ps];if {![$shape isVia]} {continue}
  set via [$shape getTechVia];if {$via eq "NULL"} {set via [$shape getVia]}
  if {[$via getName] ne $via_name || [$shape getViaXY] ne [list $x $y]} {continue}
  foreach cap [$via getBoxes] {
   if {[[$cap getTechLayer] getName] eq $layer && [$cap xMin]<=-140 && [$cap yMin]<=-140 && [$cap xMax]>=140 && [$cap yMax]>=140} {set found 1}
  }
 }}
 if {!$found} {error "No exact original same-net via metal containing candidate"}
}
# Only after every selected source pin/owned cap passes native preflight.
foreach spec $specs {
 lassign $spec pin net layer x0 y0 x1 y1 x y via_name
 place_pin -pin_name $pin -layer $layer -location [list [expr {$x/2000.}] [expr {$y/2000.}]] -pin_size {.14 .14}
 set boxes {};foreach p [[$b findBTerm $pin] getBPins] {foreach z [$p getBoxes] {lappend boxes $z}}
 if {[llength $boxes]!=1} {error "Actual pin shape count changed"}
 set z [lindex $boxes 0]
 if {[list [$z xMin] [$z yMin] [$z xMax] [$z yMax]] ne [list [expr {$x-140}] [expr {$y-140}] [expr {$x+140}] [expr {$y+140}]]} {error "Actual pin snapped or clamped"}
}
puts "NATIVE_10261_PIN_XY_ECO_ON_EXISTING_OWN_METAL; ROUTES_RETAINED; REQUIRES_FRESH_FULL_GATES_AND_PARENT_ACCESS"
