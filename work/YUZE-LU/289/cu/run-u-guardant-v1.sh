#!/bin/bash
set -euo pipefail
fraction=$1;hold=$2;upper=$3
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
seed=$root/../audit/U-antenna/candidate-guard-ant-v1
run=$root/runs/U-v14-guardant-f${fraction}-h${hold}-u${upper}
mkdir -p "$run";cd "$run"
test ! -e STARTED || exit 2
date -Is > STARTED
cp "$seed/config.mk" config.mk
export U_RESULTS=$run/flow/results/nangate45/u-overlay-current/base
export U_SOURCE=$seed/flow/results/nangate45/u-overlay-current/base
mkdir -p "$U_RESULTS"
export U_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
export U_UPPER_MARGIN=$upper
export U_REPEATER_FRACTION=0.$fraction U_TARGET_DRIVE=4 U_TARGET_HOLD_COUNT=$hold
export U_COMBINED_HOOKS="$root/../audit/U-antenna/guard-v1-map/insert-diodes-v2.tcl $root/../u-upper-ndr-hook.tcl"
source /OpenROAD-flow-scripts/env.sh
python3 "$root/manifest.py" "$run"
sha256sum "$root/u-guardant-edit-v1.tcl" "$root/u-guardant-route-v1.tcl" "$U_SOURCE/6_final.odb" "$U_SOURCE/6_final.sdc" $U_COMBINED_HOOKS > eco-source-sha256.txt
openroad -no_init -exit "$root/u-guardant-edit-v1.tcl" > edit.log 2>&1
openroad -no_init -exit "$root/u-guardant-route-v1.tcl" > implementation.log 2>&1
mkdir -p "$run/flow/logs/nangate45/u-overlay-current/base" "$run/flow/reports/nangate45/u-overlay-current/base"
rc=0
openroad -no_init -exit "$root/u-fresh-electrical-gate.tcl" > fresh-gate.log 2>&1 || rc=$?
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8 do-gds > gds.log 2>&1
printf 'fresh_gate_exit=%s\n' "$rc" > pending-independent-acceptance.txt
exit "$rc"