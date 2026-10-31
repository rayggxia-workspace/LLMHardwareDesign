set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-805/tasks/revision300-final-source-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-805/src/project/experiments/block_v1/odb_geometry.tcl}
set block [ord::get_db_block]
bvgeom::export source-occupancy.tsv
set f [open native-summary.tsv w]
puts $f "dbu\t[$block getDbUnitsPerMicron]"
puts $f "top\t[$block getName]"
set die [$block getDieArea]
puts $f "die\t[$die xMin]\t[$die yMin]\t[$die xMax]\t[$die yMax]"
close $f
set f [open native-pins.tsv w]
foreach term [$block getBTerms] {
  set net [$term getNet]
  if {![bvgeom::present $net]} {error "Unconnected native port"}
  foreach pin [$term getBPins] {
    foreach box [$pin getBoxes] {
      if {[$box isVia]} {error "Via-shaped native BPin requires explicit expansion"}
      puts $f "[$term getName]\t[$term getIoType]\t[$term getSigType]\tn[$net getId]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
    }
  }
}
close $f
set f [open source-occupancy.tsv a]
set instances 0;set master_boxes 0;set block_boxes 0
foreach instance [$block getInsts] {
  incr instances
  set owner i[$instance getId]
  puts $f "# NET $owner [binary encode hex [encoding convertto utf-8 @instance/[$instance getName]]]"
  set transform [$instance getTransform]
  foreach box [[$instance getMaster] getObstructions] {
    incr master_boxes
    bvgeom::db_box $f $owner $box instance-obstruction $transform
  }
}
foreach obstruction [$block getObstructions] {
  incr block_boxes
  bvgeom::db_box $f block-obstruction [$obstruction getBBox] block-obstruction
}
close $f
set f [open occupancy-summary.tsv w]
puts $f "instances\t$instances"
puts $f "master_obstruction_boxes\t$master_boxes"
puts $f "block_obstruction_boxes\t$block_boxes"
close $f
write_abstract_lef -bloat_occupied_layers candidate.lef
