set_thread_count 16
read_db {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-926/tasks/revision300-final-source-r/flow/results/nangate45/bv1_block_v1_r/base/6_final.odb}
set ::env(BV1_GEOMETRY_SOURCE) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-926/src/project/experiments/block_v1/odb_geometry.tcl}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-926/src/project/experiments/block_v1/signal_connectivity.tcl}
signal_connectivity_export {signal-geometry.tsv}
