set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-enclosure-bulk-20261030-453/merge/probe.odb}
set ::env(BV1_GEOMETRY_SOURCE) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-last-detour-20261030-456/helpers/odb_geometry.tcl}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-last-detour-20261030-456/helpers/native_escape_geometry.tcl}
set selected [list [encoding convertfrom utf-8 [binary decode hex 6e6574313034313134]]]
write_def before.def
write_verilog before.v
escape_geometry before-geometry.tsv $selected
