#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
clock=$1
run=$root/runs/C-v20-native-clock$clock
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
if [ "$clock" = 2 ];then
 cp "$root/studies/C-capacity-v2-0.0/global-candidate.odb" .
 cp "$root/studies/C-capacity-v2-0.0/route.guide" .
else
 export CU_SOURCE_ODB=$src/4_cts.odb CU_SOURCE_SDC=$src/4_cts.sdc
 openroad -no_init -exit "$root/c-capacity-clock4.tcl" > grt.log 2>&1
fi
sha256sum global-candidate.odb route.guide route-source.sdc "$root/c-native-route-probe.tcl" > native-inputs.sha256
rc=0
openroad -no_init -exit "$root/c-native-route-probe.tcl" > route.log 2>&1 || rc=$?
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