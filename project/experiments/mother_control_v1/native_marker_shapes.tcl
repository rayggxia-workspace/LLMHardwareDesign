# Read-only: export real same-net routed metal covering each fresh marker.
set block [ord::get_db_block]
if {[$block getDbUnitsPerMicron]!=2000} {error "Unexpected native database units"}
set itr [odb::new_dbWirePathItr]
set path [odb::new_dbWirePath]
set step [odb::new_dbWirePathShape]
set input [open marker-input.tsv r]
set output [open marker-shapes.tsv w]
while {[gets $input row]>=0} {
 lassign [split $row "\t"] index name layer_name x0 y0 x1 y1
 if {[llength [split $row "\t"]]!=7 || $layer_name ni {metal2 metal3}} {error "Unsupported fresh marker"}
 set net [$block findNet $name]
 if {$net eq "NULL" || [$net getSigType] ni {SIGNAL CLOCK}} {error "Missing original marker net: $name"}
 set wire [$net getWire]
 if {$wire eq "NULL"} {error "Original marker net has no wire"}
 set layer [[ord::get_db_tech] findLayer $layer_name]
 odb::dbWirePathItr_begin $itr $wire
 while {[odb::dbWirePathItr_getNextPath $itr $path]} {
  while {[odb::dbWirePathItr_getNextShape $itr $step]} {
   set shape [odb::dbWirePathShape_shape_get $step]
   if {![odb::dbShape_isSegment $shape] || [odb::dbShape_getTechLayer $shape] ne $layer} {continue}
   set ax [expr {max($x0,[odb::dbShape_xMin $shape])}]
   set ay [expr {max($y0,[odb::dbShape_yMin $shape])}]
   set bx [expr {min($x1,[odb::dbShape_xMax $shape])}]
   set by [expr {min($y1,[odb::dbShape_yMax $shape])}]
   if {$ax<$bx && $ay<$by} {puts $output "$index\t$ax\t$ay\t$bx\t$by"}
  }
 }
}
close $input
close $output
