#!/bin/bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/audit/C-output-clock-paths-v1
mkdir "$out"
cd "$out"
cp "$root/audit/c-output-clock-paths-v1.tcl" query.tcl
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$root/cu/runs/C-v28-actual-i8-h50/config.mk" | tail -1)
seed=$root/audit/C-v28-nine-net-normalization-v1/reextract-encoder
source_results=$root/cu/runs/C-v28-actual-i8-h50/flow/results/nangate45/c-overlay-current/base
sha256sum "$seed/before.odb" "$seed/isolated.spef" "$source_results/6_final.sdc" query.tcl $CU_LIBS > inputs-before.sha256
openroad -no_init -exit query.tcl > query.log 2>&1
sha256sum "$seed/before.odb" "$seed/isolated.spef" "$source_results/6_final.sdc" query.tcl $CU_LIBS > inputs-after.sha256
cmp inputs-before.sha256 inputs-after.sha256
printf 'read_only=true\nphysical_or_constraint_change=false\nbackend_accepted=false\n' > scope.txt
