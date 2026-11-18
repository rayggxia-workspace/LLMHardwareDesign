#!/bin/bash
set -euo pipefail
kind=$1
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
src=/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/C
run=$root/runs/C-v13-exactio-macropdn-$kind
res=$run/flow/results/nangate45/c-overlay-current/base
cd "$run"
test -s fixed-pins.log
test ! -e inputs-manifest-before-postio.json
mv inputs-manifest.json inputs-manifest-before-postio.json
python3 "$root/manifest.py" "$run"
source /OpenROAD-flow-scripts/env.sh
export CU_OUTPUT_PORTS=$root/C-outputs.txt
args=(-C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8)
make "${args[@]}" place > place.log 2>&1
export CU_SNAPSHOT_ODB=$src/flow/results/nangate45/c-overlay-current/base/4_cts.odb CU_SNAPSHOT_OUT=$run/geometry-reference.tsv
openroad -no_init -exit "$root/snapshot-geometry.tcl" > geometry-reference.log 2>&1
export CU_SNAPSHOT_ODB=$res/3_place.odb CU_SNAPSHOT_OUT=$run/geometry-prects.tsv
openroad -no_init -exit "$root/snapshot-geometry.tcl" > geometry-prects.log 2>&1
python3 "$root/compare-signal-geometry.py" geometry-reference.tsv geometry-prects.tsv geometry-prects-contract.json
make "${args[@]}" cts > cts.log 2>&1
export CU_SNAPSHOT_ODB=$res/4_cts.odb CU_SNAPSHOT_OUT=$run/geometry-postcts.tsv
openroad -no_init -exit "$root/snapshot-geometry.tcl" > geometry-postcts.log 2>&1
python3 "$root/compare-signal-geometry.py" geometry-reference.tsv geometry-postcts.tsv geometry-postcts-contract.json
make "${args[@]}" do-grt > grt.log 2>&1
make "${args[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > route.log 2>&1
make "${args[@]}" do-finish > finish.log 2>&1
make "${args[@]}" do-gds > gds.log 2>&1
bash "$root/signoff-v4.sh" "$run"
bash "$root/lec-v3.sh" "$run" "$src/flow/results/nangate45/c-overlay-current/base/4_cts.odb"
