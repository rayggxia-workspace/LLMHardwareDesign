read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/U-v7-macropdn-x8-seed0/flow/results/nangate45/u-overlay-current/base/6_final.odb
set b [ord::get_db_block]
set it [odb::dbWireShapeItr]
set shape [odb::dbShape]
set count 0
foreach net [$b getNets] {
 set wire [$net getWire]
 if {$wire eq "NULL"} {continue}
 $it begin $wire
 while {[$it next $shape]} {
  set box [$shape getBox]
  puts "WIRE [$net getName] VIA [$shape isVia] BOX [$box xMin] [$box yMin] [$box xMax] [$box yMax]"
  incr count
  if {$count>=5} {break}
 }
 if {$count>=5} {break}
}
puts "ITERATOR_PILOT_COMPLETE"
