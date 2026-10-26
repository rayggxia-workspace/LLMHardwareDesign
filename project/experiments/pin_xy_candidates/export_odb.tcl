# Read-only database exporter. All writes go to the caller's independent task directory.
set case $::env(PINXY_CASE)
set src $::env(PINXY_ODB)
read_db $src
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set out "data/$case"
file mkdir $out
set ff [open "$out/tech.tsv" w]
puts $ff "layer\ttype\tlevel\twidth\tspacing\tpitchx\tpitchy\tdirection"
foreach l [$tech getLayers] {puts $ff "[$l getName]\t[$l getType]\t[$l getRoutingLevel]\t[$l getWidth]\t[$l getSpacing]\t[$l getPitchX]\t[$l getPitchY]\t[$l getDirection]"}
close $ff
set ff [open "$out/vias.tsv" w]
puts $ff "via\tlayer\tx0\ty0\tx1\ty1"
foreach v [$tech getVias] {foreach s [$v getBoxes] {puts $ff "[$v getName]\t[[$s getTechLayer] getName]\t[$s xMin]\t[$s yMin]\t[$s xMax]\t[$s yMax]"}}
close $ff
set ff [open "$out/endpoints.tsv" w]
puts $ff "pin\tnet_id\tnet\tinst\tmterm\tdirection\tx\ty\tlayers"
set pp [open "$out/bterms.tsv" w]
puts $pp "pin\tnet_id\tnet\tdirection\tlayer\tx0\ty0\tx1\ty1"
foreach bt [$block getBTerms] {
 set net [$bt getNet]
 foreach bp [$bt getBPins] {foreach s [$bp getBoxes] {puts $pp "[$bt getName]\t[$net getId]\t[$net getName]\t[$bt getIoType]\t[[$s getTechLayer] getName]\t[$s xMin]\t[$s yMin]\t[$s xMax]\t[$s yMax]"}}
 if {[$bt getSigType] in {POWER GROUND}} {continue}
 foreach it [$net getITerms] {
  lassign [$it getAvgXY] ok x y
  set layers {}
  foreach g [$it getGeometries] {lappend layers [[lindex $g 0] getName]}
  puts $ff "[$bt getName]\t[$net getId]\t[$net getName]\t[[$it getInst] getName]\t[[$it getMTerm] getName]\t[$it getIoType]\t$x\t$y\t[join [lsort -unique $layers] ,]"
 }
}
close $ff;close $pp
set ff [open "$out/cells.tsv" w]
puts $ff "x0\ty0\tx1\ty1\ttype"
foreach inst [$block getInsts] {set bb [$inst getBBox];puts $ff "[$bb xMin]\t[$bb yMin]\t[$bb xMax]\t[$bb yMax]\t[[$inst getMaster] getType]"}
close $ff
set sf [open "$out/shapes.tsv" w]
puts $sf "layer\tx0\ty0\tx1\ty1\tnet_id\tkind"
proc emit {s net kind {dx 0} {dy 0}} {
 global sf
 set l [$s getTechLayer]
 if {$l eq "NULL"} {return}
 set name [$l getName]
 # Include all routing metal >= M4 and all cut layers. Lower metals are not a proposed access layer.
 if {[$l getRoutingLevel]>0 && [$l getRoutingLevel]<4} {return}
 puts $sf "$name\t[expr {[$s xMin]+$dx}]\t[expr {[$s yMin]+$dy}]\t[expr {[$s xMax]+$dx}]\t[expr {[$s yMax]+$dy}]\t$net\t$kind"
}
proc emitvia {s net kind} {
 set v [$s getTechVia]
 if {$v eq "NULL"} {set v [$s getVia]}
 if {$v eq "NULL"} {error "Unknown via"}
 lassign [$s getViaXY] x y
 foreach box [$v getBoxes] {emit $box $net $kind $x $y}
}
set itr [odb::dbWirePathItr];set path [odb::dbWirePath];set ps [odb::dbWirePathShape]
set count 0
foreach net [$block getNets] {
 set id [$net getId]
 set w [$net getWire]
 if {$w ne "NULL"} {
  $itr begin $w
  while {[$itr getNextPath $path]} {while {[$itr getNextShape $ps]} {
   set s [odb::dbWirePathShape_shape_get $ps]
   if {[$s isVia]} {emitvia $s $id signal_via} else {emit $s $id signal_wire}
  }}
 }
 foreach sw [$net getSWires] {foreach s [$sw getWires] {
  if {[$s isVia]} {
   set v [$s getTechVia];if {$v eq "NULL"} {set v [$s getBlockVia]}
   lassign [$s getViaXY] x y
   foreach box [$v getBoxes] {emit $box $id pg_via $x $y}
  } else {emit $s $id pg_wire}
 }}
 incr count
 if {$count%10000==0} {puts "EXPORTED $case $count nets"}
}
close $sf
puts "EXPORT_COMPLETE $case nets=$count units=[$block getDbUnitsPerMicron]"
