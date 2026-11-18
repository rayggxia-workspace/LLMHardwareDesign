#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
margin=$1;holdps=$2
export C_ECO_TAG=e${margin}_h${holdps} C_ECO_MARGIN=$margin C_ECO_HOLD_PS=$holdps
run=$root/runs/C-v24-joint-e${margin}-h${holdps}${C_ECO_SUFFIX:-}
mkdir -p "$run";cd "$run"
test ! -e STARTED || exit 2
date -Is > STARTED
export C_ECO_SOURCE_ODB=${C_ECO_SOURCE_ODB:-/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1/patched.odb}
export C_ECO_SOURCE_SDC=$root/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base/6_final.sdc
expected=${C_EXPECTED_ODB_SHA:-e0d64d00f28f2b3349001ab9e2acb5feaa741cc0bb7aee7a61c166c244a0b91f}
test "$(sha256sum "$C_ECO_SOURCE_ODB" | cut -d' ' -f1)" = "$expected"
cp "$root/runs/C-v20-native-clock4/config.mk" config.mk
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
export CU_RESULTS=$run/flow/results/nangate45/c-overlay-current/base RESULTS_DIR=$run
mkdir -p "$CU_RESULTS"
cp "$root/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base/1_synth_lec.v" "$CU_RESULTS/"
for file in "$C_ECO_SOURCE_ODB" "$C_ECO_SOURCE_SDC" "$root/diagnostics/C-main-v1-rcx/results/6_final.spef" "$root/diagnostics/C-main-hold-budget-v3/hold-setup-budget.tsv" "$root/diagnostics/C-main-hold-budget-v3/original-signatures.tcllist" "$root/c-joint-electric-v1.tcl" "$root/c-joint-edit-v2.tcl" "$root/c-joint-route-v1.tcl" "$root/c-freeze-outputs-v1.tcl" "$root/c-macro-access-ripup-v1.tcl" "$root/c-dot-actual-cut-guard-v1.tcl" /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-antenna-main-v2/hook.tcl $CU_LIBS ${C_EXTRA_HOOKS:-} ${C_EXTRA_RIP_HOOKS:-};do test -s "$file";sha256sum "$file";done > inputs.sha256
source /OpenROAD-flow-scripts/env.sh
openroad -no_init -exit "$root/c-joint-electric-v1.tcl" > electric.log 2>&1
openroad -no_init -exit "$root/c-joint-edit-v2.tcl" > edit.log 2>&1
route_rc=0
openroad -no_init -exit "$root/c-joint-route-v1.tcl" > route.log 2>&1 || route_rc=$?
printf "route_exit=%s\n" "$route_rc" > route-status.txt
if [ "${C_EDIT_ONLY:-0}" = 1 ];then echo EDIT_ONLY_PILOT_NOT_ACCEPTED;exit 0;fi
test -s "$CU_RESULTS/6_final.def" || exit "${route_rc:-1}"
mkdir -p "$run/flow/logs/nangate45/c-overlay-current/base" "$run/flow/reports/nangate45/c-overlay-current/base"
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8 do-gds > gds.log 2>&1
export U_RESULTS=$CU_RESULTS U_LIBS=$CU_LIBS
rc=99
if test -s "$CU_RESULTS/6_final.spef"; then
 rc=0
 openroad -no_init -exit "$root/u-fresh-spef-pg.tcl" > fresh.log 2>&1 || rc=$?
fi
printf 'fresh_exit=%s\naccepted=false_pending_native_fullGDS_LEC_RC_geometry\n' "$rc" > status.txt
sha256sum "$CU_RESULTS/6_final.odb" "$CU_RESULTS/6_final.def" "$CU_RESULTS/6_final.gds" "$CU_RESULTS/6_final.spef" "$CU_RESULTS/6_final.sdc" "$CU_RESULTS/6_final.v" > candidate.sha256 || true
