#!/bin/bash
set -euo pipefail
base=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
r=$base/cu
run=$r/runs/C-v40-final-sizes
mkdir "$run";cd "$run"
source_run=$r/runs/C-v38-close-y640-h50
cp "$source_run/config.mk" config.mk
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
export CU_RESULTS=$run/flow/results/nangate45/c-overlay-current/base RESULTS_DIR=$run
mkdir -p "$CU_RESULTS"
cp "$source_run/flow/results/nangate45/c-overlay-current/base/1_synth_lec.v" "$CU_RESULTS/"
export C_ECO_SOURCE_SDC=$source_run/flow/results/nangate45/c-overlay-current/base/6_final.sdc
export C_CLOSE_SOURCE_ODB=$source_run/flow/results/nangate45/c-overlay-current/base/6_final.odb
export C_SIZES_PLAN=$run/size-plan.tsv
cp "$r/diagnostics/C-cache-margin-v1/plan.tsv" "$C_SIZES_PLAN"
echo '8e64222ad9eeab2266455e4f8a3023ca0eb622f5028e37a48efab8e0db2a66a7  '"$C_CLOSE_SOURCE_ODB" | sha256sum -c -
cp "$r/c-final-sizes-edit-v1.tcl" edit-frozen.tcl
cp "$r/c-close-route-v1.tcl" route-frozen.tcl
for f in "$C_CLOSE_SOURCE_ODB" "$C_ECO_SOURCE_SDC" "$C_SIZES_PLAN" edit-frozen.tcl route-frozen.tcl "$r/c-freeze-outputs-v1.tcl" "$r/geometry.tcl" $CU_LIBS;do test -s "$f";sha256sum "$f";done > inputs.sha256
source /OpenROAD-flow-scripts/env.sh
openroad -no_init -exit edit-frozen.tcl > edit.log 2>&1
rc=0;openroad -no_init -exit route-frozen.tcl > route.log 2>&1 || rc=$?
printf 'route_exit=%s\n' "$rc" > route-status.txt
test -s "$CU_RESULTS/6_final.def" || exit 1
mkdir -p "$run/flow/logs/nangate45/c-overlay-current/base" "$run/flow/reports/nangate45/c-overlay-current/base"
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8 do-gds > gds.log 2>&1
export U_RESULTS=$CU_RESULTS U_LIBS=$CU_LIBS
rc=0;openroad -no_init -exit "$r/u-fresh-spef-pg.tcl" > fresh.log 2>&1 || rc=$?
printf 'fresh_exit=%s\naccepted=false_pending_all_final_gates\n' "$rc" > status.txt
sha256sum "$CU_RESULTS"/6_final.{odb,def,gds,spef,sdc,v} > candidate.sha256
