set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-380/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
source odb_geometry.tcl
set bvgeom::markers [dict create metal3 {{0 1051800 680200 1052200 680600}}]
source native_drc_locate.tcl
drt::check_drc_cmd native-drc.rpt 0 0 0 0 pg_short_readonly
