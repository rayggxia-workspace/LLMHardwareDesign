#!/bin/bash
# Called only inside allocated compute node + ORFS container.
set -euo pipefail
block=$1
seed=${2:-0}
cores=${3:-8}
case "$block" in C|U) ;; *) exit 2;; esac
case "$seed" in 0|1|2) ;; *) exit 2;; esac
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
src=/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/$block
lower=$(printf '%s' "$block" | tr '[:upper:]' '[:lower:]')
run=$root/runs/$block-v2-seed$seed
mkdir -p "$run"
cd "$run"
test ! -e STARTED || { echo 'Refusing to overwrite a candidate'; exit 2; }
date -Is > STARTED
cp "$src/config.mk" config.mk
printf '\nexport PRE_GLOBAL_ROUTE_TCL = %s/pre-global-v2.tcl\nexport GRT_SEED = %s\nexport OR_SEED = %s\n' "$root" "$seed" "$seed" >> config.mk
printf '\nexport DONT_USE_CELLS += BUF_X1 BUF_X2 BUF_X4\n' >> config.mk
res=$run/flow/results/nangate45/$lower-overlay-current/base
mkdir -p "$res"
cp "$src/flow/results/nangate45/$lower-overlay-current/base/4_cts.odb" "$src/flow/results/nangate45/$lower-overlay-current/base/4_cts.sdc" "$res/"
sha256sum "$res/4_cts.odb" "$res/4_cts.sdc" "$src/config.mk" "$src/input.sdc" > source-sha256.txt
export CU_OUTPUT_PORTS=$root/$block-outputs.txt
source /OpenROAD-flow-scripts/env.sh
make_args=(-C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES="$cores")
make "${make_args[@]}" do-grt > grt.log 2>&1
make "${make_args[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > route.log 2>&1
make "${make_args[@]}" do-finish > finish.log 2>&1
make "${make_args[@]}" do-gds > gds.log 2>&1
date -Is > BACKEND_ARTIFACTS_CREATED_NOT_SIGNED_OFF
