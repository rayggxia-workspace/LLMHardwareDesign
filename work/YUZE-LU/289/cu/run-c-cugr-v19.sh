#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
seed=$root/runs/C-v18-donly-m0.04-d0.025
run=$root/runs/C-v19-cugr-m04-d025
mkdir -p "$run";cd "$run"
test ! -e STARTED || exit 2
date -Is > STARTED
cp "$seed/config.mk" config.mk
printf '\nexport GLOBAL_ROUTE_USE_CUGR = 1\nexport GLOBAL_ROUTE_ARGS = -use_cugr -verbose\n' >> config.mk
src=$seed/flow/results/nangate45/c-overlay-current/base
res=$run/flow/results/nangate45/c-overlay-current/base
mkdir -p "$res"
for name in 4_cts.odb 4_cts.sdc 4_cts.v 1_synth_lec.v;do cp "$src/$name" "$res/";done
cp "$seed/geometry-repaired.tsv" geometry-before.tsv
cp "$seed/source-proof-binding.json" .
sha256sum "$src/4_cts.odb" "$src/4_cts.sdc" config.mk "$root/run-c-cugr-v19.sh" > cugr-inputs.sha256
source /OpenROAD-flow-scripts/env.sh
export CU_OUTPUT_PORTS=$root/C-outputs.txt
args=(-C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8)
make "${args[@]}" do-grt > grt.log 2>&1
make "${args[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > route.log 2>&1
make "${args[@]}" do-finish > finish.log 2>&1
export U_RESULTS=$res
export U_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
rc=0
openroad -no_init -exit "$root/u-fresh-electrical-gate.tcl" > fresh-gate.log 2>&1 || rc=$?
make "${args[@]}" do-gds > gds.log 2>&1
printf 'fresh_gate_exit=%s\n' "$rc" > pending-independent-acceptance.txt
exit "$rc"