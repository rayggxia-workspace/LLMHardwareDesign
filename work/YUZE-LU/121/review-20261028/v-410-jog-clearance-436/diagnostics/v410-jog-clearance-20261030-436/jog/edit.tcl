set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-410/tasks/revision300-route-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
set ::env(BV1_GEOMETRY_SOURCE) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-jog-clearance-20261030-436/helpers/odb_geometry.tcl}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-jog-clearance-20261030-436/helpers/native_escape_geometry.tcl}
read_def -floorplan_initialize {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-jog-clearance-20261030-436/jog/patch.def}
write_def after.def
write_verilog after.v
write_db probe.odb
escape_geometry after-geometry.tsv {$abc$1379946$new_n210590}
drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc
