#!/bin/bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/audit/C-clock-actual-paths-v1/m$1
mkdir -p "$out"
cd "$out"
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$root/cu/runs/C-v28-actual-i8-h50/config.mk" | tail -1)
export CLOCK_ACTUAL_RESULTS=$root/audit/C-clock-layer-v7/m$1/results
cp "$root/audit/c-clock-actual-paths-v1.tcl" query.tcl
sha256sum "$CLOCK_ACTUAL_RESULTS"/6_final.{odb,spef,sdc} query.tcl $CU_LIBS > before.sha256
openroad -no_init -exit query.tcl > query.log 2>&1
sha256sum "$CLOCK_ACTUAL_RESULTS"/6_final.{odb,spef,sdc} query.tcl $CU_LIBS > after.sha256
cmp before.sha256 after.sha256