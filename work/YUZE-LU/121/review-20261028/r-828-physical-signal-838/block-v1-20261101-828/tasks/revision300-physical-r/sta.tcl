set ::env(BV1_ODB) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-828/tasks/revision300-final-source-r/flow/results/nangate45/bv1_block_v1_r/base/6_final.odb}
set ::env(BV1_SDC) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-828/tasks/revision300-final-source-r/flow/results/nangate45/bv1_block_v1_r/base/6_final.sdc}
set ::env(BV1_SPEF) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-828/tasks/revision300-final-source-r/flow/results/nangate45/bv1_block_v1_r/base/6_final.spef}
rename write_sdc bv1_original_write_sdc
proc write_sdc {args} {uplevel 1 [list bv1_original_write_sdc -digits 12 {*}$args]}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-828/src/project/experiments/block_v1/native_sta.tcl}
