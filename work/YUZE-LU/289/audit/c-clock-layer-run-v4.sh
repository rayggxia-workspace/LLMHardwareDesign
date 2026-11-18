#!/bin/bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
case "$1" in 4|7|9) ;; *) exit 2;; esac
export CLOCK_MIN_LAYER=$1
out=$root/audit/C-clock-layer-v4/m$1
mkdir "$out"
cd "$out"
cp "$root/audit/c-clock-layer-route-v4.tcl" route.tcl
cp "$root/cu/u-fresh-spef-pg.tcl" fresh.tcl
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$root/cu/runs/C-v28-actual-i8-h50/config.mk" | tail -1)
export U_LIBS=$CU_LIBS U_RESULTS=$out/results
mkdir "$U_RESULTS"
seed=$root/audit/C-v28-nine-net-normalization-v1/reextract-encoder
source_results=$root/cu/runs/C-v28-actual-i8-h50/flow/results/nangate45/c-overlay-current/base
sha256sum "$seed/before.odb" "$source_results/6_final.sdc" route.tcl fresh.tcl $CU_LIBS > inputs-before.sha256
openroad -no_init -exit route.tcl > route.log 2>&1
fresh_status=0
openroad -no_init -exit fresh.tcl > fresh.log 2>&1 || fresh_status=$?
sha256sum "$seed/before.odb" "$source_results/6_final.sdc" route.tcl fresh.tcl $CU_LIBS > inputs-after.sha256
cmp inputs-before.sha256 inputs-after.sha256
printf 'fresh_exit=%s\nbackend_accepted=false\nactual_wire_layer_diagnostic=true\n' "$fresh_status" > status.txt
