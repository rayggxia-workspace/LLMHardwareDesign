# Read-only bounded hierarchy/ownership evidence, not a DRC waiver.
read_db $::env(PINXY_AUDIT_ODB)
set b [ord::get_db_block]
set window $::env(PINXY_AUDIT_BOX)
set target $::env(PINXY_AUDIT_PIN)
set bt [$b findBTerm $target]
if {$bt eq "NULL"} {error "Actual source interface pin missing"}
set selected_net [[$bt getNet] getName]
set f [open $::env(PINXY_AUDIT_OUT) w]
puts $f "net\trole\tlayer\tx0\ty0\tx1\ty1\tkind\towner\tlink"
proc emit_region {nn layer box kind owner link} {
 global f window selected_net
 lassign $window a c d e;lassign $box x0 y0 x1 y1
 if {$x0>$d || $x1<$a || $y0>$e || $y1<$c} {return}
 set role [expr {$nn eq $selected_net ? "SELECTED_INTERFACE_NET" : ($nn in {VDD VSS} ? "PG" : "OTHER_OR_UNOWNED")}]
 puts $f [join [list $nn $role $layer $x0 $y0 $x1 $y1 $kind $owner $link] "\t"]
}
proc emit_box {nn box kind owner link {dx 0} {dy 0}} {
 emit_region $nn [[$box getTechLayer] getName] [list [expr {[$box xMin]+$dx}] [expr {[$box yMin]+$dy}] [expr {[$box xMax]+$dx}] [expr {[$box yMax]+$dy}]] $kind $owner $link
}
set itr [odb::dbWirePathItr];set path [odb::dbWirePath];set ps [odb::dbWirePathShape]
foreach n [$b getNets] {
 set nn [$n getName];set wire [$n getWire];set serial 0
 if {$wire ne "NULL"} {
  $itr begin $wire
  while {[$itr getNextPath $path]} {while {[$itr getNextShape $ps]} {
   incr serial;set s [odb::dbWirePathShape_shape_get $ps]
   if {[$s isVia]} {
    set v [$s getTechVia];if {$v eq "NULL"} {set v [$s getVia]};lassign [$s getViaXY] x y
    foreach box [$v getBoxes] {emit_box $nn $box VIA {} "via_$serial" $x $y}
   } else {emit_box $nn $s WIRE {} "wire_$serial"}
  }}
 }
 foreach sw [$n getSWires] {foreach s [$sw getWires] {
  incr serial
  if {[$s isVia]} {
   set v [$s getTechVia];if {$v eq "NULL"} {set v [$s getBlockVia]};lassign [$s getViaXY] x y
   foreach box [$v getBoxes] {emit_box $nn $box PG_VIA {} "pgvia_$serial" $x $y}
  } else {emit_box $nn $s PG_WIRE {} "pgwire_$serial"}
 }}
}
foreach bt [$b getBTerms] {foreach pin [$bt getBPins] {foreach box [$pin getBoxes] {emit_box [[$bt getNet] getName] $box BTERM [$bt getName] "B:[$bt getName]"}}}
foreach i [$b getInsts] {
 set bb [$i getBBox];lassign $window a c d e
 if {[$bb xMin]>$d || [$bb xMax]<$a || [$bb yMin]>$e || [$bb yMax]<$c} {continue}
 foreach it [$i getITerms] {
  set n [$it getNet];if {$n eq "NULL"} {set nn NULL} else {set nn [$n getName]}
  foreach g [$it getGeometries] {set ly [lindex $g 0];set r [lindex $g 1];emit_region $nn [$ly getName] [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]] ITERM [$i getName] "I:[$i getName]/[[$it getMTerm] getName]"}
 }
 lassign [[$i getMaster] getOrigin] ox oy
 if {[$i getOrient] eq "R0" && $ox==0 && $oy==0} {
  lassign [$i getLocation] dx dy
  foreach ob [[$i getMaster] getObstructions] {emit_box UNOWNED_ABSTRACT_OBS $ob MACRO_OBS [$i getName] {} $dx $dy}
 } elseif {[llength [[$i getMaster] getObstructions]]} {
  emit_region UNCHECKED_MACRO_TRANSFORM UNKNOWN [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]] UNCHECKED_MACRO_TRANSFORM [$i getName] [$i getOrient]
 }
}
foreach ob [$b getObstructions] {emit_box UNOWNED_BLOCK_OBS [$ob getBBox] BLOCK_OBS {} {}}
close $f
puts "BOUNDED_ACTUAL_METAL_PG_PIN_AND_OBS_EXPORT; original geometry untouched; not DRC pass"
