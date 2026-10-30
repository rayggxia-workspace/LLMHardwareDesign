set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-380/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
source odb_geometry.tcl
set block [ord::get_db_block]
set net [$block findNet clk]
if {$net eq "NULL"} {error "Missing exact clock net"}
set output [open clk-shapes.tsv w]
set info [open clk-terminals.tsv w]
set itr [odb::new_dbWirePathItr]
set path [odb::new_dbWirePath]
set element [odb::new_dbWirePathShape]
$itr begin [$net getWire]
while {[$itr getNextPath $path]} {
 while {[$itr getNextShape $element]} {bvgeom::wire_shape $output clk [odb::dbWirePathShape_shape_get $element]}
}
foreach term [$net getITerms] {
 set inst [$term getInst]
 set mterm [$term getMTerm]
 puts $info "[$inst getName]\t[[$inst getMaster] getName]\t[$mterm getName]\t[$inst getLocation]\t[$inst getOrient]"
 foreach pin [$mterm getMPins] {
  foreach box [$pin getGeometry] {bvgeom::db_box $output clk $box I-[$inst getName] [$inst getTransform]}
 }
}
close $info
close $output
set output [open clk-obstructions.tsv w]
foreach term [$net getITerms] {
 set inst [$term getInst]
 foreach box [[$inst getMaster] getObstructions] {bvgeom::db_box $output clk $box OBS-[$inst getName] [$inst getTransform]}
}
close $output
