set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
file mkdir $root/u-physical
read_db $root/cu/runs/U-v7-macropdn-x8-seed0/flow/results/nangate45/u-overlay-current/base/6_final.odb
set b [ord::get_db_block]
set tech [[ord::get_db] getTech]
set f [open $root/u-physical/layers.tsv w]
foreach layer [$tech getLayers] {puts $f "[$layer getName]\t[$layer getWidth]"}
close $f
set f [open $root/u-physical/vias.tsv w]
foreach via [concat [$tech getVias] [$b getVias]] {
 foreach box [$via getBoxes] {
  puts $f "[$via getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
 }
}
close $f
set f [open $root/u-physical/bpins.tsv w]
foreach bt [$b getBTerms] {
 foreach bp [$bt getBPins] {
  foreach box [$bp getBoxes] {
   puts $f "[$bt getName]\t[[$bt getNet] getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
  }
 }
}
close $f
puts U_PARENT_ROUTE_METADATA_COMPLETE
