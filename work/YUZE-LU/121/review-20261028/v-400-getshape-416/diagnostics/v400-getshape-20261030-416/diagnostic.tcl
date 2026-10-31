set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-400/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/5_2_route.odb}
source odb_geometry.tcl
set paths [open path-shapes.tsv w]
set actuals [open get-shapes.tsv w]
set iterator [odb::new_dbWirePathItr]
set path [odb::new_dbWirePath]
set element [odb::new_dbWirePathShape]
set block [ord::get_db_block]
foreach name {net131734 net104095 clknet_leaf_2488_clk {$abc$1405522$new_n120169}} {
 set net [$block findNet $name]
 if {$net eq "NULL"} {error "Missing selected net $name"}
 set wire [$net getWire]
 set alias [binary encode hex [encoding convertto utf-8 $name]]
 $iterator begin $wire
 while {[$iterator getNextPath $path]} {
  while {[$iterator getNextShape $element]} {
   set id [odb::dbWirePathShape_junction_id_get $element]
   bvgeom::wire_shape $paths "$alias:$id" [odb::dbWirePathShape_shape_get $element]
   set actual [$wire getShape $id]
   bvgeom::wire_shape $actuals "$alias:$id" $actual
  }
 }
}
close $paths
close $actuals
puts SELECTED_GETSHAPE_COMPARISON_COMPLETE
