#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
out=$root/diagnostics/C-main-hold-budget-v1
mkdir -p "$out";cd "$out"
source /OpenROAD-flow-scripts/env.sh
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$root/runs/C-v20-native-clock4/config.mk" | tail -1)
sha256sum "$root/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base/6_final.odb" "$root/diagnostics/C-main-v1-rcx/results/6_final.spef" "$root/c-main-hold-budget-v1.tcl" > inputs.sha256
openroad -no_init -exit "$root/c-main-hold-budget-v1.tcl" > budget.log 2>&1
