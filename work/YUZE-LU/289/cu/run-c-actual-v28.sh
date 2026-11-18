#!/bin/bash
set -euo pipefail
base=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
root=$base/cu
iso=$1;hold=$2
run=$root/runs/C-v28-actual-i${iso}-h${hold}
mkdir -p "$run";cd "$run"
test ! -e STARTED || exit 2
date -Is > STARTED
source_run=$root/runs/C-v27-joint-e20-h30
cp "$source_run/config.mk" config.mk
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
export CU_RESULTS=$run/flow/results/nangate45/c-overlay-current/base RESULTS_DIR=$run
mkdir -p "$CU_RESULTS"
cp "$source_run/flow/results/nangate45/c-overlay-current/base/1_synth_lec.v" "$CU_RESULTS/"
export C_ECO_SOURCE_SDC=$source_run/flow/results/nangate45/c-overlay-current/base/6_final.sdc
export C_STAGE_INPUT_ODB=$root/diagnostics/C-actual-prepared-v1/resized.odb
export C_STAGE_HOLD_PLAN=$root/diagnostics/C-actual-prepared-v1/hold-setup-budget.tsv
export C_STAGE_TAG=v28_i${iso}_h${hold} C_STAGE_ISO_SIZE=$iso C_STAGE_HOLD_MARGIN_PS=$hold
export C_STAGE_EXTRA_HOOKS="$base/audit/C-antenna-v27-r2/hook.tcl $base/audit/C-v27-r-fullguard/hook.tcl $base/audit/C-v27-external-via9-guard/hook.tcl $base/audit/C-v27-s-m9-guard-v2/hook.tcl"
for f in "$C_STAGE_INPUT_ODB" "$C_STAGE_HOLD_PLAN" "$C_ECO_SOURCE_SDC" "$root/c-actual-edit-v2.tcl" "$root/c-actual-route-v1.tcl" "$root/c-v27-electrical-plan.tsv" "$root/diagnostics/C-fast-hold-probe-v1/branch-plan.tsv" $CU_LIBS $C_STAGE_EXTRA_HOOKS;do test -s "$f";sha256sum "$f";done > inputs.sha256
cp "$root/c-actual-edit-v2.tcl" edit-frozen.tcl
cp "$root/c-actual-route-v1.tcl" route-frozen.tcl
source /OpenROAD-flow-scripts/env.sh
openroad -no_init -exit edit-frozen.tcl > edit.log 2>&1
route_rc=0
openroad -no_init -exit route-frozen.tcl > route.log 2>&1 || route_rc=$?
printf 'route_exit=%s\n' "$route_rc" > route-status.txt
test -s "$CU_RESULTS/6_final.def" || exit 1
mkdir -p "$run/flow/logs/nangate45/c-overlay-current/base" "$run/flow/reports/nangate45/c-overlay-current/base"
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8 do-gds > gds.log 2>&1
export U_RESULTS=$CU_RESULTS U_LIBS=$CU_LIBS
rc=99
if test -s "$CU_RESULTS/6_final.spef";then
 rc=0
 openroad -no_init -exit "$root/u-fresh-spef-pg.tcl" > fresh.log 2>&1 || rc=$?
fi
printf 'fresh_exit=%s\naccepted=false_pending_all_gates\n' "$rc" > status.txt
sha256sum "$CU_RESULTS"/6_final.{odb,def,gds,spef,sdc,v} > candidate.sha256
