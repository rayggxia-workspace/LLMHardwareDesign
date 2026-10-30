set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-380/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
source odb_geometry.tcl
proc inspect_clock {label} {
 set net [[ord::get_db_block] findNet clk]
 set wire [$net getWire]
 set out [open $label.tsv w]
 set itr [odb::new_dbWirePathItr]
 set path [odb::new_dbWirePath]
 set elem [odb::new_dbWirePathShape]
 set shape [odb::new_dbShape]
 $itr begin $wire
 while {[$itr getNextPath $path]} {
  while {[$itr getNextShape $elem]} {
   set id [odb::dbWirePathShape_junction_id_get $elem]
   set shape [$wire getShape $id]
   bvgeom::wire_shape $out $id $shape
  }
 }
 close $out
}
inspect_clock before
set ndr [[[ord::get_db_block] findNet clk] getNonDefaultRule]
set out [open ndr.tsv w]
foreach layer [[[[ord::get_db_block] getDb] getTech] getLayers] {
 set rule [$ndr getLayerRule $layer]
 if {$rule ne "NULL"} {puts $out "[$layer getName]\t[$rule getWidth]\t[$rule getSpacing]"}
}
close $out
