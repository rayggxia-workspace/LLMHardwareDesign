#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/cu/u-v15-probe
mkdir -p "$out";cd "$out"
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "U_RESULTS=$out,U_SOURCE=$root/audit/U-antenna/candidate-guard-ant-v1/flow/results/nangate45/u-overlay-current/base,U_COMBINED_HOOKS=$root/audit/U-antenna/guard-v1-map/insert-diodes-v2.tcl $root/u-upper-ndr-hook-v2.tcl,U_UPPER_MARGIN=1.2,U_TARGET_DRIVE=4,U_REPEATER_FRACTION=0.67,U_TARGET_HOLD_COUNT=3" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/cu/u-guardant-edit-v1.tcl"