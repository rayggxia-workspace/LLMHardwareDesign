#!/bin/bash
set -euo pipefail
mode=$1
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
seed=$root/runs/C-v16-genericadder-cached
out=$root/studies/C-cts-v1-$mode
mkdir -p "$out";cd "$out"
test ! -e STARTED || exit 2
date -Is > STARTED
cp "$seed/config.mk" config.mk
args='-sink_clustering_enable -repair_clock_nets -apply_ndr none -root_buf BUF_X32 -buf_list {BUF_X8 BUF_X16 BUF_X32}'
case "$mode" in
 no_balance) ;;
 no_insert) args="$args -balance_levels -no_insertion_delay";;
 neither) args="$args -no_insertion_delay";;
 *) exit 2;;
esac
printf '\nexport CTS_ARGS = %s\nexport SKIP_CTS_REPAIR_TIMING = 1\n' "$args" >> config.mk
res=$out/flow/results/nangate45/c-overlay-current/base
src=$seed/flow/results/nangate45/c-overlay-current/base
mkdir -p "$res"
for f in 3_place.odb 3_place.sdc 1_synth_lec.v;do cp "$src/$f" "$res/";done
sha256sum "$src/3_place.odb" "$src/3_place.sdc" config.mk "$root/c-cts-topology-diagnose.tcl" > inputs.sha256
source /OpenROAD-flow-scripts/env.sh
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$out/config.mk" WORK_HOME="$out/flow" NUM_CORES=8 SKIP_CTS_REPAIR_TIMING=1 do-4_1_cts > cts.log 2>&1
export CU_ODB=$res/4_1_cts.odb
export CU_SDC=$res/4_1_cts.sdc
if [ ! -s "$CU_SDC" ];then export CU_SDC=$src/3_place.sdc;fi
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
openroad -no_init -exit "$root/c-cts-topology-diagnose.tcl" > diagnose.log 2>&1
python3 "$root/compare-signal-geometry.py" "$seed/geometry-prects.tsv" geometry.tsv geometry-contract.json