#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
mode=$1
run=$root/runs/C-v27-joint-e20-h30
out=$root/diagnostics/C-v27-${mode}
mkdir -p "$out";cd "$out"
export U_RUN=$run U_RESULTS=$run/flow/results/nangate45/c-overlay-current/base
export U_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
export CU_LIBS=$U_LIBS
sha256sum "$U_RESULTS/6_final.odb" "$U_RESULTS/6_final.sdc" "$U_RESULTS/6_final.spef" "$root/c-v27-${mode}.tcl" > inputs.sha256
source /OpenROAD-flow-scripts/env.sh
openroad -no_init -exit "$root/c-v27-${mode}.tcl" > openroad.log 2>&1
