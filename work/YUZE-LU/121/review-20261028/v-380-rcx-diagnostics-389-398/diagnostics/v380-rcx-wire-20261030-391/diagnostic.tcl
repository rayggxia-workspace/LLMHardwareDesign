set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-380/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
source odb_geometry.tcl
proc export_clk {destination} {
 set net [[ord::get_db_block] findNet clk]
 set output [open $destination w]
 set itr [odb::new_dbWirePathItr]
 set path [odb::new_dbWirePath]
 set element [odb::new_dbWirePathShape]
 $itr begin [$net getWire]
 while {[$itr getNextPath $path]} {
  while {[$itr getNextShape $element]} {bvgeom::wire_shape $output clk [odb::dbWirePathShape_shape_get $element]}
 }
 close $output
 odb::delete_dbWirePathShape $element
 odb::delete_dbWirePath $path
 odb::delete_dbWirePathItr $itr
}
export_clk clk-before-rcx.tsv
puts "BEGIN_RCX"
define_process_corner -ext_model_index 0 X
set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules
extract_parasitics
puts "END_RCX"
export_clk clk-after-rcx.tsv
write_def after-rcx.def
puts "BEGIN_POST_RCX_PG"
set code [catch {check_power_grid -net VSS -error_file post-rcx-vss.rpt} msg]
set out [open pg-status.tsv w]
puts $out "$code\t$msg"
close $out
puts "END_POST_RCX_PG $code $msg"
