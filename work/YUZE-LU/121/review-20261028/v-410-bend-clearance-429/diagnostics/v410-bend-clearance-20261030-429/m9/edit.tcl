set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-410/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
set ::env(BV1_GEOMETRY_SOURCE) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-bend-clearance-20261030-429/helpers/odb_geometry.tcl}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-bend-clearance-20261030-429/helpers/native_escape_geometry.tcl}
read_def -floorplan_initialize {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-bend-clearance-20261030-429/m9/patch.def}
write_def after.def
write_verilog after.v
write_db probe.odb
escape_geometry after-geometry.tsv {net95974}
drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc
