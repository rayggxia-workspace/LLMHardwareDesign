set ::env(BV1_ODB) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-538/tasks/revision300-final-source-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.odb}
set ::env(BV1_SDC) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-538/tasks/revision300-final-source-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.sdc}
set ::env(BV1_SPEF) {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-538/tasks/revision300-final-source-v/flow/results/nangate45/bv1_block_v1_v/base/6_final.spef}
rename write_sdc bv1_original_write_sdc
proc write_sdc {args} {uplevel 1 [list bv1_original_write_sdc -digits 12 {*}$args]}
read_db $::env(BV1_ODB)
set ::env(BV1_UNDRIVEN_REPORT) {used-signal-drivers.tsv}
source {/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-538/src/project/experiments/block_v1/native_undriven.tcl}
