#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
mode=$1
out=$root/diagnostics/C-main-v1-$mode
mkdir -p "$out";cd "$out"
test ! -e STARTED || exit 2
date -Is > STARTED
source /OpenROAD-flow-scripts/env.sh
src=$root/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base
if [ "$mode" = rcx ];then
 mkdir results
 cp "$src/6_final.odb" "$src/6_final.sdc" results/
 export U_RESULTS=$out/results
 export U_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$root/runs/C-v20-native-clock4/config.mk" | tail -1)
 sha256sum "$src/6_final.odb" "$src/6_final.sdc" "$root/c-main-rcx-v1.tcl" > inputs.sha256
 openroad -no_init -exit "$root/c-main-rcx-v1.tcl" > rcx.log 2>&1
 sha256sum before-rcx.def after-rcx.def > rcx-def-sha256.txt
 rc=0
 openroad -no_init -exit "$root/u-fresh-spef-pg.tcl" > fresh.log 2>&1 || rc=$?
 printf 'fresh_diagnostic_exit=%s\naccepted=false_native_one\n' "$rc" > status.txt
else
 openroad -no_init -exit "$root/c-main-notch-probe.tcl" > notch-probe.log 2>&1
fi
