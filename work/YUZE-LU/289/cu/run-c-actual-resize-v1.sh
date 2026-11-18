#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
export C_STRENGTH=$1
run=$root/runs/C-v27-joint-e20-h30
out=$root/diagnostics/C-actual-resize-X$C_STRENGTH
mkdir -p "$out";cd "$out"
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
sha256sum "$root/c-actual-resize-v1.tcl" "$root/c-v27-electrical-plan.tsv" "$run/flow/results/nangate45/c-overlay-current/base/6_final.odb" "$run/flow/results/nangate45/c-overlay-current/base/6_final.spef" > inputs.sha256
source /OpenROAD-flow-scripts/env.sh
openroad -no_init -exit "$root/c-actual-resize-v1.tcl" > openroad.log 2>&1
