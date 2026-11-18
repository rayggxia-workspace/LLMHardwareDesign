#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$root/u-physical/candidate-guard-v1
mkdir "$run"
cd "$run"
cp "$root/cu/runs/U-v13-electrical-f50-x4/config.mk" config.mk
export U_RESULTS=$run/flow/results/nangate45/u-overlay-current/base
export U_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
mkdir -p "$U_RESULTS" "$run/flow/logs/nangate45/u-overlay-current/base" "$run/flow/reports/nangate45/u-overlay-current/base"
source /OpenROAD-flow-scripts/env.sh
sha256sum "$root/u-spacing-guard.tcl" "$root/u-remove-pg-stacks.tsv" "$root/u-physical/leaf-cut-obs.tsv" "$root/cu/runs/U-v13-electrical-f50-x4/flow/results/nangate45/u-overlay-current/base/6_final.odb" > inputs.sha256
openroad -no_init -exit "$root/u-spacing-guard.tcl" > implementation.log 2>&1
openroad -no_init -exit "$root/cu/u-fresh-electrical-gate.tcl" > fresh-gate.log 2>&1 || echo 'FRESH_TIMING_ELECTRICAL_FAILED; diagnostic GDS continues' > fresh-gate-failed.txt
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8 do-gds > gds.log 2>&1
klayout -b -r "$root/u-physical/upper-spacing-diagnostic-v2.lydrc" -rd "in_gds=$U_RESULTS/6_final.gds" -rd "report_file=$run/upper-diagnostic.lyrdb" > upper-diagnostic.log 2>&1
