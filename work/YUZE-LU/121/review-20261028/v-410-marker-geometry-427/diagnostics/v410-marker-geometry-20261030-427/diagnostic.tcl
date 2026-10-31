set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-410/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-marker-geometry-20261030-427/odb_geometry.tcl}
set bvgeom::markers [dict create metal2 {{0 77240 306480 78180 307350}} metal3 {{1 53130 1278430 54030 1279370}} metal9 {{2 1246700 467340 1252990 473740}}]
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-marker-geometry-20261030-427/native_drc_locate.tcl}
file rename scan-counts.tsv wire-scan-counts.tsv
rename bvgeom::rectangle {}
rename bvgeom::unfiltered_rectangle bvgeom::rectangle
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-marker-geometry-20261030-427/marker_cells.tcl}
