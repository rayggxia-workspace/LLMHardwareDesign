#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
source /OpenROAD-flow-scripts/env.sh
n=$1;x=$2
seedrun=$root/runs/C-v16-genericadder-cached
run=$root/runs/C-v17-closure-r${n}-x${x}
mkdir -p "$run";cd "$run"
test ! -e STARTED || exit 2
date -Is > STARTED
cp "$seedrun/config.mk" config.mk
export CU_SEED=$seedrun/flow/results/nangate45/c-overlay-current/base
export CU_RESULTS=$run/flow/results/nangate45/c-overlay-current/base
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
export CU_RESET_N=$n CU_TRACE_X=$x CU_OUTPUT_PORTS=$root/C-outputs.txt
mkdir -p "$CU_RESULTS"
cp "$CU_SEED/1_synth_lec.v" "$CU_RESULTS/"
sha256sum "$CU_SEED/4_1_pre_repair_setup_hold.odb" "$CU_SEED/4_1_pre_repair_setup_hold.sdc" "$root/c-cached-closure-edit.tcl" "$root/c-cached-closure-repair.tcl" "$root/c-inject-actual-cuts.tcl" > closure-input-sha256.txt
cp "$root/c-leaf-cut-source-binding.json" "$seedrun/source-proof-binding.json" .
openroad -no_init -exit "$root/c-cached-closure-edit.tcl" > edit.log 2>&1
openroad -no_init -exit "$root/c-cached-closure-repair.tcl" > repair.log 2>&1
python3 "$root/compare-signal-geometry.py" "$seedrun/geometry-reference.tsv" geometry-repaired.tsv geometry-contract.json
cp geometry-repaired.tsv "$run/geometry-before.tsv"
args=(-C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8)
make "${args[@]}" do-grt > grt.log 2>&1
make "${args[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > route.log 2>&1
make "${args[@]}" do-finish > finish.log 2>&1
make "${args[@]}" do-gds > gds.log 2>&1
bash "$root/signoff-v4.sh" "$run"