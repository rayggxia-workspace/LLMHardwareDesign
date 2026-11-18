#!/bin/bash
set -euo pipefail
n=$1;drive=$2
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
run=$root/runs/U-v11-targeted-n${n}-x${drive}
mkdir -p "$run"
cd "$run"
test ! -e STARTED || exit 2
date -Is > STARTED
cp "$root/runs/U-v7-macropdn-x8-seed0/config.mk" config.mk
export U_RESULTS=$run/flow/results/nangate45/u-overlay-current/base
mkdir -p "$U_RESULTS"
export U_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
export U_TARGET_HOLD_COUNT=$n U_TARGET_DRIVE=$drive
source /OpenROAD-flow-scripts/env.sh
python3 "$root/manifest.py" "$run"
sha256sum "$root/u-postroute-eco.tcl" "$root/runs/U-v7-macropdn-x8-seed0/flow/results/nangate45/u-overlay-current/base/6_final.odb" > eco-source-sha256.txt
openroad -no_init -exit "$root/u-targeted-edit-v2.tcl" > edit.log 2>&1
openroad -no_init -exit "$root/u-targeted-route.tcl" > implementation.log 2>&1
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8 do-gds > gds.log 2>&1
a=0; bash "$root/signoff-v4.sh" "$run" || a=$?
b=0; bash "$root/lec-v3.sh" "$run" /public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/U/flow/results/nangate45/u-overlay-current/base/4_cts.odb || b=$?
test "$a" -eq 0 -a "$b" -eq 0
