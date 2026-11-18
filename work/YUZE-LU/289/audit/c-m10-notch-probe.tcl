set_thread_count 8
read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base/6_final.odb
set b [ord::get_db_block]
set tech [[ord::get_db] getTech]
set f [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1/layers.tsv w]
foreach l [$tech getLayers] {puts $f "[$l getName]\t[$l getWidth]\t[$l getSpacing]"}
close $f
set f [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1/vias.tsv w]
foreach v [concat [$tech getVias] [$b getVias]] {foreach x [$v getBoxes] {puts $f "[$v getName]\t[[$x getTechLayer] getName]\t[$x xMin]\t[$x yMin]\t[$x xMax]\t[$x yMax]"}}
close $f
set f [open /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1/nearby-pins.tsv w]
foreach i [$b getInsts] {
 if {![[$i getMaster] isBlock]} {continue}
 puts $f "INSTANCE [$i getName] [$i getOrigin] [$i getOrient]"
 if {[$i getOrient] ne "R0"} {continue}
 lassign [$i getOrigin] ox oy
 foreach it [$i getITerms] {foreach mp [[$it getMTerm] getMPins] {foreach x [$mp getGeometry] {
  if {[[$x getTechLayer] getName] ne "metal10"} {continue}
  set x1 [expr {$ox+[$x xMin]}];set x2 [expr {$ox+[$x xMax]}];set y1 [expr {$oy+[$x yMin]}];set y2 [expr {$oy+[$x yMax]}]
  if {$x2<2782000 || $x1>2792000 || $y2<1156000 || $y1>1166000} {continue}
  puts $f "[$i getName]/[[$it getMTerm] getName] [[$it getNet] getName] $x1 $y1 $x2 $y2"
 }}}
}
close $f
help read_def
puts "ENCODER [info commands odb::*Wire*]"
