#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
orientation=$1;depth=$2
seed=$root/runs/C-corner-v1-${orientation}-${depth}
run=$root/runs/C-corner-v5-${orientation}-${depth}
mkdir -p "$run";cd "$run"
test ! -e STARTED || exit 2
date -Is > STARTED
cp "$seed/config.mk" config.mk
cp "$seed/corner-global.odb" global-candidate.odb
cp "$seed/route.guide" .
cp "$seed/corner-edited.sdc" route-source.sdc
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
export CU_RESULTS=$run/flow/results/nangate45/c-overlay-current/base
export CU_CLOCK_MIN=4 RESULTS_DIR=$run
mkdir -p "$CU_RESULTS"
sha256sum global-candidate.odb route.guide route-source.sdc "$root/c-corner-resume-v5.tcl" > inputs.sha256
source /OpenROAD-flow-scripts/env.sh
rc=0
openroad -no_init -exit "$root/c-corner-resume-v5.tcl" > route.log 2>&1 || rc=$?
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
