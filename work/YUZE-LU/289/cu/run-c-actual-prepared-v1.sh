#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
export C_STRENGTH=8
run=$root/runs/C-v27-joint-e20-h30
out=$root/diagnostics/C-actual-prepared-v1
mkdir -p "$out";cd "$out"
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
sha256sum "$root/c-actual-prepared-v1.tcl" "$root/c-v27-electrical-plan.tsv" "$run/flow/results/nangate45/c-overlay-current/base/6_final.odb" "$run/flow/results/nangate45/c-overlay-current/base/6_final.spef" > inputs.sha256
for f in /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-m10/reroute-v2/patched.odb /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-static-greedy-v3/cumulative-plan-from-X8.tsv /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-rcx-normalization-v2/reextract-encoder/isolated.spef;do sha256sum "$f";done >> inputs.sha256
source /OpenROAD-flow-scripts/env.sh
openroad -no_init -exit "$root/c-actual-prepared-v1.tcl" > openroad.log 2>&1
