#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
margin=$1;delay=$2
seedrun=$root/runs/C-v17-closure-r24-x16
run=$root/runs/C-v18-donly-m${margin}-d${delay}
mkdir -p "$run";cd "$run"
test ! -e STARTED || exit 2
date -Is > STARTED
cp "$seedrun/config.mk" config.mk
export CU_SEED=$seedrun/flow/results/nangate45/c-overlay-current/base
export CU_RESULTS=$run/flow/results/nangate45/c-overlay-current/base
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
export CU_HOLD_MARGIN=$margin CU_CELL_DELAY=$delay CU_OUTPUT_PORTS=$root/C-outputs.txt
mkdir -p "$CU_RESULTS"
cp "$CU_SEED/1_synth_lec.v" "$CU_RESULTS/"
cp "$seedrun/source-proof-binding.json" .
source /OpenROAD-flow-scripts/env.sh
sha256sum "$CU_SEED/4_cts.odb" "$CU_SEED/4_cts.sdc" "$root/c-unshare-hold.tcl" "$root/c-plan-d-delay.tcl" "$root/c-apply-d-delay.tcl" "$root/c-donly-finalize.tcl" > closure-input-sha256.txt
for script in c-unshare-hold c-plan-d-delay c-apply-d-delay c-donly-finalize;do
 openroad -no_init -exit "$root/$script.tcl" > "$script.log" 2>&1
done
python3 "$root/compare-signal-geometry.py" "$root/runs/C-v16-genericadder-cached/geometry-reference.tsv" geometry-repaired.tsv geometry-contract.json
cp geometry-repaired.tsv geometry-before.tsv
args=(-C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8)
make "${args[@]}" do-grt > grt.log 2>&1
make "${args[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > route.log 2>&1
make "${args[@]}" do-finish > finish.log 2>&1
export U_RESULTS=$CU_RESULTS U_LIBS=$CU_LIBS
rc=0
openroad -no_init -exit "$root/u-fresh-electrical-gate.tcl" > fresh-gate.log 2>&1 || rc=$?
make "${args[@]}" do-gds > gds.log 2>&1
printf 'fresh_gate_exit=%s\n' "$rc" > pending-independent-acceptance.txt
exit "$rc"