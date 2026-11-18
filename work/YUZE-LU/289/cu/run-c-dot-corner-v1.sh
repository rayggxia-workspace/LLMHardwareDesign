#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
orientation=$1;depth=$2;clock=4
run=$root/runs/C-corner-v1-${orientation}-${depth}${CU_RUN_SUFFIX:-}
mkdir -p "$run";cd "$run"
test ! -e STARTED || exit 2
date -Is > STARTED
seed=$root/runs/C-v18-donly-m0.04-d0.025
cp "$seed/config.mk" config.mk
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
export CU_RESULTS=$run/flow/results/nangate45/c-overlay-current/base
export CU_CLOCK_MIN=$clock RESULTS_DIR=$run CU_VALUE=0.0
mkdir -p "$CU_RESULTS"
src=$seed/flow/results/nangate45/c-overlay-current/base
cp "$src/4_cts.sdc" route-source.sdc
cp "$src/1_synth_lec.v" "$CU_RESULTS/"
cp "$seed/source-proof-binding.json" .
source /OpenROAD-flow-scripts/env.sh
export CU_SOURCE_ODB=$root/runs/C-v22-access-metal1/flow/results/nangate45/c-overlay-current/base/6_final.odb
export CU_SOURCE_SDC=$root/runs/C-v22-access-metal1/flow/results/nangate45/c-overlay-current/base/6_final.sdc
export CU_ORIENT=$orientation CU_DEPTH=$depth
sha256sum "$CU_SOURCE_ODB" "$CU_SOURCE_SDC" "$root/c-dot-corner-v1.tcl" "$root/c-dot-actual-cut-guard-v1.tcl" > native-inputs.sha256
rc=0
openroad -no_init -exit "$root/c-dot-corner-v1.tcl" > route.log 2>&1 || rc=$?
printf 'native_route_exit=%s\naccepted=false\n' "$rc" > native-status.txt
if [ -s "$CU_RESULTS/6_final.def" ];then
 mkdir -p "$run/flow/logs/nangate45/c-overlay-current/base" "$run/flow/reports/nangate45/c-overlay-current/base"
 make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8 do-gds > gds.log 2>&1
fi
if [ "$rc" -eq 0 ];then
 export U_RESULTS=$CU_RESULTS U_LIBS=$CU_LIBS
 openroad -no_init -exit "$root/u-fresh-spef-pg.tcl" > fresh-gate.log 2>&1 || rc=$?
fi
exit "$rc"