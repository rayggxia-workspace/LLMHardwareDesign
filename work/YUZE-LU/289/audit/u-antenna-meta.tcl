set root /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
file mkdir $root/audit/U-antenna
read_db $root/cu/runs/U-v13-electrical-f50-x4/flow/results/nangate45/u-overlay-current/base/6_final.odb
set b [ord::get_db_block]
set tech [[ord::get_db] getTech]
set f [open $root/audit/U-antenna/layers.tsv w]
foreach layer [$tech getLayers] {puts $f "[$layer getName]\t[$layer getWidth]"}
close $f
set f [open $root/audit/U-antenna/vias.tsv w]
foreach via [concat [$tech getVias] [$b getVias]] {
 foreach box [$via getBoxes] {
  puts $f "[$via getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
 }
}
close $f
set f [open $root/audit/U-antenna/bpins.tsv w]
foreach bt [$b getBTerms] {
 foreach bp [$bt getBPins] {
  foreach box [$bp getBoxes] {
   puts $f "[$bt getName]\t[[$bt getNet] getName]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
  }
 }
}
close $f
puts U_PARENT_ROUTE_METADATA_COMPLETE

set f [open $root/audit/U-antenna/endpoints.tsv w]
foreach net [$b getNets] {
 if {[$net getSigType] in {POWER GROUND}} {continue}
 foreach it [$net getITerms] {
  set i [$it getInst];set m [$i getMaster];set pin [$it getMTerm]
  puts $f "[$net getName]\t[$i getName]\t[$m getName]\t[$pin getName]\t[$pin getIoType]\t[join [$i getLocation] {\t}]\t[$i getOrient]\t[$m getWidth]\t[$m getHeight]"
 }
}
close $f
