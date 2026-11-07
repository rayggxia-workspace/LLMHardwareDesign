# Add actual same-net M2/M3 metal across narrowly diagnosed gaps. Never delete copper.
read_db $::env(MC_NOTCH_INPUT)
set block [ord::get_db_block]
if {[$block getDbUnitsPerMicron]!=2000} {error "unexpected database units"}
set itr [odb::new_dbWirePathItr]
set path [odb::new_dbWirePath]
set step [odb::new_dbWirePathShape]
set encoder [odb::dbWireEncoder]
set stream [open $::env(MC_NOTCH_PATCHES) r]
while {[gets $stream line]>=0} {
 lassign [split $line "\t"] name layer_name x0 y0 x1 y1
 if {[llength [split $line "\t"]]!=6 || $layer_name ni {metal2 metal3} || !($x0<$x1 && $y0<$y1) || $x1-$x0>320 || $y1-$y0>320} {error "invalid notch patch $line"}
 set net [$block findNet $name]
 if {$net eq "NULL" || [$net getSigType] ni {SIGNAL CLOCK}} {error "invalid signal net $name"}
 set layer [[ord::get_db_tech] findLayer $layer_name]
 set wire [$net getWire]
 if {$wire eq "NULL"} {error "unrouted net $name"}
 set touching 0
 odb::dbWirePathItr_begin $itr $wire
 while {[odb::dbWirePathItr_getNextPath $itr $path]} {
  while {[odb::dbWirePathItr_getNextShape $itr $step]} {
   set shape [odb::dbWirePathShape_shape_get $step]
   if {[odb::dbShape_isSegment $shape]} {
    if {[odb::dbShape_getTechLayer $shape] eq $layer && [odb::dbShape_xMin $shape]<$x1 && [odb::dbShape_xMax $shape]>$x0 && [odb::dbShape_yMin $shape]<$y1 && [odb::dbShape_yMax $shape]>$y0} {incr touching}
   } elseif {[odb::dbShape_isVia $shape]} {
    set via [odb::dbShape_getTechVia $shape]
    if {$via eq "NULL"} {set via [odb::dbShape_getVia $shape]}
    if {$via eq "NULL"} {error "Missing actual via definition"}
    set boxes [$via getBoxes]
    set vx0 2147483647;set vy0 2147483647;set vx1 -2147483647;set vy1 -2147483647
    foreach box $boxes {
     set vx0 [expr {min($vx0,[$box xMin])}];set vy0 [expr {min($vy0,[$box yMin])}]
     set vx1 [expr {max($vx1,[$box xMax])}];set vy1 [expr {max($vy1,[$box yMax])}]
    }
    if {$vx1-$vx0 != [odb::dbShape_xMax $shape]-[odb::dbShape_xMin $shape] || $vy1-$vy0 != [odb::dbShape_yMax $shape]-[odb::dbShape_yMin $shape]} {error "Via geometry/origin mismatch"}
    set dx [expr {[odb::dbShape_xMin $shape]-$vx0}];set dy [expr {[odb::dbShape_yMin $shape]-$vy0}]
    foreach box $boxes {
     if {[$box getTechLayer] eq $layer && [$box xMin]+$dx<$x1 && [$box xMax]+$dx>$x0 && [$box yMin]+$dy<$y1 && [$box yMax]+$dy>$y0} {incr touching}
    }
   }
  }
 }
 if {$touching<2} {error "patch does not touch two real same-net metal shapes: $line ($touching)"}
 # Draw a normal legal-width routed segment through the original gap.
 # Expanded proof boxes are NOT emitted as thin/protruding RECT patches.
 set bx0 [expr {$x0+10}];set by0 [expr {$y0+10}]
 set bx1 [expr {$x1-10}];set by1 [expr {$y1-10}]
 set width [$layer getWidth]
 $encoder append $wire
 $encoder newPath $layer ROUTED
 if {$bx1-$bx0==$width && $by1-$by0<=$width} {
  set x [expr {($bx0+$bx1)/2}]
  $encoder addPoint $x $by0
  $encoder addPoint $x $by1
 } elseif {$by1-$by0==$width && $bx1-$bx0<=$width} {
  set y [expr {($by0+$by1)/2}]
  $encoder addPoint $bx0 $y
  $encoder addPoint $bx1 $y
 } else {error "Gap does not match native routed width: $line width=$width"}
 $encoder end
 puts "MC_NATIVE_NOTCH $line existing_segments=$touching"
}
close $stream
write_db $::env(MC_NOTCH_OUTPUT)
