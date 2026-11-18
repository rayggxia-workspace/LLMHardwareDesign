#!/bin/bash
set -euo pipefail
fraction=$1;drive=$2
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
run=$root/runs/U-v12-electrical-f${fraction}-x${drive}
mkdir -p "$run"
cd "$run"
test ! -e STARTED || exit 2
date -Is > STARTED
cp "$root/runs/U-v7-macropdn-x8-seed0/config.mk" config.mk
export U_RESULTS=$run/flow/results/nangate45/u-overlay-current/base
mkdir -p "$U_RESULTS"
export U_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
export U_REPEATER_FRACTION=0.$fraction U_TARGET_DRIVE=$drive
source /OpenROAD-flow-scripts/env.sh
python3 "$root/manifest.py" "$run"
sha256sum "$root/u-electrical-edit.tcl" "$root/u-electrical-route.tcl" "$root/runs/U-v11-targeted-n4-x8/flow/results/nangate45/u-overlay-current/base/6_final.odb" > eco-source-sha256.txt
openroad -no_init -exit "$root/u-electrical-edit.tcl" > edit.log 2>&1
openroad -no_init -exit "$root/u-electrical-route.tcl" > implementation.log 2>&1
mkdir -p "$run/flow/logs/nangate45/u-overlay-current/base" "$run/flow/reports/nangate45/u-overlay-current/base"
openroad -no_init -exit "$root/u-fresh-electrical-gate.tcl" > fresh-gate.log 2>&1
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8 do-gds > gds.log 2>&1
a=0; bash "$root/signoff-v4.sh" "$run" || a=$?
b=0; bash "$root/lec-v3.sh" "$run" /public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/U/flow/results/nangate45/u-overlay-current/base/4_cts.odb || b=$?
test "$a" -eq 0 -a "$b" -eq 0
