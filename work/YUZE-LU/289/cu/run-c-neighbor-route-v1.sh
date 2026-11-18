#!/bin/bash
set -euo pipefail
base=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
r=$base/cu
seed=$1
export C_BOUNDED_SOURCE=$r/runs/C-v42-neighbor-common
export C_ROUTE_SEED=$seed
run=$r/runs/C-v42-neighbor-k1-seed${seed}
mkdir "$run";cd "$run"
cp "$C_BOUNDED_SOURCE/config.mk" config.mk
cp "$C_BOUNDED_SOURCE/geometry-original.tsv" geometry-original.tsv
cp "$r/c-final-route-k1-v1.tcl" route-frozen.tcl
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
export CU_RESULTS=$run/flow/results/nangate45/c-overlay-current/base RESULTS_DIR=$run
export C_ECO_SOURCE_SDC=$r/runs/C-v38-close-y640-h50/flow/results/nangate45/c-overlay-current/base/6_final.sdc
mkdir -p "$CU_RESULTS"
cp "$r/runs/C-v38-close-y640-h50/flow/results/nangate45/c-overlay-current/base/1_synth_lec.v" "$CU_RESULTS/"
(cd "$C_BOUNDED_SOURCE"; sha256sum -c prepared.sha256) > shared-source-hash-check.log
sha256sum "$C_BOUNDED_SOURCE"/regenerated-ap.odb "$C_BOUNDED_SOURCE"/route.guide "$C_ECO_SOURCE_SDC" route-frozen.tcl config.mk $CU_LIBS > inputs.sha256
printf 'or_seed=%s\nor_k=1\ncommon_placement_grt_ap=true\n' "$seed" > choices.txt
source /OpenROAD-flow-scripts/env.sh
rc=0;openroad -no_init -exit route-frozen.tcl > route.log 2>&1 || rc=$?
printf 'route_exit=%s\n' "$rc" > route-status.txt
test -s "$CU_RESULTS/6_final.def" || exit 1
mkdir -p "$run/flow/logs/nangate45/c-overlay-current/base" "$run/flow/reports/nangate45/c-overlay-current/base"
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8 do-gds > gds.log 2>&1
export U_RESULTS=$CU_RESULTS U_LIBS=$CU_LIBS
rc=0;openroad -no_init -exit "$r/u-fresh-spef-pg.tcl" > fresh.log 2>&1 || rc=$?
printf 'fresh_exit=%s\naccepted=false_pending_all_final_gates\n' "$rc" > status.txt
sha256sum "$CU_RESULTS"/6_final.{odb,def,gds,spef,sdc,v} > candidate.sha256
