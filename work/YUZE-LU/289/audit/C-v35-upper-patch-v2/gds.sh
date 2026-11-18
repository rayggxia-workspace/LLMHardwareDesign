set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
openroad -exit /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-upper-patch-v2/obs.tcl > /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-upper-patch-v2/obs.log 2>&1
klayout -zz -rd design_name=cfj_group_c_memory_legacy \
        -rd in_def=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-upper-patch-v2/patched.def \
        -rd in_files="/OpenROAD-flow-scripts/flow/platforms/nangate45/gds/NangateOpenCellLibrary.gds /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base/6_final.gds /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/release/e_compact/6_final.gds /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs/candidate-G-hold03-v3/qualification-v2/flow/results/nangate45/bv1_block_v2_g/base/6_final.gds /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt252/delivery/native/6_final.gds /public/home/yuzelu/project-circuit/c-blockv2-main-250mhz-20261115-01/dot-leaf250-antenna/flow/results/nangate45/c_dot_e32_250/base/6_final.gds /public/home/yuzelu/project-circuit/issue250-mc-native-physical-20261111-03/route/bank-stream.gds " \
        -rd seal_file="" \
        -rd out_file=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-upper-patch-v2/patched.gds \
        -rd tech_file=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v35-unified-i8-h100-pnone/flow/objects/nangate45/c-overlay-current/base/klayout.lyt \
        -rd layer_map= \
        -r /OpenROAD-flow-scripts/flow/util/def2stream.py
klayout -b -r /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-upper-patch-v2/gds-check.py
