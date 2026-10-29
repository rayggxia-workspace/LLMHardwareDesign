set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-380/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
set out [open api.txt w]
foreach pattern {odb::*WirePathShape* odb::*dbShape* odb::*Wire*Shape* odb::*Wire*Rule* odb::*NonDefaultRule*} {puts $out "$pattern: [info commands $pattern]"}
set net [[ord::get_db_block] findNet clk]
set ndr [$net getNonDefaultRule]
puts $out "ndr [$ndr getName]"
foreach rule [$ndr getLayerRules] {puts $out "[[$rule getLayer] getName] [$rule getWidth] [$rule getSpacing]"}
close $out
