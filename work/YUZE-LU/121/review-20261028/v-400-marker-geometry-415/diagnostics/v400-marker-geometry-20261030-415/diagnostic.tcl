set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-400/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/5_2_route.odb}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v400-marker-geometry-20261030-415/odb_geometry.tcl}
set bvgeom::markers [dict create metal2 {{0 77240 295280 78180 296150} {3 2196120 790599 2197000 791401}} metal3 {{1 50890 1996630 51750 1997570} {2 2434250 715630 2435110 716570}}]
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v400-marker-geometry-20261030-415/native_drc_locate.tcl}
