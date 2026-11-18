#!/bin/bash
set -euo pipefail
base=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
r=$base/cu
case_id=$1
case "$case_id" in 0|1|2|3|4|5) ;; *) exit 2;; esac
plans=$r/diagnostics/C-actual-seven-size-v4/selectedplans
(cd "$plans"; sha256sum -c selection.sha256) > /dev/null
run=$r/runs/C-v43-margin-plan${case_id}
mkdir "$run";cd "$run"
source_run=$base/audit/C40-clock-planning-frozen-v1
cp "$source_run/config.mk" config.mk
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
export CU_RESULTS=$run/flow/results/nangate45/c-overlay-current/base RESULTS_DIR=$run
mkdir -p "$CU_RESULTS"
cp "$source_run/results/1_synth_lec.v" "$CU_RESULTS/"
export C_ECO_SOURCE_SDC=$source_run/results/6_final.sdc
export C_CLOSE_SOURCE_ODB=$source_run/results/6_final.odb
export C_SIZES_PLAN=$run/size-plan.tsv
cp "$plans/plan${case_id}.tsv" "$C_SIZES_PLAN"
cp "$plans/selection.json" static-plan-selection.json
cp "$source_run/planning-source.json" planning-source.json
echo 'b59360079c0e79e335c93b8b014d7f0269d283deb6889c27c64d5ac7e0950ed0  '"$C_CLOSE_SOURCE_ODB" | sha256sum -c -
cp "$r/c-final-sizes-edit-v1.tcl" edit-frozen.tcl
cp "$r/c-margin-prepare-v1.tcl" prepare-frozen.tcl
cp "$r/c-final-route-k1-v1.tcl" route-frozen.tcl
cp "$r/u-fresh-spef-pg.tcl" fresh-frozen.tcl
export C_BOUNDED_SOURCE=$run C_ROUTE_SEED=$case_id
for f in "$C_CLOSE_SOURCE_ODB" "$C_ECO_SOURCE_SDC" "$C_SIZES_PLAN" edit-frozen.tcl prepare-frozen.tcl route-frozen.tcl fresh-frozen.tcl static-plan-selection.json planning-source.json "$r/c-freeze-outputs-v1.tcl" "$r/geometry.tcl" $CU_LIBS;do test -s "$f";sha256sum "$f";done > inputs.sha256
source /OpenROAD-flow-scripts/env.sh
openroad -no_init -exit edit-frozen.tcl > edit.log 2>&1
openroad -no_init -exit prepare-frozen.tcl > prepare-route.log 2>&1
sha256sum legalized.{odb,def,v} global.odb regenerated-ap.odb route.guide geometry-original.tsv config.mk size-plan.tsv > prepared.sha256
rc=0;openroad -no_init -exit route-frozen.tcl > route.log 2>&1 || rc=$?
printf 'route_exit=%s\n' "$rc" > route-status.txt
test -s "$CU_RESULTS/6_final.def" || exit 1
mkdir -p "$run/flow/logs/nangate45/c-overlay-current/base" "$run/flow/reports/nangate45/c-overlay-current/base"
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8 do-gds > gds.log 2>&1
export U_RESULTS=$CU_RESULTS U_LIBS=$CU_LIBS
rc=0;openroad -no_init -exit fresh-frozen.tcl > fresh.log 2>&1 || rc=$?
printf 'fresh_exit=%s\naccepted=false_pending_all_final_gates\n' "$rc" > status.txt
sha256sum "$CU_RESULTS"/6_final.{odb,def,gds,spef,sdc,v} > candidate.sha256

sha256sum -c inputs.sha256 > inputs-after-check.txt
sha256sum -c prepared.sha256 > prepared-after-check.txt
(cd "$plans"; sha256sum -c selection.sha256) > selection-after-check.txt
printf "case_complete=true\nbackend_accepted=false\n" > CANDIDATE-COMPLETE.txt
