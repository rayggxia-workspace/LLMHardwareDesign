set_thread_count 8
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base/6_final.odb
set b [ord::get_db_block]
set it [odb::dbWireShapeItr]
set shape [odb::dbShape]
set f [open local-wire-shapes.tsv w]
puts $f "net\tlayer\tvia\tx1\ty1\tx2\ty2"
foreach net [$b getNets] {
 set wire [$net getWire]
 if {$wire eq "NULL"} {continue}
 $it begin $wire
 while {[$it next $shape]} {
  set box [$shape getBox]
  if {[$box xMax]<2782000 || [$box xMin]>2792000 || [$box yMax]<1156000 || [$box yMin]>1166000} {continue}
  set layer [$shape getTechLayer]
  set lname VIA
  if {$layer ne "NULL"} {set lname [$layer getName]}
  puts $f "[$net getName]\t$lname\t[$shape isVia]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
 }
}
close $f
set f [open nearby-terminals.tsv w]
foreach i [$b getInsts] {
 if {![[$i getMaster] isBlock]} {continue}
 set orient [$i getOrient]
 lassign [$i getOrigin] ox oy
 foreach it [$i getITerms] {
  foreach mp [[$it getMTerm] getMPins] {foreach box [$mp getGeometry] {
   set layer [$box getTechLayer]
   if {$layer eq "NULL" || [$layer getName] ne "metal10"} {continue}
   if {$orient ne "R0"} {continue}
   set x1 [expr {$ox+[$box xMin]}];set y1 [expr {$oy+[$box yMin]}]
   set x2 [expr {$ox+[$box xMax]}];set y2 [expr {$oy+[$box yMax]}]
   if {$x2<2782000 || $x1>2792000 || $y2<1156000 || $y1>1166000} {continue}
   puts $f "[$i getName]/[[$it getMTerm] getName]\t[[$it getNet] getName]\t$x1\t$y1\t$x2\t$y2"
  }}
 }
}
close $f
puts MAIN_NATIVE_ONE_LOCAL_SHAPES_COMPLETE
