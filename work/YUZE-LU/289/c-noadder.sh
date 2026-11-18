#!/bin/bash
set -euo pipefail
kind=$1
case "$kind" in distributed|distributed-parallel) ;; *) exit 2;; esac
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
cu=$root/cu
old=$cu/runs/C-v13-exactio-macropdn-$kind
run=$root/noadder/C-$kind
src=/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/C
test -s "$old/geometry-prects-contract.json"
mkdir -p "$run"
cd "$run"
test ! -e STARTED || exit 2
date -Is > STARTED
cp "$old/loader-candidate.sv" "$old/input.sdc" .
sed "s@$old@$run@g" "$old/config.mk" > config.mk
printf '\n# Let generic techmap and ABC optimize across full adder logic.\nexport ADDER_MAP_FILE =\n' >> config.mk
sha256sum "$old/loader-candidate.sv" loader-candidate.sv input.sdc config.mk > source.sha256
source /OpenROAD-flow-scripts/env.sh
export CU_OUTPUT_PORTS=$cu/C-outputs.txt
python3 "$cu/manifest.py" "$run"
args=(-C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8 ADDER_MAP_FILE=)
res=$run/flow/results/nangate45/c-overlay-current/base
make "${args[@]}" synth > synth.log 2>&1
make "${args[@]}" floorplan > floorplan.log 2>&1
export CU_FIXED_INPUT=$res/2_floorplan.odb CU_FIXED_OUTPUT=$res/2_floorplan.odb
openroad -no_init -exit "$cu/c-fix-initial-pins.tcl" > fixed-pins.log 2>&1
make "${args[@]}" place > place.log 2>&1
export CU_SNAPSHOT_ODB=$src/flow/results/nangate45/c-overlay-current/base/4_cts.odb CU_SNAPSHOT_OUT=$run/geometry-reference.tsv
openroad -no_init -exit "$cu/snapshot-geometry.tcl" > geometry-reference.log 2>&1
export CU_SNAPSHOT_ODB=$res/3_place.odb CU_SNAPSHOT_OUT=$run/geometry-prects.tsv
openroad -no_init -exit "$cu/snapshot-geometry.tcl" > geometry-prects.log 2>&1
python3 "$cu/compare-signal-geometry.py" geometry-reference.tsv geometry-prects.tsv geometry-prects-contract.json
make "${args[@]}" cts > cts.log 2>&1
export CU_SNAPSHOT_ODB=$res/4_cts.odb CU_SNAPSHOT_OUT=$run/geometry-postcts.tsv
openroad -no_init -exit "$cu/snapshot-geometry.tcl" > geometry-postcts.log 2>&1
python3 "$cu/compare-signal-geometry.py" geometry-reference.tsv geometry-postcts.tsv geometry-postcts-contract.json
make "${args[@]}" do-grt > grt.log 2>&1
make "${args[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > route.log 2>&1
make "${args[@]}" do-finish > finish.log 2>&1
make "${args[@]}" do-gds > gds.log 2>&1
bash "$cu/signoff-v4.sh" "$run"
bash "$cu/lec-v3.sh" "$run" "$src/flow/results/nangate45/c-overlay-current/base/4_cts.odb"
