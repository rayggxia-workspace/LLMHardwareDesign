#!/bin/bash
set -euo pipefail
base=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
r=$base/cu
run=$r/runs/C-v43-seven-common
mkdir "$run";cd "$run"
source_run=$r/runs/C-v40-final-size-seed0
cp "$source_run/config.mk" config.mk
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
export CU_RESULTS=$run/flow/results/nangate45/c-overlay-current/base RESULTS_DIR=$run
mkdir -p "$CU_RESULTS"
cp "$source_run/flow/results/nangate45/c-overlay-current/base/1_synth_lec.v" "$CU_RESULTS/"
export C_ECO_SOURCE_SDC=$source_run/flow/results/nangate45/c-overlay-current/base/6_final.sdc
export C_CLOSE_SOURCE_ODB=$source_run/flow/results/nangate45/c-overlay-current/base/6_final.odb
export C_SIZES_PLAN=$run/size-plan.tsv
test -s "$r/diagnostics/C-actual-seven-size-v1/receipt.json"
cp "$r/diagnostics/C-actual-seven-size-v1/plan.tsv" "$C_SIZES_PLAN"
echo '6cc21b934b59858cbbee2bfe9028529746dc663e5fd61ceb1bf8f0e8b6a5cdef  '"$C_CLOSE_SOURCE_ODB" | sha256sum -c -
cp "$r/c-final-sizes-edit-v1.tcl" edit-frozen.tcl
cp "$r/c-final-sizes-prepare-v1.tcl" route-frozen.tcl
for f in "$C_CLOSE_SOURCE_ODB" "$C_ECO_SOURCE_SDC" "$C_SIZES_PLAN" edit-frozen.tcl route-frozen.tcl "$r/c-freeze-outputs-v1.tcl" "$r/geometry.tcl" $CU_LIBS;do test -s "$f";sha256sum "$f";done > inputs.sha256
cp "$r/diagnostics/C-actual-seven-size-v1/receipt.json" static-planning-receipt.json
sha256sum static-planning-receipt.json >> inputs.sha256
source /OpenROAD-flow-scripts/env.sh
openroad -no_init -exit edit-frozen.tcl > edit.log 2>&1
openroad -no_init -exit route-frozen.tcl > prepare-route.log 2>&1
sha256sum legalized.{odb,def,v} global.odb regenerated-ap.odb route.guide geometry-original.tsv config.mk size-plan.tsv > prepared.sha256
