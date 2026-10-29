set -e
source /OpenROAD-flow-scripts/env.sh
cp /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-via-enclosure-20261030-451/merge/before.def /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-via-gds-20261030-452/before/gds-flow/results/nangate45/bv1_block_v1_v/base/6_final.def
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-410/tasks/revision300-route-v/config.mk WORK_HOME=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/diagnostics/v410-via-gds-20261030-452/before/gds-flow NUM_CORES=16 do-gds
